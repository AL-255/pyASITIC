"""Promote validated main ancestors without rolling back a newer Pages build."""
import argparse,json,os,re,subprocess
from pathlib import Path


def gh_api(endpoint):
    return json.loads(subprocess.check_output(['gh','api',endpoint],text=True))


def pages(api,endpoint):
    for page in range(1,10001):
        rows=api(endpoint+('&'if'?'in endpoint else'?')+f'per_page=100&page={page}')
        if not isinstance(rows,list):raise ValueError('Expected a GitHub API page')
        yield from rows
        if len(rows)<100:return
    raise ValueError('Deployment pagination exceeded its bound')


def sha(value):
    if not isinstance(value,str)or not re.fullmatch('[0-9a-f]{40}',value):raise ValueError('Expected a full commit SHA')
    return value


def published_commit(repository,api):
    for deployment in pages(api,f'repos/{repository}/deployments?environment=github-pages'):
        identifier=deployment['id']
        if not isinstance(identifier,int)or identifier<=0:raise ValueError('Invalid deployment identifier')
        for status in pages(api,f'repos/{repository}/deployments/{identifier}/statuses'):
            # Skipped Deploy steps have no site URL, even if the environment
            # job is marked successful. A site URL comes from Deploy's output.
            # Conservatively retain it after a later job/cleanup failure too,
            # because publication may already have happened. This prevents an
            # older completed build from overwriting that deployment.
            if status.get('environment_url'):
                return sha(deployment['sha'])
    return None


def decision(repository,candidate,api=gh_api):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository):raise ValueError('Expected owner/repository')
    candidate=sha(candidate);main=sha(api(f'repos/{repository}/git/ref/heads/main')['object']['sha'])
    result=dict(candidate=candidate,main=main,published=None,publish=False)
    if candidate!=main and api(f'repos/{repository}/compare/{candidate}...{main}')['status']!='ahead':
        return dict(result,reason='Candidate is outside the current main history')
    published=published_commit(repository,api);result['published']=published
    if published is None:return dict(result,publish=True,reason='First published Pages build')
    if candidate==published:return dict(result,publish=True,reason='Rebuild of the published commit')
    if api(f'repos/{repository}/compare/{published}...{candidate}')['status']=='ahead':
        return dict(result,publish=True,reason='Validated build advances published Pages')
    return dict(result,reason='A newer or unrelated commit is already published')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository',default=os.environ.get('GITHUB_REPOSITORY'))
    parser.add_argument('--candidate',default=os.environ.get('GITHUB_SHA'));parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    if not args.repository or not args.candidate:parser.error('Provide --repository and --candidate, or the corresponding GitHub Actions environment')
    result=decision(args.repository,args.candidate);print(json.dumps(result,sort_keys=True))
    if not args.dry_run:
        with Path(os.environ['GITHUB_OUTPUT']).open('a')as output:output.write('publish='+str(result['publish']).lower()+'\n')


if __name__=='__main__':main()
