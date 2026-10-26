"""Lossless transport factoring for complete native exit heap metadata."""
import copy,gzip,hashlib,json
from pathlib import Path

INLINE=('label','esp','ebp')
BYTE_BANKS=('driver_heap_pages','loader_regions','storage_pages','storage_blobs','cache_file_pages')
REFERENCE='Every complete exit heap dictionary expands identically before its dense representation is replaced. Label and ABI markers remain inline; every other field is retained in the SHA256 content bank. No owner, field, word, state or outcome is omitted. Each expansion returns independent mutable containers, so later assertion mutations cannot alter earlier component inputs.'


def content_key(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def heap(fixture,point):
    value=point['heap']
    if 'content'not in value:return copy.deepcopy(value)
    body=fixture['exit_heap_states'][value['content']]
    if content_key(body)!=value['content']:raise ValueError('Changed complete exit heap content')
    result=copy.deepcopy(body);result.update((key,value[key])for key in INLINE if key in value)
    return result


def expand_case(fixture,entry):
    # Only assertion transport is expanded. No runtime input is initialized.
    shutdown=dict(entry['shutdown'])
    for name in('exit_calls','crt_calls'):
        if name not in shutdown:continue
        shutdown[name]=[dict(call,**{phase:dict(call[phase],heap=heap(fixture,call[phase]))for phase in('before','after')if phase in call})for call in shutdown[name]]
    return dict(entry,shutdown=shutdown)


def factor(fixture):
    bank={};count=0
    for entry in fixture['cases']:
        for call in entry['shutdown']['exit_calls']+entry['shutdown'].get('crt_calls',[]):
            for phase in('before','after'):
                if phase not in call:continue
                point=call[phase];original=point['heap'];body={k:v for k,v in original.items()if k not in INLINE};key=content_key(body)
                if key in bank and bank[key]!=body:raise ValueError('Conflicting exit heap content')
                bank[key]=body;packed=dict(content=key,**{name:original[name]for name in INLINE if name in original})
                if dict(body,**{name:packed[name]for name in INLINE if name in packed})!=original:raise ValueError('Exit heap factoring changed a native field')
                point['heap']=packed;count+=1
    fixture['exit_heap_states']=bank;fixture['exit_heap_projection']=dict(states_checked=count,unique_states=len(bank),reference=REFERENCE)
    return fixture


def factor_file(path):
    path=Path(path);f=json.loads(gzip.decompress(path.read_bytes()));factor(f)
    with gzip.GzipFile(str(path),'wb',mtime=0)as stream:stream.write((json.dumps(f,separators=(',',':'))+'\n').encode())
    return f['exit_heap_projection']


def read_fixture(path):
    path=Path(path);fixture=json.loads(gzip.decompress(path.read_bytes()))
    for bank,info in fixture.get('external_banks',{}).items():
        if bank not in BYTE_BANKS or Path(info['file']).name!=info['file']:raise ValueError('Invalid native exit bank owner')
        raw=(path.parent/info['file']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=info['sha256']:raise ValueError('Changed complete native exit bank')
        values=json.loads(gzip.decompress(raw))
        if len(values)!=info['entries']or sum(len(v)//2 for v in values.values())!=info['bytes']:raise ValueError('Changed complete native exit bank extent')
        if fixture.get(bank):raise ValueError('Native bank is both inline and external')
        fixture[bank]=values
    return fixture


def externalize_file(path,*,banks=('driver_heap_pages','loader_regions')):
    path=Path(path);fixture=json.loads(gzip.decompress(path.read_bytes()));external={}
    prefix=path.name.removesuffix('_original.json.gz')
    for bank in banks:
        if bank not in BYTE_BANKS:raise ValueError('Invalid native byte bank')
        values=fixture[bank];name=prefix+'_'+bank+'_original.json.gz';target=path.parent/name
        with gzip.GzipFile(str(target),'wb',mtime=0)as stream:stream.write((json.dumps(values,separators=(',',':'))+'\n').encode())
        if json.loads(gzip.decompress(target.read_bytes()))!=values:raise ValueError('External bank changed captured native content')
        if target.stat().st_size>=100*1024**2:raise ValueError('Native bank requires further lossless factoring')
        external[bank]=dict(file=name,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),entries=len(values),bytes=sum(len(v)//2 for v in values.values()));fixture[bank]={}
    fixture['external_banks']=external
    with gzip.GzipFile(str(path),'wb',mtime=0)as stream:stream.write((json.dumps(fixture,separators=(',',':'))+'\n').encode())
    loaded=read_fixture(path)
    if loaded['external_banks']!=external:raise ValueError('Changed native exit bank manifest')
    return external
