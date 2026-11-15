import hashlib
import json
from dataclasses import replace
from html.parser import HTMLParser
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from radio.arrangement import arrangement_for
from radio.compose import compose,midi
from radio.config import Config
from radio.melodic_connections import connect_melody
from radio.render import render,render_notes
from radio.melody_audition import audition_melody,report_html


class MelodyAuditionTests(unittest.TestCase):
    def font(self,root):
        p=root/'test.sf2';p.write_bytes(b'not used by mocked engines');return p

    def test_invalid_inputs_and_existing_outputs_have_no_side_effects(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);font=self.font(root)
            with patch('radio.melody_audition.engine_versions',side_effect=AssertionError('must validate first')):
                cases=[{'positions':(1,1)},{'positions':(0,)},{'positions':tuple(range(1,26))},{'seconds':19},{'seconds':1801},{'seconds':120,'positions':tuple(range(1,25))},{'bpm':39},{'station_seed':True}]
                for arguments in cases:
                    with self.subTest(arguments=arguments),self.assertRaises(ValueError):audition_melody(root/'new',font,**arguments)
                    self.assertFalse((root/'new').exists())
                existing=root/'existing';existing.mkdir()
                with self.assertRaises(FileExistsError):audition_melody(existing,font)
                link=root/'broken';link.symlink_to(root/'absent')
                with self.assertRaises(FileExistsError):audition_melody(link,font)

    def test_station_data_guard_does_not_create_database_or_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);font=self.font(root);station=root/'station';station.mkdir();(station/'radio.sqlite').write_bytes(b'unchanged')
            child=station/'nested';child.mkdir()
            with patch('sqlite3.connect',side_effect=AssertionError('offline tool must not connect')):
                with self.assertRaises(ValueError):audition_melody(child/'new',font)
            self.assertEqual((station/'radio.sqlite').read_bytes(),b'unchanged');self.assertFalse((child/'new').exists())

    def test_engine_failure_records_failed_not_complete(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);font=self.font(root)
            with patch('radio.melody_audition.engine_versions',side_effect=RuntimeError('deliberate')),patch('sqlite3.connect',side_effect=AssertionError('no database')):
                with self.assertRaises(RuntimeError):audition_melody(root/'out',font)
            report=json.loads((root/'out/report.json').read_text())
            self.assertEqual(report['status'],'failed');self.assertIn('deliberate',report['error']);self.assertFalse((root/'out/index.html').exists())
            self.assertFalse(list((root/'out').rglob('radio.sqlite')))

    def test_changed_font_is_rejected_before_stitching(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);font=self.font(root);calls=0
            def digest(path):
                nonlocal calls
                if Path(path)==font:
                    calls+=1;return 'a'*64 if calls==1 else 'b'*64
                return hashlib.sha256(Path(path).read_bytes()).hexdigest()
            def fake_render(config,seed,seconds,stem,*,arrangement=None):
                (config.data/'midi').mkdir(exist_ok=True);(config.data/'audio').mkdir(exist_ok=True)
                score=midi(compose(seed,seconds,config.bpm,arrangement),seconds,config.bpm,programs=arrangement.programs)
                (config.data/'midi'/f'{stem}.mid').write_bytes(score);audio=config.data/'audio'/f'{stem}.wav';audio.write_bytes(b'unmeasured');return audio,{}
            with patch('radio.melody_audition.engine_versions',return_value={}),patch('radio.melody_audition.digest',side_effect=digest),patch('radio.melody_audition.render',side_effect=fake_render),patch('radio.melody_audition.stitch') as stitch:
                with self.assertRaisesRegex(ValueError,'[Ff]ont'):audition_melody(root/'out',font,positions=(1,),seconds=20)
                stitch.assert_not_called()
            self.assertEqual(json.loads((root/'out/report.json').read_text())['status'],'failed')

    def test_html_names_same_font_different_score_and_escapes_font_name(self):
        report={'font':{'path':'/private/<img src=x>.sf2'},'sequence_seconds':235,'target_lufs':-22,'added_notes':0,'variants':{name:{'final_loudness':{'integrated_lufs':-22},'gain_db':0} for name in ['baseline','connections']},'changes':[]}
        page=report_html(report)
        self.assertNotIn('<img src=x>',page);self.assertIn('&lt;img src=x&gt;',page)
        self.assertIn('same SoundFont',page);self.assertIn('identical scores',page.lower());self.assertIn('0',page)
        class Parser(HTMLParser):
            def __init__(self):super().__init__();self.audio=[]
            def handle_starttag(self,tag,attrs):
                if tag=='audio':self.audio.append(dict(attrs))
        parser=Parser();parser.feed(page);self.assertEqual(len(parser.audio),2)
        self.assertEqual({a['src'] for a in parser.audio},{'baseline/listen.mp3','connections/listen.mp3'})
        for a in parser.audio:self.assertIn('controls',a);self.assertEqual(a['preload'],'none');self.assertNotIn('autoplay',a)


TOOLS=all(shutil.which(name) for name in ['fluidsynth','ffmpeg'])

@unittest.skipUnless(TOOLS,'requires installed FluidSynth/FFmpeg')
class MelodyMediaTests(unittest.TestCase):
    def test_default_renderer_retains_historical_midi_and_notes_entry_point(self):
        cases=json.loads((Path(__file__).parent/'fixtures/melody-baseline-midi.json').read_text())['cases']
        cases=[c for c in cases if c['station_seed']==42 and c['position']==2 and c['seconds']==20]
        self.assertEqual(len(cases),3)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with patch('sqlite3.connect',side_effect=AssertionError('no database')):
                for index,c in enumerate(cases):
                    a=arrangement_for(c['station_seed'],c['position']) if c['version'] else None
                    if c['version']==1:a=replace(a,version=1,phrase_bars=0)
                    data=root/str(index);data.mkdir();config=Config.from_env({'RADIO_DATA':str(data),'BPM':str(c['bpm'])})
                    path,metrics=render(config,c['station_seed']+c['position'],c['seconds'],1,arrangement=a)
                    self.assertEqual(hashlib.sha256((data/'midi/1.mid').read_bytes()).hexdigest(),c['sha256'])
                    self.assertAlmostEqual(metrics['duration'],20,delta=.1);self.assertFalse(list((data/'work').iterdir()))
                    if c['version']==2:
                        notes=connect_melody(compose(44,20,c['bpm'],a),20,c['bpm'],a)
                        path,metrics=render_notes(config,notes,20,2,arrangement=a)
                        expected=midi(notes,20,c['bpm'],programs=a.programs)
                        self.assertEqual((data/'midi/2.mid').read_bytes(),expected);self.assertAlmostEqual(metrics['duration'],20,delta=.1)

    def test_real_pair_uses_same_font_and_measured_matched_audio_without_database(self):
        font=Path('/usr/share/sounds/sf2/TimGM6mb.sf2')
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'pair'
            with patch('sqlite3.connect',side_effect=AssertionError('no database')):
                report=audition_melody(output,font,station_seed=20261114,positions=(2,3),seconds=20,bpm=60)
            self.assertEqual(report['status'],'complete');self.assertEqual(report['sequence_seconds'],35)
            for label,variant in report['variants'].items():
                self.assertEqual(variant['font_sha256'],report['font']['sha256'])
                self.assertLessEqual(variant['gain_db'],0);self.assertAlmostEqual(variant['final_loudness']['integrated_lufs'],report['target_lufs'],delta=.2)
                self.assertLessEqual(variant['final_loudness']['true_peak_dbfs'],-2.9)
                self.assertAlmostEqual(variant['final_analysis']['duration'],35,delta=.1)
                self.assertTrue((output/label/'listen.mp3').is_file());self.assertTrue((output/label/'listen.wav').is_file())
                for segment in variant['segments']:
                    a=arrangement_for(20261114,segment['position']);base=compose(20261114+segment['position'],20,60,a)
                    notes=base if label=='baseline' else connect_melody(base,20,60,a)
                    content=midi(notes,20,60,programs=a.programs)
                    self.assertEqual(segment['midi_sha256'],hashlib.sha256(content).hexdigest())
                    self.assertEqual(segment['added_notes'],len(notes)-len(base))
            self.assertFalse(list(output.rglob('radio.sqlite')));self.assertTrue((output/'index.html').is_file())


if __name__=='__main__':unittest.main()
