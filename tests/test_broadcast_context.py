import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from radio.config import Config
from radio.store import Store


class BroadcastLabelsTests(unittest.TestCase):
    def labels(self):
        self.assertIsNotNone(importlib.util.find_spec('radio.labels'), 'safe broadcast label helpers are missing')
        from radio import labels
        return labels

    def analysis(self, **values):
        arrangement = {'version':2,'chapter':78,'stage':'unfold','programs':[89,32,4]}
        arrangement.update(values)
        return json.dumps({'arrangement':arrangement})

    def test_each_stage_and_palette_has_controlled_readable_copy(self):
        labels=self.labels()
        stages={'arrival':'beginning','unfold':'unfolding','bloom':'in bloom','settle':'settling','release':'closing'}
        for stage,phrase in stages.items():
            for programs,palette in [([89,32,4],'Warm keys'),([94,32,4],'Halo keys'),([89,32,11],'Soft bells')]:
                for version in (1,2):
                    with self.subTest(stage=stage,programs=programs,version=version):
                        self.assertEqual(labels.title_for_analysis(self.analysis(stage=stage,programs=programs,version=version)),f'Chapter 78 is {phrase}. {palette}.')
        self.assertEqual(labels.title_for_analysis(self.analysis(programs=[1,2,3])),'Chapter 78 is unfolding.')

    def test_invalid_or_unbounded_analysis_never_becomes_public_text(self):
        labels=self.labels()
        values=[None,'','not JSON','[]','null','{}',json.dumps({'arrangement':'secret'}),' '*8193,'['*2000+']'*2000,
                self.analysis(stage=[]),self.analysis(chapter=True),self.analysis(chapter=0),self.analysis(chapter=-1),
                self.analysis(chapter='78'),self.analysis(chapter=2**63),self.analysis(version=True),
                self.analysis(version=3),self.analysis(stage='<script>private-token</script>')]
        for value in values:
            with self.subTest(value=str(value)[:60]):
                self.assertEqual(labels.title_for_analysis(value),'Original ambient music.')
        self.assertEqual(labels.title_for_analysis(self.analysis(chapter=2**63-1)),f'Chapter {2**63-1} is unfolding. Warm keys.')
        # Unused fields, raw paths and source tokens are not copied into the label.
        a=json.loads(self.analysis());a['private_token']='DO_NOT_PUBLISH';a['arrangement']['programs']=['private',32,4]
        self.assertEqual(labels.title_for_analysis(json.dumps(a)),'Chapter 78 is unfolding.')

    def test_annotation_preserves_absolute_path_and_quotes_metadata(self):
        labels=self.labels();path='/tmp/room, blue:one/1.wav'
        uri=labels.annotated_request(path,self.analysis())
        self.assertEqual(uri,'annotate:title="Chapter 78 is unfolding. Warm keys.",artist="Generative Radio":'+path)
        self.assertEqual(labels.annotated_request('/data/audio/1.wav',None),'annotate:title="Original ambient music.",artist="Generative Radio":/data/audio/1.wav')
        for invalid in ['relative.wav','/tmp/a\n.wav','/tmp/a\r.wav','/tmp/a\x00.wav','/tmp/a\x7f.wav','/tmp/a\x85.wav','/tmp/a\u2028.wav']:
            with self.subTest(path=invalid),self.assertRaises(ValueError):labels.annotated_request(invalid,self.analysis())


class ContextDispatchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.data=Path(self.temp.name)/'station';self.data.mkdir();(self.data/'audio').mkdir()
        self.c=Config(self.data,20,20,60,42,'unused');self.store=Store(self.data);self.addCleanup(self.store.db.close)
        self.metadata=[]
        for chapter in (17,29):
            self.store.enqueue(self.c);job=self.store.claim();p=self.data/'audio'/f'{job["id"]}.wav';p.write_bytes(b'fixture audio')
            analysis={'arrangement':{'version':2,'chapter':chapter,'stage':'unfold','programs':[89,32,4]}}
            self.metadata.append(analysis);self.store.finish(job,p,analysis)

    def test_info_dispatch_keeps_saved_metadata_and_legacy_path_behavior(self):
        self.assertTrue(hasattr(self.store,'next_track_info'),'atomic dispatch information is missing')
        info=self.store.next_track_info();self.assertEqual(info['path'],str(self.data/'audio/1.wav'));self.assertEqual(json.loads(info['analysis']),self.metadata[0])
        self.assertEqual(self.store.next_track(),str(self.data/'audio/2.wav'))
        self.assertIsNone(self.store.next_track_info());self.assertEqual(self.store.next_track(),'')
        self.assertEqual([r[0] for r in self.store.db.execute('SELECT status FROM jobs ORDER BY id')],['served','served'])

    def test_missing_audio_is_skipped_before_selecting_its_label(self):
        self.assertTrue(hasattr(self.store,'next_track_info'))
        (self.data/'audio/1.wav').unlink();info=self.store.next_track_info()
        self.assertEqual(info['path'],str(self.data/'audio/2.wav'));self.assertEqual(json.loads(info['analysis']),self.metadata[1])
        self.assertEqual([r[0] for r in self.store.db.execute('SELECT status FROM jobs ORDER BY id')],['failed','served'])

    def test_cli_annotation_is_opt_in_and_plain_next_is_unchanged(self):
        env={**os.environ,'RADIO_DATA':str(self.data)};command=[sys.executable,'-m','radio','next']
        annotated=subprocess.run(command+['--annotate'],env=env,capture_output=True,text=True,timeout=5)
        self.assertEqual(annotated.returncode,0,annotated.stderr)
        self.assertEqual(annotated.stdout.strip(),'annotate:title="Chapter 17 is unfolding. Warm keys.",artist="Generative Radio":'+str(self.data/'audio/1.wav'))
        plain=subprocess.run(command,env=env,capture_output=True,text=True,timeout=5)
        self.assertEqual(plain.returncode,0,plain.stderr);self.assertEqual(plain.stdout.strip(),str(self.data/'audio/2.wav'))

    def test_annotation_flag_is_rejected_before_data_creation_for_other_commands(self):
        absent=self.data/'must-not-be-created';env={**os.environ,'RADIO_DATA':str(absent)}
        for command in ['composer','renderer','preview','status','health']:
            with self.subTest(command=command):
                r=subprocess.run([sys.executable,'-m','radio',command,'--annotate'],env=env,capture_output=True,text=True,timeout=3)
                self.assertEqual(r.returncode,2);self.assertIn('only',r.stderr.lower());self.assertFalse(absent.exists())
