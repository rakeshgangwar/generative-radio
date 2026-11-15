import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from radio.audition import audition, validate_inputs, shared_level, report_html, check_levels


class AuditionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.font=self.root/'fixture.sf2';self.font.write_bytes(b'font fixture')
        self.fonts={'reference':self.font,'candidate':self.font}

    def test_invalid_inputs_are_rejected_before_any_output_is_created(self):
        cases=[{'fonts':{'one':self.font}}, {'fonts':{'../escape':self.font,'safe':self.font}},
               {'positions':[0]}, {'positions':[1,1]}, {'positions':list(range(1,26))},
               {'seconds':19}, {'seconds':1801}, {'seconds':120,'positions':list(range(1,17))},
               {'bpm':39}, {'bpm':91}, {'station_seed':True}]
        for overrides in cases:
            args={'fonts':self.fonts,'positions':[1],'seconds':20,'bpm':60,'station_seed':42}|overrides
            with self.subTest(overrides=overrides),self.assertRaises(ValueError):
                audition(self.root/'output',**args)
            self.assertFalse((self.root/'output').exists())

    def test_font_paths_are_readable_regular_local_soundfonts(self):
        for path in [self.root/'missing.sf2',self.root,self.root/'wrong.txt']:
            path.parent.mkdir(exist_ok=True)
            if path.suffix=='.txt':path.write_bytes(b'fixture')
            with self.subTest(path=path),self.assertRaises((ValueError,OSError)):
                validate_inputs({'a':self.font,'b':path},[1],20,60,42)

    def test_existing_output_or_symlinks_are_never_overwritten(self):
        output=self.root/'output';output.mkdir();sentinel=output/'keep';sentinel.write_text('untouched')
        with self.assertRaises(FileExistsError):audition(output,self.fonts,positions=[1],seconds=20)
        self.assertEqual(sentinel.read_text(),'untouched')
        link=self.root/'link';link.symlink_to(self.root/'absent')
        with self.assertRaises(FileExistsError):audition(link,self.fonts,positions=[1],seconds=20)
        self.assertTrue(link.is_symlink());self.assertFalse((self.root/'absent').exists())

    def test_output_cannot_be_nested_inside_station_data_even_through_an_alias(self):
        station=self.root/'station';station.mkdir();(station/'radio.sqlite').write_bytes(b'live database sentinel')
        (station/'nested').mkdir();alias=self.root/'alias';alias.symlink_to(station/'nested',target_is_directory=True)
        for output in [station/'comparison',alias/'comparison']:
            with self.subTest(output=output),patch('radio.audition.engine_versions',return_value={}),patch('radio.audition.render',side_effect=RuntimeError('must not render')):
                with self.assertRaisesRegex(ValueError,'station data'):
                    audition(output,self.fonts,positions=[1],seconds=20)
                self.assertFalse(output.exists())
        self.assertEqual((station/'radio.sqlite').read_bytes(),b'live database sentinel')

    def test_shared_level_only_attenuates_and_preserves_true_peak_headroom(self):
        for values,expected in [([(-20,-2),(-24,-6)],-24),([(-24,-1),(-23,-5)],-26),([(-18,-8),(-19,-7)],-22)]:
            inputs=[{'integrated_lufs':i,'true_peak_dbfs':p} for i,p in values]
            target=shared_level(inputs);self.assertEqual(target,expected)
            for i,p in values:
                self.assertLessEqual(target-i,0);self.assertLessEqual(p+target-i,-3)

    def test_final_variants_must_match_each_other_not_only_the_target(self):
        with self.assertRaises(ValueError):
            check_levels([{'integrated_lufs':-24.19,'true_peak_dbfs':-5},
                          {'integrated_lufs':-23.81,'true_peak_dbfs':-5}],-24)
        check_levels([{'integrated_lufs':-24.1,'true_peak_dbfs':-3},
                      {'integrated_lufs':-24.15,'true_peak_dbfs':-4}],-24)

    def test_nonfinite_or_missing_loudness_is_not_accepted(self):
        for value in [math.nan,math.inf,-math.inf,'bad',None]:
            for key in ['integrated_lufs','true_peak_dbfs']:
                measured={'integrated_lufs':-24,'true_peak_dbfs':-6};measured[key]=value
                with self.subTest(value=value,key=key),self.assertRaises(ValueError):shared_level([measured])
        with self.assertRaises(ValueError):shared_level([])
        with self.assertRaises(ValueError):shared_level([{}])

    def test_caught_render_failure_leaves_failed_receipt_and_partial_artifacts(self):
        output=self.root/'output'
        with patch('radio.audition.engine_versions',return_value={}),patch('radio.audition.render',side_effect=RuntimeError('fixture render failure')):
            with self.assertRaisesRegex(RuntimeError,'fixture render failure'):
                audition(output,self.fonts,positions=[1],seconds=20)
        report=json.loads((output/'report.json').read_text());self.assertEqual(report['status'],'failed')
        self.assertNotIn('complete',report['status']);self.assertTrue(output.exists())

    def test_wrong_rendered_score_is_rejected_instead_of_compared(self):
        def wrong(config,seed,seconds,stem,**kwargs):
            (config.data/'midi').mkdir();(config.data/'midi'/f'{stem}.mid').write_bytes(b'wrong score')
            return config.data/'unused.wav', {'duration':seconds}
        output=self.root/'output'
        with patch('radio.audition.engine_versions',return_value={}),patch('radio.audition.render',side_effect=wrong):
            with self.assertRaisesRegex(ValueError,'score differs'):audition(output,self.fonts,positions=[1],seconds=20)
        self.assertEqual(json.loads((output/'report.json').read_text())['status'],'failed')
        self.assertFalse((output/'index.html').exists())

    def test_changing_font_during_render_cannot_publish_a_complete_report(self):
        from radio.compose import compose,midi
        def changed(config,seed,seconds,stem,*,arrangement):
            (config.data/'midi').mkdir()
            (config.data/'midi'/f'{stem}.mid').write_bytes(midi(compose(seed,seconds,config.bpm,arrangement),seconds,config.bpm,programs=arrangement.programs))
            self.font.write_bytes(b'changed while rendering')
            return config.data/'unused.wav', {'duration':seconds}
        output=self.root/'output'
        with patch('radio.audition.engine_versions',return_value={}),patch('radio.audition.render',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'changed during'):audition(output,self.fonts,positions=[1],seconds=20)
        self.assertEqual(json.loads((output/'report.json').read_text())['status'],'failed')

    def test_report_escapes_text_and_has_no_external_assets_or_autoplay(self):
        report={'target_lufs':-24,'sequence_seconds':20,'variants':{'<img src=x onerror=bad>':{'gain_db':-1,'final_loudness':{'integrated_lufs':-24},'font':{'size_bytes':123}}}}
        html=report_html(report)
        self.assertIn('&lt;img',html);self.assertNotIn('<img',html)
        self.assertNotIn('autoplay',html);self.assertNotIn('https://',html);self.assertNotIn('http://',html)
        self.assertIn('preload="none"',html)


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('fluidsynth') and Path('/usr/share/sounds/sf2/TimGM6mb.sf2').exists(),'actual audio tools and installed font required')
class ActualAuditionTests(unittest.TestCase):
    def test_real_identity_control_is_matched_complete_and_playable(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'comparison';font=Path('/usr/share/sounds/sf2/TimGM6mb.sf2')
            report=audition(root,{'one':font,'two':font},positions=[1,2],seconds=20)
            self.assertEqual(report['status'],'complete');self.assertEqual(report['sequence_seconds'],35)
            levels=[]
            for variant in report['variants'].values():
                self.assertEqual(len(variant['segments']),2)
                self.assertAlmostEqual(variant['final_analysis']['duration'],35,places=2)
                self.assertLessEqual(variant['gain_db'],0)
                self.assertLessEqual(variant['final_loudness']['true_peak_dbfs'],-2.9)
                levels.append(variant['final_loudness']['integrated_lufs'])
            self.assertLessEqual(max(levels)-min(levels),.2)
            self.assertEqual([s['midi_sha256'] for s in report['variants']['one']['segments']],[s['midi_sha256'] for s in report['variants']['two']['segments']])
            self.assertTrue((root/'one/listen.mp3').stat().st_size>1000)
            decoded=subprocess.run(['ffmpeg','-nostdin','-v','error','-i',str(root/'one/listen.mp3'),'-f','null','-'],capture_output=True,timeout=30)
            self.assertEqual(decoded.returncode,0,decoded.stderr)
            self.assertTrue((root/'index.html').is_file())
            self.assertEqual(json.loads((root/'report.json').read_text())['status'],'complete')
