import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs";
import { installNumericalKernels } from "./numeric-kernels.mjs";

const ready = (async () => {
  const python = await loadPyodide();
  const response = await fetch(new URL("reasitic.zip", import.meta.url));
  if (!response.ok) throw new Error("Could not load the simulation package.");
  python.unpackArchive(await response.arrayBuffer(), "zip");
  await installNumericalKernels(python);
  python.runPython(`
from reasitic.fft import _compiled_transform
from reasitic.x87_math import _native_tanh,_native_cosh
from reasitic.symmetric import _compiled_symmetric
from reasitic.contact_kernel import _compiled_contact_pair
from reasitic.linear import _compiled_general
from reasitic.table_kernel import _compiled_tables,_compiled_coefficients
assert all(x is not None for x in (_compiled_transform,_native_tanh,_native_cosh,_compiled_symmetric,_compiled_contact_pair,_compiled_general,_compiled_tables,_compiled_coefficients)), "Could not initialize numerical kernels"
from reasitic.bridge import request_json
`);
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
