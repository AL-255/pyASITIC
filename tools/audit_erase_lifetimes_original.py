"""Validate captured native erasure lifetimes; this is not a Python ERASE gate."""
import gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
f=json.loads(gzip.decompress((ROOT/'tests/fixtures/phase_erase_original.json.gz').read_bytes()))
assert len(f['cases'])==15 and sum(len(c['states'])for c in f['cases'])==210
for name,digest in f['parents'].items():assert hashlib.sha256((ROOT/'tests/fixtures'/f'{name}.json').read_bytes()).hexdigest()==digest
for c in f['cases']:
 assert c['signal']==0 and len(c['states'])==len(c['operations'])+1,c['label']
 for event in c['states']:
  assert event['control']==0x37f
  names={s['address']:s['name']for s in event['shapes']};assert len(names)==len(event['shapes'])
  for s in event['shapes']:
   assert s['partner']==names.get(s['partner_address'])
   assert s['dangling_partner']==bool(s['partner_address']and s['partner_address']not in names)
   for segment in s['segments']:assert len(bytes.fromhex(segment['coordinates_bits']))==18*8
 if c['label']!='erase-directed':assert not c['states'][-1]['shapes'],c['label']
c=next(c for c in f['cases']if c['label']=='erase-directed')
get=lambda i,name:next(s for s in c['states'][i]['shapes']if s['name']==name)
erased=get(0,'A')['address'];assert get(5,'B')['partner_address']==erased and get(5,'B')['dangling_partner']
assert get(6,'B')['origin_bits']!=get(5,'B')['origin_bits']
assert get(7,'D')['address']==erased and get(7,'B')['partner']=='D'
assert get(8,'D')['origin_bits']!=get(7,'D')['origin_bits']
print('Native ERASE evidence verified: all 210 states retained, empty scenes, mutual/self links, stale freed link, descriptor reuse and subsequent moved copy. Python ERASE remains unimplemented; this audit makes no runtime-equivalence claim.')
