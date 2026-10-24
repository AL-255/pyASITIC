"""Capture whole-pair threshold, orientation and degeneracy cases independently."""
import argparse
import json
import math
from pathlib import Path
from capture_mutual import capture,ROOT


def cases():
    rows=[]
    def add(label,a,b,orders=True):
        def reverse(wire):return [*wire[3:6],*wire[:3],*wire[6:]]
        variants=[('forward',a,b)]
        if orders:variants.extend([('reverse-first',reverse(a),b),('reverse-second',a,reverse(b)),('swap',b,a)])
        for order,first,second in variants:rows.append(dict(mode=4,label=label+'/'+order,input=[*first,*second]))
    def wire(x,y,z,dx,dy,dz,width=5.,thickness=1.):return [x,y,z,x+dx,y+dy,z+dz,width,thickness]
    for theta in (0.,1e-12,1e-9,1e-6,.01,.3,1.,math.nextafter(math.pi/2,0.),math.pi/2,math.nextafter(math.pi/2,math.inf),math.pi-1e-9,math.pi):
        for height in (0.,1e-6,.5):
            a=wire(0.,0.,1.3,40.,0.,0.)
            b=wire(10.,30.,1.3+height,30.*math.cos(theta),30.*math.sin(theta),0.)
            add(f'angle={theta.hex()}/height={height.hex()}',a,b)
    for length in (math.nextafter(1e-6,0.),1e-6,math.nextafter(1e-6,math.inf),1e-5,1e-4):
        for axis in range(3):
            d=[0.,0.,0.];d[axis]=length
            add(f'normalization={length.hex()}/axis={axis}',wire(0.,0.,0.,*d),wire(10.,20.,30.,1e6,2e6,3e6))
    for height in (math.nextafter(1e-6,0.),1e-6,math.nextafter(1e-6,math.inf),-1e-6,0.,-0.):
        add(f'coplanarity={height.hex()}',wire(0.,0.,0.,40.,0.,0.),wire(10.,30.,height,12.,15.,0.))
    for translation in (0.,5000.,-5000.,1e8,-1e8,1e12):
        for height in (0.,1.1):
            add(f'translation={translation.hex()}/height={height.hex()}',wire(translation,translation,1.3,40.,0.,0.),wire(translation+10.,translation+30.,1.3+height,12.,15.,3.))
    for length in (0.,-0.,1e-310,1e-250,1e-12,1e-6,1.,1e250,1e308):
        add(f'length={length.hex()}',wire(0.,0.,0.,length,0.,0.),wire(0.,10.,1.,30.,0.,0.))
    for x in (0.,1e-9,1.,10.,20.,30.,40.,50.):
        for y in (0.,1e-6,1e-3):
            add(f'intersection={x.hex()}/{y.hex()}',wire(0.,0.,0.,40.,0.,0.),wire(x,y,0.,10.,0.,0.))
    base=wire(0.,0.,1.3,40.,0.,0.);other=wire(10.,30.,4.5,30.,0.,0.)
    for value in (math.nan,math.inf,-math.inf):
        for field in (0,2,3,5,6,7):
            a=base.copy();a[field]=value
            add(f'nonfinite={value}/field={field}',a,other,orders=False)
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True)
    result=capture(parser.parse_args().reference,cases())
    result['reference']='Independent whole-pair threshold/degeneracy cases execute the intact original segment routine at 0x08061110. No instruction substitutes, runtime replacements or calculated expected outputs.'
    (ROOT/'tests/fixtures/mutual_boundaries_original.json').write_text(json.dumps(result,separators=(',',':'),allow_nan=False)+'\n')
    print(len(result['cases']),'intact-original whole-pair boundary cases captured')


if __name__=='__main__':main()
