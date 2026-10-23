import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs";

const ready = (async () => {
  const python = await loadPyodide();
  const response = await fetch(new URL("reasitic.zip", import.meta.url));
  if (!response.ok) throw new Error("Could not load the simulation package.");
  python.unpackArchive(await response.arrayBuffer(), "zip");
  python.runPython("from reasitic.bridge import request_json");
  self.postMessage({ ready: true });
  return python;
})();
ready.catch(error => self.postMessage({ fatal: String(error) }));

// Serialize requests: all share one Python interpreter.
let queue = Promise.resolve();
self.onmessage = ({ data: { id, request } }) => {
  queue = queue.then(async () => {
    try {
      const python = await ready;
      const call = python.globals.get("request_json");
      try {
        const progress=point=>self.postMessage({id,progress:JSON.parse(point)});
        const result = JSON.parse(request.action==="selfres"?call(JSON.stringify(request),progress):call(JSON.stringify(request)));
        self.postMessage({ id, ...result });
      } finally { call.destroy(); }
    } catch (error) { self.postMessage({ id, error: String(error) }); }
  });
};
