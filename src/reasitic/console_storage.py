"""Source console emitters and successful, already-buffered i386 FILE stores.

The message templates follow console_runtime.cpp, potential_solver.cpp,
potential_cache.cpp, potential_tables.cpp and solver.cpp in the reference.
Only earlier FILE bindings/control inputs enter this object. Observed native
messages are never inputs. Buffer tails survive fflush, as in glibc libio.
Line/unbuffered streams, IO errors and timed/dump analysis need other paths.
"""
import math,struct
from .retained_scalar import Real


class ConsoleStorage:
    def __init__(self,inputs):
        self.inputs=inputs;self.memory=None;self.calls=[]
        self.position=dict(setup_events=0,prefix_events=0,events=0)
        if inputs['timing']or inputs['matrix_dump']:
            raise ValueError('Console storage requires the untimed, nondump analysis path')

    def initial_regions(self,known_regions=()):
        regions=[]
        for stream in self.inputs['streams'].values():
            if stream is None:continue
            address=stream['address'];data=bytes.fromhex(stream['data'])
            for start,raw in known_regions:
                if start<=address and address+len(data)<=start+len(raw):
                    if raw[address-start:address-start+len(data)]!=data:raise ValueError('Conflicting earlier console FILE bytes')
                    break
            else:regions.append((address,data))
        return tuple(regions)

    def bind(self,memory):
        if self.memory is not None:raise ValueError('Console memory is already bound')
        for address,data in self.initial_regions():
            if memory.read(address,len(data))!=data:raise ValueError('Earlier console FILE prefix differs from initial memory')
        self.memory=memory

    def _write(self,name,data):
        stream=self.inputs['streams'].get(name)
        if stream is None:raise ValueError('Console emitter requires an open '+name+' stream')
        self.write_stream(stream['address'],data)

    def write_stream(self,address,data):
        """The same flushed narrow stream path, including the input log."""
        memory=self.memory
        flags,rp,re,rb,wb,wp,we,bb,be=struct.unpack('<9I',memory.read(address,36))
        if flags&0x20a or not flags&0x800 or not bb or not bb<be or not bb<=wp<=be or (rp,re,rb,wb,we)!=(bb,bb,bb,bb,be):
            raise ValueError('Unsupported console FILE buffering state')
        offset=0
        while offset<len(data):
            if wp==be:wp=bb
            count=min(be-wp,len(data)-offset)
            memory.write(wp,data[offset:offset+count]);wp+=count;offset+=count
        # Every console emitter explicitly fflushes every stream it uses.
        # A successful flush resets the put pointer without clearing bytes.
        memory.put_u32(address+20,bb)

    def emit(self,kind,text,to_log=True):
        text=text.encode()if isinstance(text,str)else bytes(text)
        record=dict(kind=kind,text=text.hex(),**self.position)
        if kind in ('message','error'):record['to_log']=bool(to_log)
        self.calls.append(record)
        if kind=='status':self._write('stdout',b'\r'+text);return
        if kind=='output':
            self._write('stdout',text);self._write('log',text)
            if self.inputs['recording']:self._write('recording',text)
            return
        if kind not in ('message','error'):raise ValueError('Unknown source console emitter')
        self._write('stdout',b'\n'+text)
        logged=b'\n'+text+(b'\n'if kind=='error'else b'')
        if to_log:self._write('log',logged)
        if self.inputs['recording']:self._write('recording',logged)

    def warning(self,text):self.emit('error',text,bool(self.inputs['streams'].get('log')))
    def dot(self):
        if self.inputs['progress']:self.emit('output','.')

    def begin_capacitance(self,frequency):
        self.ghz=float(Real(frequency)/Real(1e9))
        if self.inputs['progress']:self.warning(f'Performing Analysis at {self.ghz:.2f} GHz')

    def contacts_ready(self,count):
        if self.inputs['progress']:self.warning(f'Generating capacitance matrix ({count}x{count}).')

    def missing_cache(self):
        self.warning(f'Warning:  Could not open data file at frequency = {self.ghz:.2f}.')
        self.warning(b'Tried using '+bytes.fromhex(self.inputs['directory'])+b' as path.')
        self.warning(f'\n\nGenerating data at {self.ghz:.2f} GHz...')
        self.warning('')

    def begin_table(self):
        self.emit('status','Calculating Green Function...')

    def table_ready(self):
        self.emit('status','Computing FFTs...            ')

    def before_numerical(self,event,filaments,has_vias):
        name=event.name;allocate=event.action=='allocate'
        if allocate and name=='cap.inverse.pivots':self.dot()
        if not allocate and name=='contact.0.0':self.dot()
        if allocate and name=='ind.full'and self.inputs['progress']:
            self.warning(f'Generating inductance matrix ({filaments}x{filaments}).')
        if allocate and name=='ind.full_inverse.work':
            self.dot();self.warning('Inverting matrix...')
        if allocate and name=='ind.zero_temporary':self.dot()
        if (allocate and name=='ind.reduced_inverse.work')or(not allocate and name=='ind.full'and not has_vias):self.dot()

    def after_numerical(self,event):
        # The final dot precedes entry into add_via_impedance, whose own
        # scratch allocation occurs after the independent via-entry boundary.
        if event.action=='free'and event.name=='ind.reduced_inverse.work':self.dot()

    def begin_nodes(self,nodes):
        if self.inputs['progress']:self.warning(f'Solving node equations...({nodes}x{nodes})')

    def report_nodes(self,ports,frequency,*,transformer=False):
        def field(value,spec):
            if math.isnan(value):
                text='-nan'if struct.pack('<d',value)[-1]&128 else'nan'
                width=spec.split('.',1)[0];return text.rjust(int(width))if width.isdecimal()else text
            return format(value,spec)
        def scaled(value,unit):return float(Real(value)/Real(unit))
        ghz=field(scaled(frequency,1e9),'<4.2f')
        if transformer:
            from .transformer import extract_transformer_equivalent
            model,_=extract_transformer_equivalent(ports,frequency)
            f=lambda key:field(scaled(model[key],1e-9)if key.endswith('_h')else model[key],'6.3g')
            self.warning('Narrowband Model at f='+ghz+' GHz:')
            self.warning('L1='+f('first_inductance_h')+'  R1='+f('first_resistance_ohm')+'  L2='+f('second_inductance_h')+' R2='+f('second_resistance_ohm')+' M='+f('mutual_h')+' (k='+f('coupling')+') RG = '+f('ground_resistance_ohm'))
            return model
        from .network_metrics import _extract,_resonance
        model=_extract(ports,frequency)
        self.warning('Pi Model at f='+ghz+' GHz:  Q = '+','.join(field(value,'4.3f')for value in (model.quality_first,model.quality_second,model.quality_differential)))
        self.warning('L  ='+field(scaled(model.inductance,1e-9),'6.3g')+' nH\tR  ='+field(model.resistance,'6.3g')
                     +'\nCs1='+field(scaled(model.capacitance_second,1e-15),'6.3g')+' fF\tRs1='+field(model.resistance_second,'6.3g')
                     +'\nCs2='+field(scaled(model.capacitance_first,1e-15),'6.3g')+' fF\tRs2='+field(model.resistance_first,'6.3g')
                     +'\tf_res = '+field(float(_resonance(model)*Real(1e-9)),'5.2f')+'GHz')
        return model
