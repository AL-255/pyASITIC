"""Original Green runtime printf messages (recomp_cpp/src/green_integration.cpp).

These are source literals, including the original spelling and cycle indices.
Binary64 arguments use the pinned glibc decimal algorithm, not host formatting.
They are separate from the console error emitter and write only stdout.
"""
import struct
from .printf_float_digits import format_binary64

MESSAGES={'fourier_error': '\nError:  Quadpack DQAWF function did not converge.',
 'arguments': '\nCalled with:  freq = %lg, sep = %lg, h = %lg',
 'max_cycles': '\nMax no. of cycles exceeded.',
 'bad_table': '\n\tThe extrapolation table not good.',
 'invalid': '\n\tThe input is invalid.',
 'bad_integrand': '\n\tBad integrand behavior.',
 'unknown': '\n\tAn unknown error=%d occurred.',
 'infinite_error': '\nError:  Quadpack DQAGI function did not converge.',
 'cycle_short_1': '\nCycle %d:  max no. of sub-divs acheived',
 'cycle_short_2': '\nCycle %d:  round-off error',
 'cycle_short_3': '\nCycle %d:  exrememely bad behavior here',
 'cycle_short_4': '\nCycle %d:  no convergence due to roundoff in extrapolation procedure',
 'cycle_short_5': '\nCycle %d:  slow convergence or divergence',
 'cycle_long_1': '\n'
                 'The maximum number of subdivisions (=(leniw-limlst)/2 has been achieved on the '
                 '%d th cycle.',
 'cycle_long_2': '\n'
                 'Occurrence of roundoff error is detected and prevents the tolerance imposed on '
                 'the %d th cycle, from being achieved on this cycle.',
 'cycle_long_3': '\nExtremely bad integrand behaviour occurs at some points of the %d th cycle.',
 'cycle_long_4': '\n'
                 'The integration procedure over the %d th cycle does not converge (to within the '
                 'required accuracy) due to roundoff in the extrapolation procedure invoked on '
                 'this cycle. it is assumed that the result on this interval is the best which can '
                 'be obtained.',
 'cycle_long_5': '\n'
                 'The integral over the %d th cycle is probably divergent or slowly convergent. it '
                 'must be noted that divergence can occur with any other value of iwork(k).',
 'infinite_status_1': '\n'
                      '\tMaximum number of subdivisions allowed\n'
                      '\thas been achieved. one can allow more\n'
                      '\tsubdivisions by increasing the value of\n'
                      '\tlimit (and taking the according dimension\n'
                      '\tadjustments into account). however, if\n'
                      '\tthis yields no improvement it is advised\n'
                      '\tto analyze the integrand in order to\n'
                      '\tdetermine the integration difficulties. if\n'
                      '\tthe position of a local difficulty can be\n'
                      '\tdetermined (e.g. singularity,\n'
                      '\tdiscontinuity within the interval) one\n'
                      '\twill probably gain from splitting up the\n'
                      '\tinterval at this point and calling the\n'
                      '\tintegrator on the subranges. if possible,\n'
                      '\tan appropriate special-purpose integrator\n'
                      '\tshould be used, which is designed for\n'
                      '\thandling the type of difficulty involved.',
 'infinite_status_2': '\n'
                      '\tThe occurrence of roundoff error is\n'
                      '\tdetected, which prevents the requested\n'
                      '\ttolerance from being achieved.\n'
                      '\tthe error may be under-estimated.',
 'infinite_status_3': '\n'
                      '\tExtremely bad integrand behaviour occurs\n'
                      '\tat some points of the integration interval.',
 'infinite_status_4': '\n'
                      '\tThe algorithm does not converge.\n'
                      '\troundoff error is detected in the\n'
                      '\textrapolation table.\n'
                      '\tit is assumed that the requested tolerance\n'
                      '\tcannot be achieved, and that the returned\n'
                      '\tresult is the best which can be obtained.',
 'infinite_status_5': '\n'
                      '\tThe integral is probably divergent, or\n'
                      '\tslowly convergent. it must be noted that\n'
                      '\tdivergence can occur with any other value\n'
                      '\tof ier.',
 'infinite_status_6': '\n'
                      '\tThe input is invalid, because\n'
                      '\t(epsabs.le.0 and\n'
                      '\t epsrel.lt.max(50*rel.mach.acc.,0.5d-28))\n'
                      '\t or limit.lt.1 or leniw.lt.limit*4.\n'
                      '\tresult, abserr, neval, last are set to\n'
                      '\tzero. exept when limit or leniw is\n'
                      '\tinvalid, iwork(1), work(limit*2+1) and\n'
                      '\twork(limit*3+1) are set to zero, work(1)\n'
                      '\tset to a and work(limit+1) to b.'}


def messages(result,frequency,separation,height,*,rounding=0):
    status=result.status
    if not status:return()
    if result.method not in('DQAGIE','DQAWFE'):raise ValueError('Unknown Green integration method')
    def number(value):return format_binary64(struct.unpack('<Q',struct.pack('<d',value))[0],rounding=rounding)
    output=[MESSAGES['infinite_error'if result.method=='DQAGIE'else'fourier_error'].encode(),
            b'\nCalled with:  freq = '+number(frequency)+b', sep = '+number(separation)+b', h = '+number(height)]
    if result.method=='DQAGIE':
        if 1<=status<=6:output.append(MESSAGES['infinite_status_'+str(status)].encode())
    elif status in(4,6):output.append(MESSAGES['bad_table'if status==4 else'invalid'].encode())
    elif status in(1,7):
        output.append(MESSAGES['max_cycles'if status==1 else'bad_integrand'].encode())
        for i,cycle in enumerate(result.cycle_statuses):
            if 1<=cycle<=5:output.append((MESSAGES['cycle_'+('short_'if status==1 else'long_')+str(cycle)]%i).encode())
    else:output.append((MESSAGES['unknown']%status).encode())
    return tuple(output)
