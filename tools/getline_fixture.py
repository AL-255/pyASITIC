"""Lossless region manifests; all owners and bytes remain independent targets."""
def record_id(region):return f"{region['address']:x}:{region['size']:x}:{region['sha256']}"


def pack_state(state,records,indices=None):
    keys=[]
    for region in state.pop('regions'):
        key=record_id(region)
        if key in records and records[key]!=region:raise ValueError('Conflicting region manifest')
        records[key]=region
        if indices is not None:key=indices.setdefault(key,len(indices))
        keys.append(key)
    state['region_ids']=keys


def expand_state(fixture,state):
    if 'region_ids'not in state:return state
    regions=[]
    for key in state['region_ids']:
        if isinstance(key,int):
            if isinstance(key,bool)or not 0<=key<len(fixture['loader_record_keys']):raise ValueError('Invalid region manifest index')
            key=fixture['loader_record_keys'][key]
        region=fixture['loader_records'][key]
        if record_id(region)!=key:raise ValueError('Invalid region manifest')
        regions.append(dict(region,pages=list(region['pages'])))
    result=dict(state,regions=regions);result.pop('region_ids');return result


def expand_case(fixture,case):
    return dict(case,byte_calls=[dict(call,before=expand_state(fixture,call['before']),
                    **({'after':expand_state(fixture,call['after'])}if 'after'in call else{}))for call in case['byte_calls']])
