import contextlib
from dataclasses import asdict
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from radio.arrangement import arrangement_for
from radio.config import Config
import radio.__main__ as service
import radio.render as rendering


class ArrangementIntegrationTests(unittest.TestCase):
    def test_renderer_flag_is_strict_and_defaults_on(self):
        with tempfile.TemporaryDirectory() as temp:
            for value,expected in [(None,True),('1',True),('0',False)]:
                env={'RADIO_DATA':temp}
                if value is not None:env['MUSICAL_MEMORY']=value
                with patch.dict(os.environ,env,clear=True):
                    self.assertEqual(Config.load().musical_memory,expected)
            for value in ['true','false','2','']:
                with patch.dict(os.environ,{'RADIO_DATA':temp,'MUSICAL_MEMORY':value},clear=True):
                    with self.assertRaises(ValueError):Config.load()

    def _renderer(self,memory):
        with tempfile.TemporaryDirectory() as temp:
            data=Path(temp);(data/'audio').mkdir();(data/'audio/fallback.wav').write_bytes(b'fallback')
            config=Config(data,20,20,60,9999,'unused',musical_memory=memory)
            stop=threading.Event();calls=[]
            class Queue:
                def heartbeat(self,role):pass
                def claim(self):return {'id':7,'seed':49,'seconds':20,'bpm':60}
                def finish(self,*args):stop.set()
                def fail(self,*args):stop.set();raise AssertionError(args)
            def render(config,seed,seconds,stem,**kwargs):
                calls.append((seed,seconds,stem,kwargs));return data/'audio/7.wav',{'duration':20}
            with patch.object(service.Config,'load',return_value=config),patch.object(service,'Store',return_value=Queue()),patch.object(service,'render',side_effect=render),patch.object(service,'stop',stop),patch('sys.argv',['radio','renderer']):
                service.main()
            return calls

    def test_renderer_uses_saved_job_origin_not_current_station_seed(self):
        calls=self._renderer(True)
        self.assertEqual(len(calls),1)
        seed,seconds,stem,kwargs=calls[0]
        self.assertEqual((seed,seconds,stem),(49,20,7))
        self.assertEqual(kwargs.get('arrangement'),arrangement_for(42,7))

    def test_renderer_flag_can_restore_legacy_independent_arrangements(self):
        self.assertIsNone(self._renderer(False)[0][3].get('arrangement'))

    def _preview(self,args):
        with tempfile.TemporaryDirectory() as temp:
            config=Config(Path(temp),20,20,60,1,'unused')
            output=io.StringIO();calls=[]
            def render(config,seed,seconds,stem,**kwargs):
                calls.append((seed,seconds,stem,kwargs))
                return config.data/'audio/preview.wav',{'duration':seconds}
            with patch.object(service.Config,'load',return_value=config),patch.object(service,'Store'),patch.object(service,'render',side_effect=render),patch('sys.argv',['radio','preview',*args]),contextlib.redirect_stdout(output),contextlib.redirect_stderr(io.StringIO()):
                service.main()
            return calls,json.loads(output.getvalue())

    def test_explicit_planned_preview_and_legacy_preview_are_distinct(self):
        calls,result=self._preview(['--station-seed','42','--position','7','--seconds','20'])
        self.assertEqual(calls[0][:3],(49,20,'preview-7'))
        self.assertEqual(calls[0][3]['arrangement'],arrangement_for(42,7))
        self.assertEqual(result['duration'],20)
        legacy,_=self._preview(['--seed','42','--seconds','20'])
        self.assertEqual(legacy[0][:3],(42,20,'preview'))
        self.assertIsNone(legacy[0][3].get('arrangement'))

    def test_preview_rejects_missing_invalid_or_ambiguous_position(self):
        for args in [['--station-seed','42'],['--position','7'],['--station-seed','42','--position','0'],['--station-seed','42','--position','-1'],['--seed','4','--station-seed','42','--position','7']]:
            with self.subTest(args=args),self.assertRaises(SystemExit) as error:
                self._preview(args)
            self.assertEqual(error.exception.code,2)

    def test_render_writes_planned_programs_and_versioned_analysis(self):
        with tempfile.TemporaryDirectory() as temp:
            data=Path(temp);config=Config(data,20,20,60,42,'unused');plan=arrangement_for(42,7)
            def run(args,**kwargs):
                if args[0]=='ffmpeg':Path(args[-1]).write_bytes(b'validated wave fixture')
            with patch.object(rendering,'run',side_effect=run),patch.object(rendering,'analyze',return_value={'duration':20,'peak':.5}):
                path,analysis=rendering.render(config,49,20,7,arrangement=plan)
            self.assertTrue(path.is_file())
            self.assertEqual(analysis['arrangement'],asdict(plan))
            self.assertEqual(json.loads(json.dumps(analysis))['arrangement']['position'],7)
            blob=(data/'midi/7.mid').read_bytes()
            for channel,program in enumerate(plan.programs):
                offset=29+11*channel
                self.assertEqual(blob[offset:offset+3],bytes([0,0xC0|channel,program]))
            self.assertEqual(list((data/'work').iterdir()),[])


if __name__=='__main__':unittest.main()
