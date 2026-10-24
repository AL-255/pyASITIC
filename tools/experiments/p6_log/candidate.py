# ============================================================================
# This source file is an extension to the SoftFloat IEC/IEEE Floating-point
# Arithmetic Package, Release 2b, written for Bochs (x86 achitecture simulator)
# floating point emulation.
#
# THIS SOFTWARE IS DISTRIBUTED AS IS, FOR FREE.  Although reasonable effort has
# been made to avoid it, THIS SOFTWARE MAY CONTAIN FAULTS THAT WILL AT TIMES
# RESULT IN INCORRECT BEHAVIOR.  USE OF THIS SOFTWARE IS RESTRICTED TO PERSONS
# AND ORGANIZATIONS WHO CAN AND WILL TAKE FULL RESPONSIBILITY FOR ALL LOSSES,
# COSTS, OR OTHER PROBLEMS THEY INCUR DUE TO THE SOFTWARE, AND WHO FURTHERMORE
# EFFECTIVELY INDEMNIFY JOHN HAUSER AND THE INTERNATIONAL COMPUTER SCIENCE
# INSTITUTE (possibly via similar legal warning) AGAINST ALL LOSSES, COSTS, OR
# OTHER PROBLEMS INCURRED BY THEIR CUSTOMERS AND CLIENTS DUE TO THE SOFTWARE.
#
# Derivative works are acceptable, even for commercial purposes, so long as
# (1) the source code for the derivative work includes prominent notice that
# the work is derivative, and (2) the source code includes prominent notice with
# these four paragraphs for those parts of this code that are retained.
# =============================================================================
"""Isolated P5/P6 log experiment, never imported by the ASITIC simulator.

Translation of Bochs FYL2X/FYL2XP1 evaluation at revision
3e874945d66e5332791b37185d98dec2bfdd2580. Upstream sources, notices and
LGPL-2.1 license are retained alongside this file. This derivative uses exact
rationals for the explicit 67/64/113-bit rounding stages. No fixture words or
input-specific corrections are used. It does not emulate exception flags.
"""
from fractions import Fraction as F
from pathlib import Path
import re
from reasitic.retained_scalar import Real as R,_exponent
source=Path(__file__).with_name('fyl2x_constants.h').read_text()
def decode(hi,lo):
 sig=(1<<112)|((hi&((1<<48)-1))<<64)|lo;e=((hi>>48)&32767)-16383-112
 return (-1 if hi>>63 else 1)*F(sig)*F(2)**e
D={k:int(v,16)for k,v in re.findall(r'#define (FYL2X_\w+) BX_CONST64\(0x([a-fA-F0-9]+)\)',source)}
C={k:decode(D['FYL2X_'+k+'_HI'],D['FYL2X_'+k+'_LO'])for k in ('L_INV','L_INV2','A1','A2','A3','B1','B2','B3','B4','B5','B6')}
arrays={k:[int(h,16)for h in re.findall(r'0x([a-fA-F0-9]+)',body)]for k,body in re.findall(r'static const (?:Bit64u|uint64_t) (\w+)\[32\] = \{(.*?)\};',source,re.S)}
L=[decode(a,b)for a,b in zip(arrays['fyl2x_L_hi'],arrays['fyl2x_L_lo'])]
T=[decode(a,b)for a,b in zip(arrays['fyl2x_T_hi'],arrays['fyl2x_T_lo'])]
def quantize(v,p=67,nearest=False):
 if not v:return F(0)
 negative=v<0;v=abs(v);scale=F(2)**(_exponent(v)-p+1);n,r=divmod(v,scale);n=int(n)
 if nearest and (r*2>scale or r*2==scale and n&1):n+=1
 return (-n if negative else n)*scale
q113=lambda v:quantize(v,113,True)
a67=lambda a,b:quantize(a+b)
m67=lambda a,b:quantize(a*b)
d67=lambda a,b:quantize(a/b)
a64=lambda a,b:R._result(q113(a+b)).value
d64=lambda a,b:R._result(q113(a/b)).value
m64=lambda a,b:R._result(q113(a*quantize(b,64))).value

def table(wm,n):
 sig=int(wm*(1<<63));index=(sig>>58)&31;c=F((sig&(~0<<58))|(1<<57),1<<63)
 r=a64(wm,-c);s=a64(r,r);t=a64(wm,c);u=d64(s,t);e=a64(F(n),L[index]);u1=m67(C['L_INV'],u);v=m67(u,u)
 p=m67(v,C['A3']);p=a64(p,C['A2']);p=m67(v,p);p=a64(p,C['A1']);p=m67(v,p);p=m67(p,u);p=a64(u1,p)
 return a67(e,a67(T[index],p))
def poly(arg,den):
 s=m67(C['L_INV2'],arg);u=d67(s,den);v=m64(u,u);w=m67(v,v)
 p=m67(w,C['B5']);p=a64(p,C['B3']);p=m67(w,p);p=a64(p,C['B1']);p=m67(v,p)
 b=m67(w,C['B6']);b=a64(b,C['B4']);b=m67(w,b);b=a64(b,C['B2']);b=m67(w,b)
 return a67(u,m67(u,a64(p,b)))
LN2=F(0xb17217f7d1cf79ac,1<<64)
def logarithm(value,y=LN2,plus=False):
 value,y=R(value),R(y)
 if plus and not value.value:return R(-0. if value.negative^y.negative else 0.)
 v=value.value;y=y.value
 if plus:
  if abs(v)>=F(1,8):w=a67(v,F(1));n=_exponent(w);z=table(w/F(2)**n,n)
  elif abs(v)<F(1,1<<70):z=m67(C['L_INV'],v)
  else:z=poly(v,a67(v,F(2)))
 elif F(7,8)<v<F(9,8):z=poly(a64(v,F(-1)),a67(v,F(1)))
 else:n=_exponent(v);z=table(v/F(2)**n,n)
 return R._result(q113(z*y))
