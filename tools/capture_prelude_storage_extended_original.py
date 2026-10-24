"""Small native square/rectangular FFT histories for portable storage checks."""
import copy,gzip,hashlib,json,re
import capture_prelude_storage_original as capture


def jobs():
    base=next(capture.geometry.arena.lifetime.jobs())
    for nx,ny in ((8,8),(16,8)):
        technology=base['request']['technology']
        for key,value in (('fftx',nx),('ffty',ny)):technology=re.sub(rf'(?im)^(\s*{key}\s*=\s*)[\d.]+',rf'\g<1>{value}',technology)
        parameters=dict(name='A',length=128,width=64,metal='M4',angle=0,phase=1,x=64,y=64)
        request=dict(action='pi2',kind='wire',parameters=parameters,technology=technology,frequency_ghz=.25,frequency_hz=250e6,eddy=False,winding=0,native_keyword=True,native_mesh=True,mesh=dict(length_cell=1000,width_cell=1000,thickness_cell=1000,capacitance_length_cell=1000,capacitance_width_cell=1000))
        script='CELL 1000 1000 1000\nCCELL 1000 1000\nEDDY OFF\nWIRE NAME=A:LEN=128:WID=64:METAL=M4:ORIENT=0:PHASE=1:XORG=64:YORG=64\nPI2 A .25\n2PORT A .25 .25 1 S RECT SLOW s.out\n'
        yield dict(label=f'prelude/fft/{nx}/{ny}',parent=base['parent'],request=copy.deepcopy(request),script=script,stdin='quit\n',variant='small-fft')


if __name__=='__main__':
    root=capture.geometry.arena.lifetime.ROOT;name='prelude_storage_extended_original.json.gz'
    parent=root/'tests/fixtures/prelude_storage_original.json.gz'
    capture.geometry.arena.main(observer=capture.OBSERVER,fixture_name=name,command_builder=capture.commands,job_factory=jobs,
                                extra_metadata=dict(prelude_storage_parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),prelude_storage_reference='Additional unmodified native square/rectangular FFT inputs. All 130 original observations remain in the parent. Every pre-CAP free buffer, complete earlier heap and independent CAP-entry output heap is retained.'))
    target=root/'tests/fixtures'/name;raw=target.read_bytes()
    fixture=capture.project(json.loads(gzip.decompress(raw)),hashlib.sha256(raw).hexdigest())
    with gzip.GzipFile(str(target),'wb',mtime=0)as stream:stream.write((json.dumps(fixture,separators=(',',':'))+'\n').encode())
