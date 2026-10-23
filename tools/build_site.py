"""Build a static Pages artifact, including one archive of the Python source."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT/"dist"
DIST.mkdir(exist_ok=True)
web_sources=sorted(file for file in (ROOT/"web").iterdir() if file.is_file())
python_sources=sorted(source for source in (ROOT/"src/reasitic").rglob("*") if source.is_file() and source.suffix in (".py",".tek",".json",".txt"))
digest=hashlib.sha256()
for source in web_sources+python_sources+[Path(__file__).resolve()]:
    digest.update(source.relative_to(ROOT).as_posix().encode()+b"\0"+source.read_bytes())
version=digest.hexdigest()[:16]
for file in web_sources:
    if file.is_file():
        shutil.copyfile(file,DIST/file.name)
with zipfile.ZipFile(DIST/"reasitic.zip","w",zipfile.ZIP_DEFLATED) as archive:
    for source in python_sources:
        archive.write(source,"reasitic/"+source.relative_to(ROOT/"src/reasitic").as_posix())
for name,replacements in {
    "index.html":{'src="app.js"':f'src="app.js?v={version}"','href="style.css"':f'href="style.css?v={version}"'},
    "app.js":{'"./analysis-views.mjs"':f'"./analysis-views.mjs?v={version}"','"worker.js"':f'"worker.js?v={version}"'},
    "worker.js":{'"reasitic.zip"':f'"reasitic.zip?v={version}"','"./numeric-kernels.mjs"':f'"./numeric-kernels.mjs?v={version}"'},
    "numeric-kernels.mjs":{'"numeric.wasm"':f'"numeric.wasm?v={version}"'},
}.items():
    target=DIST/name
    text=target.read_text()
    for old,new in replacements.items():
        if old not in text:
            raise ValueError(f"Missing versioned asset reference in {name}: {old}")
        text=text.replace(old,new)
    target.write_text(text)
(DIST/"version.json").write_text(json.dumps(dict(version=version))+"\n")
(DIST/".nojekyll").touch()
print(DIST)
