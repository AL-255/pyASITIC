"""Lossless printf snapshot metadata, FP and ordered-region references."""
import base64,hashlib,json,zlib
from functools import lru_cache
from getline_fixture import record_id
from audit_loader_lookup_original import data as dense_data
from reasitic.heap import AddressSpace
from reasitic.memory import Memory


def digest_context(context):
    return hashlib.sha256(json.dumps(context,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def digest_regions(fixture,ids):
    return hashlib.sha256(''.join(fixture['loader_record_keys'][i]+'\n'for i in ids).encode()).hexdigest()


def pack_state(fixture,state,templates_by_length):
    """Factor repeated fields without changing any native boundary target."""
    original=dict(state);ids=state.pop('region_ids');raw=state.pop('xstate')
    context={key:state.pop(key)for key in list(state)if key!='registers'}
    if context:
        key=digest_context(context);fixture.setdefault('printf_contexts',{})[key]=context;state['printf_context']=key
    key=hashlib.sha256(bytes.fromhex(raw)).hexdigest();fixture.setdefault('printf_xstates',{})[key]=raw;state['printf_xstate']=key
    templates=fixture.setdefault('printf_region_templates',[]);candidates=templates_by_length.setdefault(len(ids),[])
    if candidates:
        index=candidates[-1];updates=[[position,value]for position,value in enumerate(ids)if templates[index][position]!=value]
    else:index=None;updates=[]
    if index is None or len(updates)>len(ids)//2:
        index=len(templates);templates.append(list(ids));candidates.append(index);updates=[]
    state.update(printf_region_template=index,printf_region_updates=updates,printf_region_manifest=digest_regions(fixture,ids))
    # This compares every field and every ordered region reference against
    # the complete pre-conversion state, before the original is discarded.
    if unpack_state(fixture,state)!=original:raise ValueError('Printf snapshot conversion changed native state')


def unpack_state(fixture,state):
    if 'printf_region_template'not in state:return state
    if any(key in state for key in ('regions','region_ids','xstate')):raise ValueError('Ambiguous printf snapshot encoding')
    index=state['printf_region_template'];templates=fixture['printf_region_templates']
    if isinstance(index,bool)or not isinstance(index,int)or not 0<=index<len(templates):raise ValueError('Invalid printf region template')
    ids=list(templates[index]);previous=-1
    for item in state['printf_region_updates']:
        if not isinstance(item,list)or len(item)!=2:raise ValueError('Invalid printf region update')
        position,value=item
        if isinstance(position,bool)or not isinstance(position,int)or not previous<position<len(ids):raise ValueError('Invalid printf region update position')
        if isinstance(value,bool)or not isinstance(value,int)or not 0<=value<len(fixture['loader_record_keys']):raise ValueError('Invalid printf region update value')
        ids[position]=value;previous=position
    if any(isinstance(value,bool)or not isinstance(value,int)or not 0<=value<len(fixture['loader_record_keys'])for value in ids):raise ValueError('Invalid printf region template value')
    if digest_regions(fixture,ids)!=state['printf_region_manifest']:raise ValueError('Invalid printf ordered region manifest')
    context={}
    if key:=state.get('printf_context'):
        context=fixture['printf_contexts'][key]
        if digest_context(context)!=key:raise ValueError('Invalid printf context content')
        if any(key in context for key in ('registers','xstate','region_ids','regions')):raise ValueError('Invalid printf context fields')
    key=state['printf_xstate'];raw=fixture['printf_xstates'][key]
    if hashlib.sha256(bytes.fromhex(raw)).hexdigest()!=key:raise ValueError('Invalid printf FP content')
    result=dict(context)
    for key,value in state.items():
        if key not in ('printf_context','printf_xstate','printf_region_template','printf_region_updates','printf_region_manifest'):
            if key in result:raise ValueError('Conflicting printf context fields')
            result[key]=value
    result.update(xstate=raw,region_ids=ids);return result


def expand_state(fixture,state):
    state=unpack_state(fixture,state)
    if 'region_ids'not in state:return state
    regions=[]
    for index in state['region_ids']:
        if isinstance(index,bool)or not isinstance(index,int)or not 0<=index<len(fixture['loader_record_keys']):raise ValueError('Invalid printf region index')
        key=fixture['loader_record_keys'][index];region=fixture['loader_records'][key]
        if record_id(region)!=key:raise ValueError('Invalid printf region record')
        region=dict(region)
        for field in ('pages','printf_page_ids'):
            if field in region:region[field]=list(region[field])
        regions.append(region)
    result=dict(state,regions=regions);result.pop('region_ids');return result


@lru_cache(maxsize=2048)
def page_bytes(key,payload,base_payload=None):
    base_key=None
    if ':'in payload:base_key,payload=payload.split(':',1)
    try:raw=zlib.decompress(base64.b64decode(payload,validate=True))
    except (ValueError,zlib.error)as error:raise ValueError('Invalid compressed printf page encoding')from error
    if base_key is not None:
        if base_payload is None or ':'in base_payload:raise ValueError('Invalid printf page base')
        base=page_bytes(base_key,base_payload)
        if len(raw)!=len(base):raise ValueError('Invalid printf page delta extent')
        raw=(int.from_bytes(raw,'little')^int.from_bytes(base,'little')).to_bytes(len(raw),'little')
    if hashlib.sha256(raw).hexdigest()!=key:raise ValueError('Invalid compressed printf page content')
    return raw


def data(fixture,region):
    if 'printf_page_ids'not in region:return dense_data(fixture,region)
    pages=[];keys=fixture['printf_page_keys']
    for index in region['printf_page_ids']:
        if isinstance(index,bool)or not isinstance(index,int)or not 0<=index<len(keys):raise ValueError('Invalid printf page index')
        key=keys[index];payload=fixture['printf_pages'][key];base=fixture['printf_pages'][payload.split(':',1)[0]]if ':'in payload else None
        pages.append(page_bytes(key,payload,base))
    raw=b''.join(pages)
    if len(raw)!=region['size']or hashlib.sha256(raw).hexdigest()!=region['sha256']:raise ValueError('Invalid printf region content')
    return raw


def memory_for(fixture,state):
    ranges=[]
    for start,end in sorted((r['address'],r['address']+r['size'])for r in state['regions']):
        if ranges and start<=ranges[-1][1]:ranges[-1][1]=max(ranges[-1][1],end)
        else:ranges.append([start,end])
    memory=Memory(AddressSpace([dict(start=start,end=end)for start,end in ranges]))
    for region in state['regions']:memory.write(region['address'],data(fixture,region))
    return memory


def compact_pages(fixture):
    keys=list(fixture['loader_pages']);indices={key:i for i,key in enumerate(keys)};pages={};baselines={};hints={}
    for key,value in fixture['loader_pages'].items():
        if hashlib.sha256(bytes.fromhex(value)).hexdigest()!=key:raise ValueError('Invalid dense printf page content')
    for region in fixture['loader_records'].values():
        for offset,key in enumerate(region['pages']):
            slot=(region['address']+4096*offset,len(fixture['loader_pages'][key])//2)
            base=baselines.setdefault(slot,key)
            if key!=base:hints.setdefault(key,base)
    full=set(baselines.values())
    for key,value in fixture['loader_pages'].items():
        raw=bytes.fromhex(value)
        payload=base64.b64encode(zlib.compress(raw,9)).decode()
        if key not in full and key in hints:
            base=hints[key];old=bytes.fromhex(fixture['loader_pages'][base]);delta=(int.from_bytes(raw,'little')^int.from_bytes(old,'little')).to_bytes(len(raw),'little')
            candidate=base+':'+base64.b64encode(zlib.compress(delta,9)).decode()
            if len(candidate)<len(payload):payload=candidate
        pages[key]=payload
    for key,payload in pages.items():
        base=pages[payload.split(':',1)[0]]if ':'in payload else None
        if page_bytes(key,payload,base)!=bytes.fromhex(fixture['loader_pages'][key]):raise ValueError('Printf page conversion changed bytes')
    fixture.update(printf_page_keys=keys,printf_pages=pages)
    for region in fixture['loader_records'].values():
        original=dict(region);region['printf_page_ids']=[indices[key]for key in region.pop('pages')]
        restored=dict(region,pages=[keys[i]for i in region['printf_page_ids']]);restored.pop('printf_page_ids')
        if restored!=original:raise ValueError('Printf page conversion changed ordered region record')
    fixture.pop('loader_pages');return len(keys)
