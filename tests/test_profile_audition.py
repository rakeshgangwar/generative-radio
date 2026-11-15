import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch
import subprocess
import sys
import unittest


class ProfileCommandTests(unittest.TestCase):
    def test_cli_help_describes_offline_profile_comparison(self):
        result = subprocess.run([sys.executable, '-m', 'radio.profile_audition', '--help'],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--output', result.stdout)
        self.assertIn('--soundfont', result.stdout)
        self.assertIn('resting', result.stdout.lower())


class ProfileScoreTests(unittest.TestCase):
    def test_current_score_is_existing_v2_score_and_resting_has_declared_tempo(self):
        from radio.profile_audition import score_for
        from radio.arrangement import arrangement_for
        from radio.compose import compose, midi
        expected = arrangement_for(42, 2)
        a, notes, bpm = score_for('current', 42, 2, 120)
        self.assertEqual(bpm, 60)
        self.assertEqual(midi(notes, 120, bpm, programs=a.programs),
                         midi(compose(44, 120, 60, expected), 120, 60, programs=expected.programs))
        rest, quiet, tempo = score_for('resting', 42, 2, 120)
        self.assertEqual(tempo, 52)
        self.assertEqual(rest.profile, 0)
        self.assertEqual(rest.programs, (89, 32, 4))
        for field in ('chapter', 'chapter_segment', 'motif', 'progression', 'version', 'phrase_bars'):
            self.assertEqual(getattr(rest, field), getattr(a, field))
        beat = 60 / tempo
        for n in quiet:
            self.assertGreater(n.duration, 0)
            self.assertLessEqual(n.start + n.duration, 120)
            if n.channel == 2:
                bar = int(n.start / (4 * beat))
                self.assertNotEqual(bar % rest.phrase_bars, rest.phrase_bars - 1)
                rest_start = ((bar // rest.phrase_bars + 1) * rest.phrase_bars - 1) * 4 * beat
                self.assertLessEqual(n.start + n.duration, rest_start - .1 * beat + 1e-8)

    def test_resting_reduces_aggregate_lead_attacks_in_the_same_long_score_sample(self):
        from radio.profile_audition import score_for
        totals = {}
        for profile in ('current', 'resting'):
            totals[profile] = sum(sum(n.channel == 2 for n in score_for(profile, 42, p, 120)[1])
                                  for p in range(1, 257))
        self.assertLess(totals['resting'], totals['current'] * .8)

    def test_score_rejects_unknown_profiles_and_invalid_identity_or_duration(self):
        from radio.profile_audition import score_for
        for args in [('other',42,1,120),('resting',True,1,120),('resting',42,0,120),
                     ('resting',42,True,120),('resting',42,1,19),('resting',42,1,1801)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                score_for(*args)


class ProfileOutputTests(unittest.TestCase):
    def test_invalid_inputs_existing_outputs_and_station_markers_have_no_engine_side_effects(self):
        from radio.profile_audition import audition_profile
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);font=root/'font.sf2';font.write_bytes(b'validation only')
            with patch('radio.profile_audition.engine_versions', side_effect=AssertionError('engine must not run')):
                for args in ({'positions':(1,1)},{'positions':(0,)},{'positions':tuple(range(1,26))},
                             {'seconds':19},{'seconds':1801},{'positions':(1,2),'seconds':1000},
                             {'station_seed':True}):
                    with self.subTest(args=args), self.assertRaises(ValueError):
                        audition_profile(root/'new',font,**args)
                    self.assertFalse((root/'new').exists())
                existing=root/'existing';existing.mkdir();broken=root/'broken';broken.symlink_to(root/'absent')
                for path in (existing,broken):
                    with self.assertRaises(FileExistsError):audition_profile(path,font)
                station=root/'station';station.mkdir();marker=station/'radio.sqlite';marker.symlink_to(root/'missing-db')
                child=station/'nested';child.mkdir()
                with self.assertRaises(ValueError):audition_profile(child/'new',font)
                self.assertFalse((child/'new').exists())
                self.assertTrue(marker.is_symlink())

    def test_engine_failure_and_keyboard_interrupt_never_publish_a_complete_page(self):
        from radio.profile_audition import audition_profile
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);font=root/'font.sf2';font.write_bytes(b'validation only')
            for i,error in enumerate((RuntimeError('deliberate failure'), KeyboardInterrupt())):
                with patch('radio.profile_audition.engine_versions',side_effect=error),self.assertRaises(type(error)):
                    audition_profile(root/str(i),font,positions=(1,),seconds=20)
                report=json.loads((root/str(i)/'report.json').read_text())
                self.assertEqual(report['status'],'cancelled' if isinstance(error,KeyboardInterrupt) else 'failed')
                self.assertFalse((root/str(i)/'index.html').exists())

    def test_unexpected_rendered_midi_is_rejected_before_stitching(self):
        from radio.profile_audition import audition_profile
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);font=root/'font.sf2';font.write_bytes(b'validation only')
            def wrong(config,notes,seconds,stem,*,arrangement):
                (config.data/'midi').mkdir();(config.data/'midi'/f'{stem}.mid').write_bytes(b'wrong tempo or programs')
                return config.data/'unmeasured.wav',{}
            with patch('radio.profile_audition.engine_versions',return_value={}),patch('radio.profile_audition.render_notes',side_effect=wrong),patch('radio.profile_audition.stitch') as stitch:
                with self.assertRaisesRegex(ValueError,'MIDI'):audition_profile(root/'out',font,positions=(1,),seconds=20)
                stitch.assert_not_called()
            self.assertEqual(json.loads((root/'out/report.json').read_text())['status'],'failed')

    def test_font_change_is_rejected_before_stitching(self):
        from radio.profile_audition import audition_profile
        from radio.compose import midi
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);font=root/'font.sf2';font.write_bytes(b'validation only');calls=0
            def fingerprint(path):
                nonlocal calls
                if Path(path)==font:
                    calls+=1;return 'a'*64 if calls==1 else 'b'*64
                return hashlib.sha256(Path(path).read_bytes()).hexdigest()
            def rendered(config,notes,seconds,stem,*,arrangement):
                (config.data/'midi').mkdir();(config.data/'midi'/f'{stem}.mid').write_bytes(midi(notes,seconds,config.bpm,programs=arrangement.programs))
                return config.data/'unmeasured.wav',{}
            with patch('radio.profile_audition.engine_versions',return_value={}),patch('radio.profile_audition.digest',side_effect=fingerprint),patch('radio.profile_audition.render_notes',side_effect=rendered),patch('radio.profile_audition.stitch') as stitch:
                with self.assertRaisesRegex(ValueError,'[Ff]ont'):audition_profile(root/'out',font,positions=(1,),seconds=20)
                stitch.assert_not_called()

    def test_shared_html_retains_default_copy_and_escapes_custom_description(self):
        from radio.audition import report_html
        report={'variants':{},'sequence_seconds':20,'target_lufs':-22}
        self.assertIn('same musical score, different sound libraries',report_html(report))
        page=report_html(report,description='Different timing <img src=x> & rest')
        self.assertIn('Different timing &lt;img src=x&gt; &amp; rest',page)
        self.assertNotIn('<img src=x>',page)
        self.assertNotIn('same musical score, different sound libraries',page)


@unittest.skipUnless(all(shutil.which(name) for name in ('fluidsynth','ffmpeg','ffprobe')) and Path('/usr/share/sounds/sf2/TimGM6mb.sf2').is_file(), 'real audio engines unavailable')
class ProfileMediaTests(unittest.TestCase):
    def test_three_second_silence_cannot_pass_the_fractional_quiet_gate(self):
        from radio.profile_audition import audition_profile
        from radio.render import render_notes as real_render
        from radio.audition import command
        def gapped(config,notes,seconds,stem,*,arrangement):
            path,metrics=real_render(config,notes,seconds,stem,arrangement=arrangement)
            changed=path.with_suffix('.gapped.wav')
            command(['ffmpeg','-nostdin','-v','error','-y','-i',str(path),'-af',
                     "volume=0:enable='between(t,8,11)'",'-c:a','pcm_s16le',str(changed)])
            changed.replace(path)
            return path,metrics
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'pair'
            with patch('radio.profile_audition.render_notes',side_effect=gapped):
                with self.assertRaisesRegex(ValueError,'silence'):
                    audition_profile(output,Path('/usr/share/sounds/sf2/TimGM6mb.sf2'),positions=(1,),seconds=20)
            self.assertEqual(json.loads((output/'report.json').read_text())['status'],'failed')
            self.assertFalse((output/'index.html').exists())

    def test_real_pair_has_exact_scores_matched_audio_and_no_database(self):
        from radio.profile_audition import audition_profile,score_for
        from radio.compose import midi
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'pair'
            with patch('sqlite3.connect',side_effect=AssertionError('offline tool must not open SQLite')):
                report=audition_profile(output,Path('/usr/share/sounds/sf2/TimGM6mb.sf2'),positions=(2,3),seconds=20)
            self.assertEqual(report['status'],'complete');self.assertEqual(report['sequence_seconds'],35)
            for label,v in report['variants'].items():
                self.assertLessEqual(v['gain_db'],0)
                self.assertAlmostEqual(v['final_analysis']['duration'],35,delta=.1)
                self.assertAlmostEqual(v['final_loudness']['integrated_lufs'],report['target_lufs'],delta=.2)
                self.assertLessEqual(v['final_loudness']['true_peak_dbfs'],-2.9)
                for segment in v['segments']:
                    a,notes,bpm=score_for(label,42,segment['position'],20)
                    expected=hashlib.sha256(midi(notes,20,bpm,programs=a.programs)).hexdigest()
                    self.assertEqual(segment['midi_sha256'],expected)
                    self.assertEqual((output/label/'midi'/f'{segment["position"]}.mid').read_bytes(),midi(notes,20,bpm,programs=a.programs))
                self.assertTrue((output/label/'listen.mp3').is_file())
                self.assertTrue((output/label/'listen.wav').is_file())
            self.assertFalse(list(output.rglob('radio.sqlite')))
            page=(output/'index.html').read_text();self.assertIn('timing',page);self.assertIn('Pause other audio',page)


if __name__ == '__main__':
    unittest.main()
