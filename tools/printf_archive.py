"""Verified streaming access to complete native captures split for Git."""
import gzip,hashlib,io,json
from pathlib import Path


class JoinedFiles(io.RawIOBase):
    def __init__(self,paths):super().__init__();self.paths=iter(paths);self.current=None
    def readable(self):return True
    def readinto(self,buffer):
        view=memoryview(buffer);count=0
        while count<len(view):
            if self.current is None:
                try:self.current=next(self.paths).open('rb')
                except StopIteration:break
            used=self.current.readinto(view[count:])
            if used:count+=used
            else:self.current.close();self.current=None
        return count
    def close(self):
        if self.current is not None:self.current.close();self.current=None
        super().close()


def read_fixture(path):
    path=Path(path)
    if path.name.endswith('.gz'):
        with gzip.open(path,'rt')as stream:return json.load(stream)
    manifest=json.loads(path.read_text())
    if manifest.get('format')!='printf-capture-parts'or manifest.get('version')!=1:raise ValueError('Unknown printf archive manifest')
    archive_hash=hashlib.sha256();paths=[];total=0;names=set()
    for part in manifest['parts']:
        name=part['file']
        if not isinstance(name,str)or Path(name).name!=name or name in ('.','..')or name in names:raise ValueError('Invalid printf archive part name')
        names.add(name);target=path.parent/name;part_hash=hashlib.sha256();size=0
        with target.open('rb')as stream:
            while chunk:=stream.read(1024*1024):part_hash.update(chunk);archive_hash.update(chunk);size+=len(chunk)
        if size!=part['bytes']or part_hash.hexdigest()!=part['sha256']:raise ValueError('Invalid printf archive part content')
        total+=size;paths.append(target)
    if not paths or total!=manifest['bytes']or archive_hash.hexdigest()!=manifest['sha256']:raise ValueError('Invalid complete printf archive content')
    with JoinedFiles(paths)as chain,io.BufferedReader(chain)as buffer,gzip.GzipFile(fileobj=buffer)as binary,io.TextIOWrapper(binary,encoding='utf-8')as text:f=json.load(text)
    if len(f['cases'])!=manifest['histories']or f['parents']!=manifest['parents']:raise ValueError('Printf archive metadata differs from manifest')
    return f


def split_archive(source,target,*,histories,parents,part_bytes=32*1024*1024):
    source,target=Path(source),Path(target)
    if not target.name.endswith('.manifest.json')or part_bytes<1:raise ValueError('Require a manifest filename and positive part size')
    parts=[];digest=hashlib.sha256();total=0;prefix=target.name[:-len('.manifest.json')]
    with source.open('rb')as stream:
        while chunk:=stream.read(part_bytes):
            name=prefix+'.json.gz.'+str(len(parts)+1).zfill(3);(target.parent/name).write_bytes(chunk)
            digest.update(chunk);total+=len(chunk);parts.append(dict(file=name,bytes=len(chunk),sha256=hashlib.sha256(chunk).hexdigest()))
    manifest=dict(format='printf-capture-parts',version=1,histories=histories,parents=parents,bytes=total,sha256=digest.hexdigest(),parts=parts)
    temporary=target.with_name(target.name+'.tmp');temporary.write_text(json.dumps(manifest,indent=2)+'\n');temporary.replace(target);return manifest
