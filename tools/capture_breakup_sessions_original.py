"""All selected original Pi2/coupled outcomes after SPTOWIRE conversion."""
import argparse,copy,gzip,json,os
from pathlib import Path
from capture_join_sessions_original import jobs as joined_jobs,capture_plain,main
from capture_join_original import command as previous_command,update_names as previous_names
from capture_trailing_via_heap_original import native_environment

ROOT=Path(__file__).resolve().parents[1]


class Names(list):
    def __init__(self,values,count):super().__init__(values);self.count=count


def command(op,names):
    if op['command']=='SPTOWIRE':return 'SPTOWIRE '+names[op.get('winding',0)]+'\n'
    return previous_command(op,names)


def update_names(names,op):
    if op['command']=='SPTOWIRE':
        old=names.pop(op.get('winding',0));names.extend(old+'_'+str(i)for i in range(names.count))
    else:previous_names(names,op)


def jobs():
    parent=ROOT/'tests/fixtures/join_sessions_original.json.gz';fixture=json.loads(gzip.decompress(parent.read_bytes()));bases={c['label']:c for c in fixture['cases']};sources={job[0]:job for job in joined_jobs()}
    selections=[('wire/first/pi2','wire','first','pi2',False),('wire/last/pi2','wire','last','pi2',False),('square/first/pi2','square','first','pi2',False),('square/via/pi2','square','via','pi2',False),('balun/first/pi2','balun','first','pi2',False),('wire/pair/calctrans','wire','first','calctrans',False),('square/pair/calctrans','square','first','calctrans',False),('square/first/eddy','square','first','pi2',True)]
    for label,kind,part,action,eddy in selections:
        key='finite-'+kind+'/pi2';base=bases[key];_,_,request,prefix,stdin,names=copy.deepcopy(sources[key]);live=names.copy()
        for op in request['edits']:previous_names(live,op)
        shape=next(s for s in base['geometry_states'][0]['shapes']if s['name']==live[0]);count=len(shape['segments']);start=len(live)-1
        offset=count-1 if part=='last'else next(i for i,s in enumerate(shape['segments'])if'thickness_bits'not in s)if part=='via'else 0
        request['edits'].append(dict(command='SPTOWIRE',winding=0));request.update(action=action,winding=start+offset,eddy=eddy)
        if action=='calctrans':request.update(first_winding=start,second_winding=start+1,termination_ohm=0)
        if eddy:prefix=prefix.replace('EDDY OFF','EDDY ON',1)
        yield label,parent,request,prefix,stdin,Names(names,count)


if __name__=='__main__':
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--library-path',required=True);args,_=parser.parse_known_args();os.environ.clear();os.environ.update(native_environment(args.library_path))
    accepted=capture_plain(output_name='breakup_plain_outcomes_original',job_source=jobs,command_source=command,names_source=update_names,description='All eight selected unchanged SPTOWIRE -> Pi2/CALCTRANS/2PORT histories run without GDB or replacements. First/last converted wire, square/balun leaves, both selected two-leaf coupled models, a converted via and eddy correction are retained, including every fault or missing/nonfinite report. produced_model records report production, not finiteness.')
    main(output_name='breakup_sessions_original',job_source=lambda:iter(accepted),command_source=command,names_source=update_names,capture_cap_reference=False,description='Every produced report in the separately retained eight-request SPTOWIRE plain cohort. Complete raw Pi2/CALCTRANS Y/model/S/resonance/node observers and completed geometry snapshots follow the unchanged original scripts. The coupled sprintf tap observes output only; it does not replace numerical operations. No native input, allocation, numerical instruction, register or result is substituted. Minimal environment supplied explicitly.')
