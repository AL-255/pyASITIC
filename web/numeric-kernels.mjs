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
  const networkMetricInput = new Float64Array(api.memory.buffer, api.network_metric_buffer(), 256*26);
  const networkMetricOutput = new Float64Array(api.memory.buffer, api.network_metric_result_buffer(), 256*42);
  const impedanceWires = new Float64Array(api.memory.buffer, api.impedance_wire_buffer(), 256*10);
  const impedanceMutual = new Float64Array(api.memory.buffer, api.impedance_mutual_buffer(), 256*255/2);
  const impedanceMatrix = new Float64Array(api.memory.buffer, api.impedance_matrix_buffer(), 2*256*256);
  const conductorResistance = new Float64Array(api.memory.buffer, api.conductor_resistance_buffer(), 20000*12);
  const conductorResistanceOutput = new Float64Array(api.memory.buffer, api.conductor_resistance_result_buffer(), 4);
  const geometryMetrics = new Float64Array(api.memory.buffer, api.geometry_metrics_buffer(), 20000*7);
  const geometryMetricsOutput = new Float64Array(api.memory.buffer, api.geometry_metrics_result_buffer(), 6);
  const conductorMetrics = new Float64Array(api.memory.buffer, api.conductor_metrics_buffer(), 2000*16);
  const conductorMetricsOutput = new Float64Array(api.memory.buffer, api.conductor_metrics_result_buffer(), 9);
  const couplingMetrics = new Float64Array(api.memory.buffer, api.coupling_metrics_buffer(), 4000*8+6);
  const couplingMetricsOutput = new Float64Array(api.memory.buffer, api.coupling_metrics_result_buffer(), 4000*8+6);
  const symmetricConfig = new Float64Array(api.memory.buffer, api.symmetric_config_buffer(), 10);
  const symmetricEvents = new Float64Array(api.memory.buffer, api.symmetric_event_buffer(), 60000*14);
  const polygonConfig = new Float64Array(api.memory.buffer, api.polygon_config_buffer(), 6);
  const polygonVertices = new Float64Array(api.memory.buffer, api.polygon_vertex_buffer(), 20000*12);
  const filamentInput = new Float64Array(api.memory.buffer, api.filament_buffer(), 256*26);
  const filamentOutput = new Float64Array(api.memory.buffer, api.filament_result_buffer(), 256*9);
  const mutualInput = new Float64Array(api.memory.buffer, api.mutual_buffer(), 256*18);
  const mutualOutput = new Float64Array(api.memory.buffer, api.mutual_result_buffer(), 256*6);
  const viaInput = new Float64Array(api.memory.buffer, api.via_buffer(), 256*9);
  const viaOutput = new Float64Array(api.memory.buffer, api.via_result_buffer(), 256*2);
  const nodeInput = new Float64Array(api.memory.buffer, api.node_buffer(), 4*256*256);
  const nodeOutput = new Float64Array(api.memory.buffer, api.node_result_buffer(), 8);
  const greenConfig = new Float64Array(api.memory.buffer, api.green_config_buffer(), 12);
  const greenOutput = new Float64Array(api.memory.buffer, api.green_result_buffer(), 3032);
  const eddyConfig = new Float64Array(api.memory.buffer, api.eddy_config_buffer(), 24);
  const eddyWires = new Float64Array(api.memory.buffer, api.eddy_wire_buffer(), 2048*8);
  const eddyMatrix = new Float64Array(api.memory.buffer, api.eddy_matrix_buffer(), 2*256*256);
  const eddyInfo = new Float64Array(api.memory.buffer, api.eddy_info_buffer(), 32);
  const eddySquare = new Float64Array(api.memory.buffer, api.eddy_square_buffer(), 256*256);
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
    symmetric_geometry(config,output) {
      let c,o;
      try {
        c=config.getBuffer("f64");o=output.getBuffer("f64");
        if(c.data.length!==10||!Array.from(c.data).every(Number.isFinite)||![0,1].includes(c.data[0])||
           ![1,2].every(k=>Number.isInteger(c.data[k])&&c.data[k]>=0&&c.data[k]<256)||
           !Number.isInteger(c.data[4])||c.data[4]<4||c.data[4]>1024||c.data[4]%2||
           !Number.isInteger(c.data[8])||c.data[8]<1||c.data[4]*c.data[8]>20000||
           o.data.length%14||o.data.length>60000*14)throw new Error("Symmetric geometry configuration is invalid");
        symmetricConfig.set(c.data);const count=api.symmetric_geometry();
        if(count>0){if(o.data.length<count*14)throw new Error("Symmetric geometry output is too small");o.data.set(symmetricEvents.subarray(0,count*14));}return count;
      } finally {o?.release();c?.release();}
    },
    polygon_spiral(config,output) {
      let c,o;
      try {
        c=config.getBuffer("f64");o=output.getBuffer("f64");
        if(c.data.length!==6||!Array.from(c.data).every(Number.isFinite)||!Number.isInteger(c.data[1])||c.data[1]<3||c.data[1]>1024||c.data[1]*c.data[4]>20000||o.data.length>20000*12)throw new Error("Polygon geometry configuration is invalid");
        polygonConfig.set(c.data);const count=api.polygon_spiral();
        if(count>0){if(o.data.length<count*12)throw new Error("Polygon geometry output is too small");o.data.set(polygonVertices.subarray(0,count*12));}return count;
      } finally {o?.release();c?.release();}
    },
    impedance_assemble(wires,mutual,output,frequency) {
      let w,p,o;
      try {
        w=wires.getBuffer("f64");p=mutual.getBuffer("f64");o=output.getBuffer("f64");const n=w.data.length/10;
        if(!Number.isInteger(n)||n<1||n>256||p.data.length!==n*(n-1)/2||o.data.length!==2*n*n)throw new Error("Filament assembly dimensions are invalid");
        for(let i=0;i<n;i++)if(!Number.isInteger(w.data[10*i+1])||w.data[10*i+1]<1||w.data[10*i+1]>2147483647)throw new Error("Filament thickness count is invalid");
        impedanceWires.set(w.data);impedanceMutual.set(p.data);const status=api.impedance_assemble(n,frequency);
        if(!status)o.data.set(impedanceMatrix.subarray(0,2*n*n));return status;
      } finally {o?.release();p?.release();w?.release();}
    },
    geometry_metrics(input,output) {
      let a,b;
      try {
        a=input.getBuffer("f64");b=output.getBuffer("f64");const count=a.data.length/7;
        if(!Number.isInteger(count)||count<0||count>20000||b.data.length!==6)throw new Error("Geometry metric configuration is invalid");
        geometryMetrics.set(a.data);const status=api.geometry_metrics(count);
        if(!status)b.data.set(geometryMetricsOutput);return status;
      } finally {b?.release();a?.release();}
    },
    coupling_metrics(input,output,firstCount,secondCount) {
      let a,b;
      try {
        a=input.getBuffer("f64");b=output.getBuffer("f64");const length=8*(firstCount+secondCount)+6;
        if(![firstCount,secondCount].every(n=>Number.isInteger(n)&&n>=0&&n<=2000)||firstCount*secondCount>1000000||a.data.length!==length||b.data.length!==length)throw new Error("Coupling metric configuration is invalid");
        couplingMetrics.set(a.data);const status=api.coupling_metrics(firstCount,secondCount);
        if(!status)b.data.set(couplingMetricsOutput.subarray(0,length));return status;
      } finally {b?.release();a?.release();}
    },
    conductor_metrics(input,output) {
      let a,b;
      try {
        a=input.getBuffer("f64");b=output.getBuffer("f64");const count=a.data.length/16;
        if(!Number.isInteger(count)||count<0||count>2000||b.data.length!==9)throw new Error("Conductor metric configuration is invalid");
        for(let i=0;i<count;i++){
          if(![0,1].includes(a.data[16*i+9]))throw new Error("Conductor metric segment type is invalid");
          if(a.data[16*i+9]&&![10,11].every(k=>Number.isInteger(a.data[16*i+k])&&a.data[16*i+k]>=-2147483648&&a.data[16*i+k]<=2147483647))throw new Error("Conductor metric via counts are invalid");
        }
        conductorMetrics.set(a.data);const status=api.conductor_metrics(count);
        if(!status)b.data.set(conductorMetricsOutput);return status;
      } finally {b?.release();a?.release();}
    },
    conductor_resistance(input,output,operation,frequency) {
      let a,b;
      try {
        a=input.getBuffer("f64");b=output.getBuffer("f64");const count=a.data.length/12;
        if(!Number.isInteger(count)||count<0||count>20000||b.data.length!==4||![0,1].includes(operation)||!Number.isFinite(frequency)||frequency<0)throw new Error("Conductor resistance configuration is invalid");
        for(let i=0;i<count;i++){
          if(![0,1].includes(a.data[12*i+9]))throw new Error("Conductor resistance segment type is invalid");
          if(a.data[12*i+9]&&![10,11].every(k=>Number.isInteger(a.data[12*i+k])&&a.data[12*i+k]>=-2147483648&&a.data[12*i+k]<=2147483647))throw new Error("Via resistance counts are invalid");
        }
        conductorResistance.set(a.data);const status=api.conductor_resistance(count,operation,frequency);
        if(!status)b.data.set(conductorResistanceOutput);return status;
      } finally {b?.release();a?.release();}
    },
    network_metrics(input,output,operation=3) {
      let a,b;
      try {
        a=input.getBuffer("f64");b=output.getBuffer("f64");const n=a.data.length/26;
        if(!Number.isInteger(n)||n<1||n>256||b.data.length!==42*n||![0,1,2,3].includes(operation))throw new Error("Network metric dimensions are invalid");
        for(let i=0;i<n;i++)if(![0,1].includes(a.data[26*i])||![0,1,2].includes(a.data[26*i+2])||![0,1].includes(a.data[26*i+3]))throw new Error("Network metric configuration is invalid");
        networkMetricInput.set(a.data);const status=api.network_metrics(n,operation);
        if(!status)b.data.set(networkMetricOutput.subarray(0,42*n));return status;
      } finally {b?.release();a?.release();}
    },
    green_reflection(input,output) {
      let a,b;
      try {
        a=input.getBuffer("f64");b=output.getBuffer("f64");
        if(a.data.length!==8||b.data.length!==3032||!Array.from(a.data.subarray(0,4)).every(Number.isFinite))throw new Error("Green integration configuration is invalid");
        greenConfig.set(a.data);const status=api.green_reflection_integral();
        if(!status)b.data.set(greenOutput);return status;
      } finally {b?.release();a?.release();}
    },
    green_layered(input,output) {
      let a,b;
      try {
        a=input.getBuffer("f64");b=output.getBuffer("f64");
        if(a.data.length!==12||b.data.length!==3032||!Array.from(a.data.subarray(0,4)).every(Number.isFinite)||!Array.from(a.data.subarray(8,11)).every(Number.isFinite))throw new Error("Layered Green integration configuration is invalid");
        greenConfig.set(a.data);const status=api.green_layered_integral();
        if(!status)b.data.set(greenOutput);return status;
      } finally {b?.release();a?.release();}
    },
    eddy_stamp(config,wires,matrix,output) {
      let c,w,a,b;
      try {
        c=config.getBuffer("f64");w=wires.getBuffer("f64");a=matrix.getBuffer("f64");b=output.getBuffer("f64");
        const [version,count,n,metals,mode,square]=c.data;
        if(c.data.length!==24||version!==1||!Number.isInteger(count)||count<1||count>2048||!Number.isInteger(n)||n<1||n>256||!Number.isInteger(metals)||metals<1||metals>256||!Number.isInteger(mode)||mode<1||mode>255||![0,1].includes(square))throw new Error("Eddy configuration is invalid");
        if(![0,1].includes(c.data[19])||!Array.from(c.data.subarray(16,19)).every(Number.isFinite))throw new Error("Eddy layer configuration is invalid");
        const size=square&&mode===1?2*Math.ceil(c.data[11]):0;
        if(!Number.isInteger(size)||size<0||size>256||w.data.length!==8*count||a.data.length!==2*n*n||b.data.length!==32+size*size)throw new Error("Eddy buffer dimensions are invalid");
        for(let i=0;i<count;i++)if(!Number.isInteger(w.data[8*i+7])||w.data[8*i+7]<0||w.data[8*i+7]>65535)throw new Error("Eddy segment metal is invalid");
        eddyConfig.set(c.data);eddyWires.set(w.data);eddyMatrix.set(a.data);const status=api.eddy_stamp();
        if(!status){a.data.set(eddyMatrix.subarray(0,2*n*n));b.data.set(eddyInfo);if(size)b.data.set(eddySquare.subarray(0,size*size),32);}return status;
      } finally {b?.release();a?.release();w?.release();c?.release();}
    },
    folded_node(input,output,n) {
      let a,b;
      try {
        a=input.getBuffer("f64");b=output.getBuffer("f64");
        if(!Number.isInteger(n)||n<1||n>256||a.data.length!==4*n*n||b.data.length!==2*n*n+8)throw new Error("Folded node dimensions are invalid");
        nodeInput.set(a.data);const status=api.folded_node(n);
        b.data.set(nodeInput.subarray(0,2*n*n));b.data.set(nodeOutput,2*n*n);return status;
      } finally {b?.release();a?.release();}
    },
    via_stamp(input,output) {
      let a,b;
      try {
        a=input.getBuffer("f64");b=output.getBuffer("f64");const n=a.data.length/9;
        if(!Number.isInteger(n)||n<1||n>256||b.data.length!==n*2)throw new Error("Via batch dimensions are invalid");
        for(let i=0;i<n;i++)for(const k of [5,6]){
          const value=a.data[9*i+k];
          if(!Number.isInteger(value)||value< -65535||value>65535)throw new Error("Via cell count is invalid");
        }
        viaInput.set(a.data);const status=api.via_stamp(n);b.data.set(viaOutput.subarray(0,n*2));return status;
      } finally {b?.release();a?.release();}
    },
    mutual(input,output) {
      let a,b;
      try {
        a=input.getBuffer("f64");b=output.getBuffer("f64");const n=a.data.length/18;
        if(!Number.isInteger(n)||n<1||n>256||b.data.length!==n*6)throw new Error("Mutual batch dimensions are invalid");
        for(let i=0;i<n;i++)if(![0,1,2,3,4].includes(a.data[18*i]))throw new Error("Mutual operation is invalid");
        mutualInput.set(a.data);const status=api.mutual_probe(n);b.data.set(mutualOutput.subarray(0,n*6));return status;
      } finally {b?.release();a?.release();}
    },
    filaments(input,output) {
      let a,b;
      try {
        a=input.getBuffer("f64");b=output.getBuffer("f64");const n=a.data.length/26;
        if(!Number.isInteger(n)||n<1||n>256||b.data.length!==n*9)throw new Error("Filament batch dimensions are invalid");
        for(let i=0;i<n;i++){
          const p=a.data.subarray(26*i,26*i+26);
          for(const k of [18,19,20,21,22,23,24,25])if(!Number.isInteger(p[k])||p[k]<0||p[k]>65535)throw new Error("Filament count/index is invalid");
          if(!p[18]||!p[22]||!p[23]||!p[24]||p[19]>=p[22]||p[20]>=p[23]||p[21]>=p[24])throw new Error("Filament index is outside its mesh");
        }
        filamentInput.set(a.data);const status=api.filaments(n);b.data.set(filamentOutput.subarray(0,n*9));return status;
      } finally {b?.release();a?.release();}
    },
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
