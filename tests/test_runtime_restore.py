"""Restore source through connector transport without git or network."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class RestoreTests(unittest.TestCase):
    def module(self):
        path = ROOT / 'scripts/restore_agent_runtime.py'
        self.assertTrue(path.is_file(), 'Offline source restore is missing')
        spec = importlib.util.spec_from_file_location('source_restore', path)
        m = importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        return m

    def test_connector_sources_restore_with_exact_hashes(self):
        m=self.module()
        manifest=json.loads((ROOT/'runtime/source_manifest.json').read_text())
        sources={name:(ROOT/name).read_text() for name in manifest['files']}
        raw=json.dumps(manifest).encode()
        with tempfile.TemporaryDirectory() as directory:
            dest=Path(directory)/'restored'
            result=m.restore(raw, {'commit':'a'*40,'files':sources}, dest,
                             'a'*40, hashlib.sha256(raw).hexdigest())
            self.assertEqual(result['status'],'SOURCE_RUNTIME_RESTORED')
            self.assertEqual((dest/'tools/agent_gateway.py').read_bytes(),(ROOT/'tools/agent_gateway.py').read_bytes())
            self.assertFalse((dest/'.git').exists())
            self.assertFalse(result['validated'])

    def test_tampered_source_or_wrong_commit_never_installed(self):
        m=self.module();manifest=json.loads((ROOT/'runtime/source_manifest.json').read_text());raw=json.dumps(manifest).encode()
        sources={name:(ROOT/name).read_text() for name in manifest['files']}
        sources['tools/agent_gateway.py']+='\n# tampered\n'
        with tempfile.TemporaryDirectory() as directory:
            dest=Path(directory)/'restored'
            with self.assertRaisesRegex(ValueError,'HASH_MISMATCH'):
                m.restore(raw,{'commit':'a'*40,'files':sources},dest,'a'*40,hashlib.sha256(raw).hexdigest())
            self.assertFalse(dest.exists())
            with self.assertRaisesRegex(ValueError,'COMMIT_MISMATCH'):
                m.restore(raw,{'commit':'b'*40,'files':sources},dest,'a'*40,hashlib.sha256(raw).hexdigest())

    def test_extra_private_file_is_rejected(self):
        m=self.module();manifest=json.loads((ROOT/'runtime/source_manifest.json').read_text());raw=json.dumps(manifest).encode()
        sources={name:(ROOT/name).read_text() for name in manifest['files']};sources['collection.csv']='private'
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,'FILE_SET'):
                m.restore(raw,{'commit':'a'*40,'files':sources},Path(directory)/'out','a'*40,hashlib.sha256(raw).hexdigest())

    def test_restored_runtime_executes_real_validator_without_git(self):
        import subprocess,sys,os
        m=self.module();raw=(ROOT/'runtime/source_manifest.json').read_bytes();manifest=json.loads(raw)
        sources={name:(ROOT/name).read_text() for name in manifest['files']}
        with tempfile.TemporaryDirectory() as directory:
            private=Path(directory);dest=private/'runtime'
            m.restore(raw,{'commit':'a'*40,'files':sources},dest,'a'*40,hashlib.sha256(raw).hexdigest())
            oracle=private/'fixture.json';oracle.write_text(json.dumps({'data':{'Mountain':[{'name':'Mountain','types':['Land'],'supertypes':['Basic'],'manaValue':0,'colorIdentity':['R']}],'Shock':[{'name':'Shock','types':['Instant'],'manaValue':1,'manaCost':'{R}','colorIdentity':['R'],'text':'Shock deals 2 damage to any target.'}]}}))
            collection=private/'synthetic.csv';collection.write_text('Name,Quantity\nShock,5\n')
            deck=private/'deck.txt'
            env=dict(os.environ,PATH='/git-is-unavailable')
            for content,expected in [('56 Mountain\n4 Shock\n',0),('55 Mountain\n5 Shock\n',2)]:
                deck.write_text(content)
                result=subprocess.run([sys.executable,'-m','ai_deckbuilding_tool','validate','--synthetic','--oracle',str(oracle),'--oracle-sha256',hashlib.sha256(oracle.read_bytes()).hexdigest(),'--collection',str(collection),'--deck',str(deck)],cwd=dest,env=env,capture_output=True,text=True,timeout=30)
                report=json.loads(result.stdout)
                self.assertEqual(result.returncode,expected,report)
                self.assertEqual(report['gateway']['tool_execution'],'EXECUTED')
                self.assertEqual(report['gateway']['child_exit_code'],0 if expected==0 else 1)

    def test_symlink_existing_destination_and_path_traversal_are_rejected(self):
        m=self.module();raw=(ROOT/'runtime/source_manifest.json').read_bytes();manifest=json.loads(raw)
        sources={name:(ROOT/name).read_text() for name in manifest['files']};sha=hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);dest=root/'exists';dest.mkdir();(dest/'keep').write_text('unchanged')
            with self.assertRaisesRegex(ValueError,'ALREADY_EXISTS'):
                m.restore(raw,{'commit':'a'*40,'files':sources},dest,'a'*40,sha)
            self.assertEqual((dest/'keep').read_text(),'unchanged')
            link=root/'link';link.symlink_to(dest,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'SYMLINK'):
                m.restore(raw,{'commit':'a'*40,'files':sources},link/'new','a'*40,sha)
            bad=dict(sources);bad['../escape.py']='bad'
            with self.assertRaisesRegex(ValueError,'FILE_SET'):
                m.restore(raw,{'commit':'a'*40,'files':bad},root/'new','a'*40,sha)
