"""Native ASITIC eddy-current square packing and segment folding (eddy.cpp)."""
import math
from array import array
from .green import GreenLayers,_guard
from .retained_scalar import Real as _d
from .green_integration import GreenIntegrationState,green_integral

try:
    from _reasitic_numeric import eddy_stamp as _compiled_stamp
except ImportError:
    _compiled_stamp=None

SCALE=float.fromhex("0x1.0c6f7a0b5ed8dp-20")
THRESHOLD=float.fromhex("0x1.b7cdfd9d7bdbbp-34")


@_guard
def configure_eddy(technology):
    indices=technology.eddy_layers
    if not indices:
        raise ValueError("No eddy-current layers are defined in the technology file")
    if any(not 0<=i<len(technology.substrate) for i in indices):
        raise ValueError("Technology references an unknown eddy-current substrate layer")
    def conductivity(index):
        rho=technology.substrate[index]["rho"]
        if rho<=0:
            raise ValueError("Eddy-current layer resistivity must be positive")
        native_rho=float(_d(rho)*10000)
        return float(_d(1e6)/_d(native_rho))
    if len(indices)==1:
        return GreenIntegrationState(GreenLayers(conductivity(indices[0]),0.0,0.0),"reflection")
    high,low=max(indices),min(indices)
    depth=float(_d(SCALE)*_d(technology.substrate[high]["t"]))
    return GreenIntegrationState(GreenLayers(conductivity(high),conductivity(low),depth),"oscillating")


def packed_index(index,turns):
    return 4*index-3 if index<=turns else 4*turns-(4*(index-1-turns)+1)


def _reflected(index,turns):
    while index>turns:
        index=2*turns-index+1
    return index


def _folded_position(index,dimension,width,spacing,turns):
    offset=_reflected(index,turns)-1
    return (_d(dimension)-_d(width))-(_d(width)+_d(spacing))*(offset+offset)


def _signed_separation(i,j,dimension,width,spacing,turns):
    a,b=_reflected(i,turns)-1,_reflected(j,turns)-1
    step,base=_d(width)+_d(spacing),_d(dimension)-_d(width)
    value=((base-(a+a)*step)*(base-(b+b)*step)).sqrt()
    return -value if (i>turns)!=(j>turns) else value


def _length(wire):
    dx,dy,dz=(_d(wire[i+3])-_d(wire[i]) for i in range(3))
    return ((dx*dx+dy*dy)+dz*dz).sqrt()


def _distance(a,b):
    dx,dy,dz=(_d(a[i])-_d(b[i]) for i in range(3))
    return ((dx*dx+dy*dy)+dz*dz).sqrt()


@_guard
def classify_pair(a,b):
    ax,ay,az=(_d(a[i+3])-_d(a[i]) for i in range(3))
    bx,by,bz=(_d(b[i+3])-_d(b[i]) for i in range(3))
    dot=(ax*bx+by*ay)+az*bz
    product=float(dot)
    if _d(THRESHOLD)>abs(dot):
        return 7,product
    al,bl=float(_length(a)),float(_length(b))
    distances=[float(_distance(a,b)),float(_distance(a,b[3:])),float(_distance(a[3:],b)),_distance(a[3:],b[3:])]
    nearest=distances[0] if distances[0]<distances[1] else distances[1]
    for value in distances[2:]:
        if not nearest<value:
            nearest=value
    shorter=min(al,bl)
    if _d(shorter)/2<nearest:
        return 9,product
    cosine=_d(product)/(_d(al)*_d(bl))
    return (0 if _d(float.fromhex("0x1.fe0ded288ce70p-1"))<=abs(cosine) else 9),float(cosine)


def _wire(segment):
    return segment.start+segment.end+[segment.width if segment.primary_width is None else segment.primary_width]


def _axial_length(wire):
    return _length(wire)-(_d(wire[6])+_d(wire[6]))


def _stamp_compiled(matrix,shape,technology,frequency,mode,state,warnings):
    n=len(matrix);square=shape.kind=="square" and mode==1;p=shape.parameters
    if square:
        metal=technology.metal_index(p.get("metal",len(technology.metals)-1))
        geometry=[p.get("length",100),p.get("width",5),p.get("spacing",2),p["turns"],technology.metals[metal].geometry_height]
        size=2*math.ceil(p["turns"])
    else:geometry=[0.]*5;size=0
    if len(shape.segments)>2048 or n>256 or size>256:return None
    config=array("d",[1,len(shape.segments),n,len(technology.metals),mode,int(square),frequency,SCALE,*geometry,*state.history,*([0.]*8)])
    config[16:20]=array("d",[state.layers.layer1,state.layers.layer2,state.layers.depth,float(state.kernel=="oscillating")])
    wires=array("d",(v for s in shape.segments for v in [*_wire(s),s.metal]))
    data=array("d",(v for j in range(n) for i in range(n) for v in (matrix[i][j].real,matrix[i][j].imag)))
    output=array("d",[0.])*(32+size*size)
    status=_compiled_stamp(config,wires,data,output)
    if status:raise ValueError("Native square eddy packing exceeds this segment matrix" if status==-3 else "Invalid eddy matrix configuration")
    for i in range(n):
        for j in range(n):matrix[i][j]=complex(data[2*(j*n+i)],data[2*(j*n+i)+1])
    for i in range(16):
        if i%8 and output[i+1]:warnings.append(f"ASITIC {'DQAWFE' if i>=8 else 'DQAGIE'} did not converge (status {i%8}); native partial result retained")
    state.history[:]=output[17:20]
    info=dict(mode=mode,kernel=state.kernel,layers=technology.eddy_layers.copy(),green_calls=int(output[0]))
    if size:info["matrix"]=[[output[32+j*size+i] for j in range(size)] for i in range(size)]
    return info


@_guard
def assemble_square(dimension,width,spacing,turns,frequency,height,integral):
    n=math.ceil(turns);size=2*n
    dimension,width=float(_d(SCALE)*_d(dimension)),float(_d(SCALE)*_d(width))
    spacing_extended=_d(SCALE)*_d(spacing)
    pitch_extended=spacing_extended+_d(width)
    spacing,pitch=float(spacing_extended),float(pitch_extended)
    inner=float(_d(float(_d(dimension)-((n-1)+(n-1))*pitch_extended))-(_d(width)+_d(width)))
    matrix=[[0.0]*size for _ in range(size)]
    diagonal=float(integral(frequency,0.0,height,width))
    for i in range(1,size+1):
        matrix[i-1][i-1]=float(_folded_position(i,dimension,width,spacing,n)*_d(diagonal))
    for i in range(1,n+1):
        for j in range(i+1,n+1):
            factor=_signed_separation(i,j,dimension,width,spacing,n)
            if i==1:
                matrix[0][j-1]=float(factor*_d(integral(frequency,float(_d(pitch)*(j-1)),height,width)))
            else:
                previous=_signed_separation(i-1,j-1,dimension,width,spacing,n)
                matrix[i-1][j-1]=float((factor*_d(matrix[i-2][j-2]))/previous)
    for i in range(1,n+1):
        factor=_signed_separation(i,n+1,dimension,width,spacing,n)
        matrix[i-1][n]=float(factor*_d(integral(frequency,float(_d(pitch)*(n-i)+_d(inner)),height,width)))
    for i in range(1,n+1):
        for j in range(n+2,size+1):
            factor=_signed_separation(i,j,dimension,width,spacing,n)
            if i==1:
                matrix[0][j-1]=float(factor*_d(integral(frequency,float(_d(pitch)*(j-2)+_d(inner)),height,width)))
            else:
                previous=_signed_separation(i-1,j-1,dimension,width,spacing,n)
                matrix[i-1][j-1]=float((factor*_d(matrix[i-2][j-2]))/previous)
    for i in range(n+1,size+1):
        for j in range(n+2,size+1):
            factor=_signed_separation(i,j,dimension,width,spacing,n)
            previous=_signed_separation(i-n,j-n,dimension,width,spacing,n)
            matrix[i-1][j-1]=float((factor*_d(matrix[i-n-1][j-n-1]))/previous)
    for i in range(1,size+1):
        for j in range(1,i):
            matrix[i-1][j-1]=matrix[j-1][i-1]
    return matrix


@_guard
def add_eddy(matrix,shape,technology,frequency,mode,warnings,*,observe_integral=None):
    """Stamp the reduced impedance matrix in place; preserve native mesh indices."""
    if shape.kind=="square" and mode==1 and not technology.eddy_layers:
        warnings.append("Warning: No valid eddy current layers defined; native square correction skipped")
        return dict(mode=mode,kernel=None,layers=[],green_calls=0,skipped=True)
    state=configure_eddy(technology)
    if _compiled_stamp is not None and observe_integral is None:
        info=_stamp_compiled(matrix,shape,technology,frequency,mode,state,warnings)
        if info is not None:
            if any(not math.isfinite(z.real) or not math.isfinite(z.imag) for row in matrix for z in row):
                raise ValueError("The native eddy path produced a nonfinite impedance matrix; review short/wide segments, longitudinal mesh and process layers")
            return info
    calls=0
    def integral(f,separation,height,width):
        nonlocal calls
        calls+=1
        result=green_integral(f,separation,height,width,state)
        if observe_integral is not None:observe_integral(f,separation,height,width,result)
        if result.status:
            warnings.append(f"ASITIC {result.method} did not converge (status {result.status}); native partial result retained")
        return result.retained_value
    info=dict(mode=mode,kernel=state.kernel,layers=technology.eddy_layers.copy())
    if shape.kind=="square" and mode==1:
        p=shape.parameters
        metal=technology.metal_index(p.get("metal",len(technology.metals)-1))
        height=float(_d(float.fromhex("0x1.0c6f7a0b5ed8dp-19"))*_d(technology.metals[metal].geometry_height))
        real=assemble_square(p.get("length",100),p.get("width",5),p.get("spacing",2),p["turns"],frequency,height,integral)
        n,size=math.ceil(p["turns"]),len(real)
        limit=math.floor(_d(p["turns"])*4)
        for i in range(1,size):
            for j in range(1,size):
                row,column=packed_index(i,n)-1,packed_index(j,n)-1
                for r,c in ((row,column),(row+1,column+1)):
                    if r<limit and c<limit:
                        if not (0<=r<len(matrix) and 0<=c<len(matrix)):
                            raise ValueError("Native square eddy packing exceeds this segment matrix")
                        value=matrix[r][c]
                        matrix[r][c]=complex(float(_d(real[i-1][j-1])+_d(value.real)),value.imag)
        info["matrix"]=real
    else:
        metals=len(technology.metals)
        row=0
        for segment in shape.segments:
            if segment.metal>=metals:continue
            wire=_wire(segment)
            height=float((_d(SCALE)+_d(SCALE))*_d(wire[2]));width=float(_d(SCALE)*_d(wire[6]))
            term=(_axial_length(wire)*_d(SCALE))*_d(integral(frequency,0.0,height,width))
            value=matrix[row][row];matrix[row][row]=complex(float(_d(value.real)+term),value.imag)
            row+=1
        row=0
        for i,a in enumerate(shape.segments):
            if a.metal>=metals:continue
            column=row+1
            for b in shape.segments[i+1:]:
                if column>=len(matrix):break
                aw,bw=_wire(a),_wire(b)
                classification,product=classify_pair(aw,bw)
                if classification==0:
                    dx,dz=_d(aw[0])-_d(bw[0]),abs(_d(aw[2])-_d(bw[2]))
                    if not (abs(dx)<_d(THRESHOLD) and dz<_d(THRESHOLD)):
                        distance=_distance(aw,bw)
                        square=(distance*distance-dx*dx)-dz*dz
                        separation=_d(0) if _d(THRESHOLD)>abs(square) else square.sqrt()*_d(SCALE)
                        al,bl=float(_axial_length(aw)),float(_axial_length(bw))
                        length=(_d(al)*_d(bl)).sqrt()*_d(SCALE)
                        height=float((_d(aw[2])+_d(bw[2]))*_d(SCALE));width=float(_d(aw[6])*_d(SCALE))
                        term=(length*_d(product))*_d(integral(frequency,float(separation),height,width))
                        for r,c in ((row,column),(column,row)):
                            value=matrix[r][c];matrix[r][c]=complex(float(_d(value.real)+term),value.imag)
                # Native off-diagonal traversal consumes columns for vias too.
                column+=1
            row+=1
    info["green_calls"]=calls
    if any(not math.isfinite(z.real) or not math.isfinite(z.imag) for row in matrix for z in row):
        raise ValueError("The native eddy path produced a nonfinite impedance matrix; review short/wide segments, longitudinal mesh and process layers")
    return info
