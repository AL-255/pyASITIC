"""Every selected original Pi2/coupled outcome after UNJOIN, including empty tails."""
import copy
from capture_join_sessions_original import jobs as joined_jobs,capture_plain,main
from capture_unjoin_original import command,update_names


def jobs():
    selected={job[0]:job for job in joined_jobs()}
    for kind,index in(('wire',1),('square',2),('balun',4)):
        for part in('head','tail'):
            _,parent,r,prefix,stdin,names=copy.deepcopy(selected['finite-'+kind+'/pi2']);live=names.copy()
            for op in r['edits']:update_names(live,op)
            r['edits'].append(dict(command='UNJOIN',winding=0,index=index,name='split'));r['winding']=0 if part=='head'else len(live)
            yield kind+'/'+part+'/pi2',parent,r,prefix,stdin,names
    for pair in('head-tail','tail-other'):
        _,parent,r,prefix,stdin,names=copy.deepcopy(selected['finite-balun/calctrans']);live=names.copy()
        for op in r['edits']:update_names(live,op)
        r['edits'].append(dict(command='UNJOIN',winding=0,index=4,name='split'))
        first,second=(0,len(live))if pair=='head-tail'else(len(live),1)
        r.update(winding=first,first_winding=first,second_winding=second)
        yield 'balun/'+pair+'/calctrans',parent,r,prefix,stdin,names
    _,parent,r,prefix,stdin,names=copy.deepcopy(selected['finite-wire/pi2']);live=names.copy()
    for op in r['edits']:update_names(live,op)
    r['edits'].append(dict(command='UNJOIN',winding=0,index=2,name='empty'));r['winding']=len(live)
    yield 'wire/empty/pi2',parent,r,prefix,stdin,names


if __name__=='__main__':
    accepted=capture_plain(output_name='unjoin_plain_outcomes_original',job_source=jobs,command_source=command,names_source=update_names,description='Every selected unchanged UNJOIN/Pi2/CALCTRANS/2PORT script, without observers or replacements. Both halves of joined wires, squares and baluns, both selected split coupled pairings and the empty-tail analysis are retained, including faults and nonfinite reports. produced_model means a report exists, not that it is finite.')
    main(output_name='unjoin_sessions_original',job_source=lambda:iter(accepted),command_source=command,names_source=update_names,capture_cap_reference=False,description='Unchanged original UNJOIN/Pi2/CALCTRANS/2PORT scripts with read-only geometry, raw model/Y/S/resonance/node observers. Every selected unobserved outcome, including missing and nonfinite reports, is separately preserved in unjoin_plain_outcomes_original.json.gz.')
