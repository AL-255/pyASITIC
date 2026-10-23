// One call per FFT/grid; Python owns the input/output buffer. All retained
// arithmetic runs inside the separate, bounded SoftFloat WebAssembly memory.
export async function installNumericalKernels(python, bytes) {
  if (!bytes) {
    const response = await fetch(new URL("numeric.wasm", import.meta.url));
    if (!response.ok) throw new Error(`Numerical kernel download failed: ${response.status}`);
    bytes = await response.arrayBuffer();
  }
  const { instance } = await WebAssembly.instantiate(bytes);
  const api = instance.exports;
  const storage = new Float64Array(api.memory.buffer, api.buffer(), 2 * 66049);
  const matrix = new Float64Array(api.memory.buffer, api.matrix_buffer(), 2 * 256 * 256);
  const pivots = new Int32Array(api.memory.buffer, api.pivots_buffer(), 256);
  python.registerJsModule("_reasitic_numeric", {
    tanh_argument: (k,a,b) => api.tanh_argument(k,a,b),
    cosh_argument: (k,a,b,rounded) => api.cosh_argument(k,a,b,rounded),
    symmetric(buffer, n, invert) {
      if (!Number.isInteger(n) || n < 1 || n > 256) throw new Error("Symmetric matrix dimension is out of range");
      const view = buffer.getBuffer("f64");
      try {
        const count = 2 * n * n;
        if (view.data.length !== count + n) throw new Error("Symmetric matrix buffer length is invalid");
        matrix.set(view.data.subarray(0, count));
        const status = invert ? api.inverse(n) : api.factor(n);
        view.data.set(matrix.subarray(0, count));
        for (let i=0;i<n;i++) view.data[count+i] = pivots[i];
        return status;
      } finally { view.release(); }
    },
    transform(buffer, nx, ny) {
      if (!Number.isInteger(nx) || !Number.isInteger(ny)) throw new Error("FFT dimensions must be integers");
      if (!nx && !ny) return;
      const view = buffer.getBuffer("f64");
      try {
        const required = ny ? (nx + 1) * (ny + 1) : nx;
        if (view.data.length < required * 2 || view.data.length > storage.length) throw new Error("FFT buffer length is invalid");
        storage.set(view.data);
        const status = ny ? api.grid(nx, ny) : api.fft(nx);
        if (status) throw new Error("FFT dimensions exceed the supported power-of-two range");
        view.data.set(storage.subarray(0, view.data.length));
      } finally { view.release(); }
    }
  });
}
