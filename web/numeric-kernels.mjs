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
  const contactConfig = new Float64Array(api.memory.buffer, api.contact_config_buffer(), 4096);
  const contactTables = new Float64Array(api.memory.buffer, api.contact_table_buffer(), 2 * (66049 + 1024));
  const generalMatrix = new Float64Array(api.memory.buffer, api.general_buffer(), 2 * 514 * 514);
  const generalRhs = new Float64Array(api.memory.buffer, api.general_rhs_buffer(), 2 * 514);
  const generalPivots = new Int32Array(api.memory.buffer, api.general_pivots_buffer(), 514);
  const spectralConfig = new Float64Array(api.memory.buffer, api.spectral_config_buffer(), 2048);
  const spectralTables = new Float64Array(api.memory.buffer, api.spectral_table_buffer(), 2 * (66049 + 1024));
  const spectralDepths = new Float64Array(api.memory.buffer, api.spectral_depth_buffer(), 257);
  const transformerData = new Float64Array(api.memory.buffer, api.transformer_buffer(), 24);
  function spectralCall(config,output,probe) {
    let c,o;
    try {
      c=config.getBuffer("f64");o=output.getBuffer("f64");
      const [version,nx,ny,nm,nl]=c.data;
      if(version!==1||![nm,nl].every(v=>Number.isInteger(v)&&v>=1&&v<=256)||
         ![nx,ny].every(v=>Number.isInteger(v)&&v>=2&&v<=256&&!(v&(v-1)))||c.data.length!==10+3*nm+3*nl)
        throw new Error("Spectral configuration is invalid");
      const cells=Math.max((nx+1)*(ny+1),nx*(nx+1)+ny+1),count=probe?nl+3:4*nx+4*ny+2*cells;
      if(o.data.length!==count)throw new Error("Spectral output length is invalid");
      spectralConfig.set(c.data);
      const status=probe?api.spectral_probe(...probe):api.spectral_tables();
      if(probe){o.data.set(spectralTables.subarray(0,2));o.data.set(spectralDepths.subarray(0,nl+1),2);}
      else o.data.set(spectralTables.subarray(0,count));
      return status;
    } finally {o?.release();c?.release();}
  }
  python.registerJsModule("_reasitic_numeric", {
    transformer_model(buffer,operation) {
      if(![0,1].includes(operation))throw new Error("Transformer operation is invalid");
      const view=buffer.getBuffer("f64");
      try {
        if(view.data.length!==24)throw new Error("Transformer buffer length is invalid");
        transformerData.set(view.data);const status=api.transformer_model(operation);view.data.set(transformerData);return status;
      } finally {view.release();}
    },
    layer_coefficients(buffer) {
      const view=buffer.getBuffer("f64");
      try {
        const [version,n]=view.data;
        if(version!==1||!Number.isInteger(n)||n<1||n>256||view.data.length!==3+4*n)throw new Error("Layer coefficient configuration is invalid");
        spectralConfig.set(view.data);
        const status=api.layer_coefficients();view.data.set(spectralConfig.subarray(0,view.data.length));return status;
      } finally {view.release();}
    },
    spectral_tables: (config,output) => spectralCall(config,output),
    spectral_probe: (config,output,...args) => spectralCall(config,output,args),
    tanh_argument: (k,a,b) => api.tanh_argument(k,a,b),
    cosh_argument: (k,a,b,rounded) => api.cosh_argument(k,a,b,rounded),
    general(buffer,n,operation) {
      if(!Number.isInteger(n)||n<1||n>514||![0,1,2,3].includes(operation))throw new Error("General matrix dimensions or operation are invalid");
      const view=buffer.getBuffer("f64");
      try {
        const count=2*n*n;
        if(view.data.length!==count+3*n)throw new Error("General matrix buffer length is invalid");
        generalMatrix.set(view.data.subarray(0,count));
        if(operation===2){
          for(let i=0;i<n;i++){
            const p=view.data[count+i];
            if(!Number.isInteger(p)||p<1||p>n)throw new Error("General matrix pivot is invalid");
            generalPivots[i]=p;
          }
        }
        if(operation>=2)generalRhs.set(view.data.subarray(count+n));
        const status=api.general(n,operation);
        view.data.set(generalMatrix.subarray(0,count));
        for(let i=0;i<n;i++)view.data[count+i]=generalPivots[i];
        if(operation>=2)view.data.set(generalRhs.subarray(0,2*n),count+n);
        return status;
      } finally { view.release(); }
    },
    contact_pair(config, tables, output) {
      let c,t,o;
      try {
        c=config.getBuffer("f64");t=tables.getBuffer("f64");o=output.getBuffer("f64");
        const [version,n,nx,ny,nm,nl]=c.data;
        if(version!==1 || ![n,nm,nl].every(v=>Number.isInteger(v)&&v>=1&&v<=256) ||
           ![nx,ny].every(v=>Number.isInteger(v)&&v>=2&&v<=256&&!(v&(v-1)))) throw new Error("Contact dimensions are invalid");
        const cells=Math.max((nx+1)*(ny+1),nx*(nx+1)+ny+1);
        if(c.data.length!==17+5*n+3*nm+3*nl || t.data.length!==4*nx+4*ny+2*cells || o.data.length!==2*n*n)
          throw new Error("Contact buffer length is invalid");
        contactConfig.set(c.data);contactTables.set(t.data);matrix.set(o.data);
        const status=api.contact_pair();
        o.data.set(matrix.subarray(0,o.data.length));
        return status;
      } finally { o?.release();t?.release();c?.release(); }
    },
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
