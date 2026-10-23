"""Build a static Pages artifact, including one archive of the Python source."""
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT/"dist"
DIST.mkdir(exist_ok=True)
for file in (ROOT/"web").iterdir():
    if file.is_file():
        shutil.copyfile(file,DIST/file.name)
with zipfile.ZipFile(DIST/"reasitic.zip","w",zipfile.ZIP_DEFLATED) as archive:
    for source in sorted((ROOT/"src/reasitic").iterdir()):
        if source.suffix in (".py",".tek"):
            archive.write(source,"reasitic/"+source.name)
(DIST/".nojekyll").touch()
print(DIST)
