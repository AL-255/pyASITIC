"""Pages promotion follows actual publication and commit ancestry."""
import importlib.util
from pathlib import Path
import unittest

SPEC=importlib.util.spec_from_file_location('pages_promotion',Path(__file__).resolve().parents[1]/'tools/pages_promotion.py')
module=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(module)
REPO='owner/repo';OLD='a'*40;CANDIDATE='b'*40;TIP='c'*40
LIST=f'repos/{REPO}/deployments?environment=github-pages&per_page=100&page=1'


def api_for(main=TIP,published=OLD):
    data={f'repos/{REPO}/git/ref/heads/main':{'object':{'sha':main}},LIST:[{'id':1,'sha':published}]if published else[]}
    if published:data[f'repos/{REPO}/deployments/1/statuses?per_page=100&page=1']=[{'state':'success','environment_url':'https://owner.github.io/repo/'}]
    return data


class PagesPromotionTests(unittest.TestCase):
    def test_validated_ancestor_publishes_while_newer_main_is_pending(self):
        data=api_for();data[f'repos/{REPO}/compare/{CANDIDATE}...{TIP}']={'status':'ahead'};data[f'repos/{REPO}/compare/{OLD}...{CANDIDATE}']={'status':'ahead'}
        # Reproduce the real skipped Deploy job: environment success, no URL.
        data[LIST].insert(0,{'id':2,'sha':TIP});data[f'repos/{REPO}/deployments/2/statuses?per_page=100&page=1']=[{'state':'success','environment_url':''}]
        result=module.decision(REPO,CANDIDATE,data.__getitem__);self.assertTrue(result['publish']);self.assertEqual(result['published'],OLD)

    def test_older_or_unrelated_build_cannot_replace_published_version(self):
        for status in('behind','diverged'):
            data=api_for(published=TIP);data[f'repos/{REPO}/compare/{CANDIDATE}...{TIP}']={'status':'ahead'};data[f'repos/{REPO}/compare/{TIP}...{CANDIDATE}']={'status':status}
            self.assertFalse(module.decision(REPO,CANDIDATE,data.__getitem__)['publish'])
        data=api_for();data[f'repos/{REPO}/compare/{CANDIDATE}...{TIP}']={'status':'diverged'}
        self.assertFalse(module.decision(REPO,CANDIDATE,data.__getitem__)['publish'])

    def test_first_publication_and_same_commit_rebuild(self):
        data=api_for(main=CANDIDATE,published=None);self.assertTrue(module.decision(REPO,CANDIDATE,data.__getitem__)['publish'])
        data=api_for(main=CANDIDATE,published=CANDIDATE);self.assertTrue(module.decision(REPO,CANDIDATE,data.__getitem__)['publish'])

    def test_pagination_and_inactive_receipt_with_retained_site_url(self):
        data={LIST:[{'id':i,'sha':TIP}for i in range(2,102)],LIST.replace('&page=1','&page=2'):[{'id':1,'sha':OLD}]}
        for i in range(2,102):data[f'repos/{REPO}/deployments/{i}/statuses?per_page=100&page=1']=[{'state':'failure','environment_url':''}]
        data[f'repos/{REPO}/deployments/1/statuses?per_page=100&page=1']=[{'state':'pending'}]*100
        data[f'repos/{REPO}/deployments/1/statuses?per_page=100&page=2']=[{'state':'inactive','environment_url':'https://owner.github.io/repo/'}]
        self.assertEqual(module.published_commit(REPO,data.__getitem__),OLD)

    def test_failure_after_site_output_does_not_allow_rollback(self):
        data=api_for(published=TIP)
        data[f'repos/{REPO}/deployments/1/statuses?per_page=100&page=1']=[{'state':'failure','environment_url':'https://owner.github.io/repo/'}]
        data[f'repos/{REPO}/compare/{CANDIDATE}...{TIP}']={'status':'ahead'};data[f'repos/{REPO}/compare/{TIP}...{CANDIDATE}']={'status':'behind'}
        self.assertFalse(module.decision(REPO,CANDIDATE,data.__getitem__)['publish'])

    def test_api_failure_and_invalid_identifiers_do_not_allow_publication(self):
        def broken(endpoint):raise RuntimeError('GitHub API unavailable')
        with self.assertRaisesRegex(RuntimeError,'unavailable'):module.decision(REPO,CANDIDATE,broken)
        with self.assertRaisesRegex(ValueError,'full commit SHA'):module.decision(REPO,'main',broken)
        with self.assertRaisesRegex(ValueError,'owner/repository'):module.decision('owner/repo/extra',CANDIDATE,broken)
