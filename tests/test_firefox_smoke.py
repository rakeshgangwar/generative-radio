import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from radio.firefox_smoke import Options, run
from radio.watchdog import terminate_process

SECRET = "private-protocol-error-canary"
DRIVER = r'''#!/usr/bin/env python3
import argparse,json,os,time
from pathlib import Path
from http.server import BaseHTTPRequestHandler,HTTPServer
parser=argparse.ArgumentParser();parser.add_argument('--port',type=int);parser.add_argument('--profile-root');args,_=parser.parse_known_args()
Path(os.environ['RADIO_TEST_DRIVER_PID']).write_text(str(os.getpid()))
Path(args.profile_root,'private-profile').write_text('owned profile')
mode=os.environ['RADIO_TEST_DRIVER_MODE'];url_reads=0
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        global url_reads
        if self.path.endswith('/url'):
            url_reads+=1
            value='http://example.com/' if mode in ('redirect','redirect_slow') or (mode=='redirect_late' and url_reads>1) else 'http://127.0.0.1:8080/'
        else:value={'ready':True}
        body=json.dumps({'value':value}).encode()
        self.send_response(200);self.end_headers();self.wfile.write(body)
    def do_POST(self):
        self.rfile.read(int(self.headers.get('Content-Length','0')))
        Path(os.environ['RADIO_TEST_DRIVER_PHASE']).write_text('request')
        if mode=='stall':time.sleep(30)
        if mode=='redirect_slow' and self.path=='/session':time.sleep(16)
        if mode=='drip':
            self.send_response(200);self.send_header('Content-Length','2000');self.end_headers()
            for _ in range(2000):self.wfile.write(b' ');self.wfile.flush();time.sleep(.1)
            return
        if mode in ('redirect','redirect_late','redirect_slow'):
            if self.path=='/session':value={'sessionId':'fixture','capabilities':{'browserName':'firefox','platformName':'linux','browserVersion':'157'}}
            elif self.path.endswith('/execute/sync'):value={'ready':True,'player_state':'idle','current_time':0,'ready_state':0,'network_state':0,'paused':True,'error_code':None}
            elif self.path.endswith('/element'):value={'element-6066-11e4-a52e-4f735466cecf':'button'}
            elif self.path.endswith('/click'):
                Path(os.environ['RADIO_TEST_DRIVER_PHASE']+'.clicked').write_text('clicked after redirect')
                value={'error':'unknown error','message':'private-protocol-error-canary'}
            else:value=None
            body=json.dumps({'value':value}).encode()
        elif mode=='oversize':body=b'x'*(1024*1024+1)
        elif mode=='nested':body=b'{"value":'+b'['*1900+b'0'+b']'*1900+b'}'
        elif mode=='missing':body=b'{"value":{"sessionId":"../../private","capabilities":{"browserName":"firefox","browserVersion":"private-protocol-error-canary"}}}'
        else:body=b'{"value":{"error":"session not created","message":"private-protocol-error-canary"}}'
        self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
HTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
'''

class OptionsTests(unittest.TestCase):
    def make(self,root,**kwargs):
        values=dict(driver=Path(sys.executable),firefox=Path(sys.executable),output=root/'new',url='http://127.0.0.1:8080/',timeout=120)
        values.update(kwargs);return Options(**values)

    def test_only_loopback_root_without_credentials_or_query(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for url in ['http://127.0.0.1:8080/','http://localhost/','http://[::1]:8080/']:
                self.make(root,url=url)
            for url in ['https://127.0.0.1/','http://example.com/','http://127.0.0.1.evil/','http://user:secret@localhost/','http://localhost/?private=1','http://localhost/#x','http://localhost/admin/','http://localhost:0/']:
                with self.subTest(url=url),self.assertRaises(ValueError):self.make(root,url=url)
            self.assertFalse((root/'new').exists())

    def test_bounds_and_executable_validation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for timeout in [0,301,float('nan'),float('inf')]:
                with self.subTest(timeout=timeout),self.assertRaises(ValueError):self.make(root,timeout=timeout)
            with self.assertRaises(ValueError):self.make(root,driver=root/'missing')
            nonexec=root/'nonexec';nonexec.write_text('no')
            with self.assertRaises(ValueError):self.make(root,firefox=nonexec)

    def test_existing_output_and_station_data_remain_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);existing=root/'existing';existing.mkdir();marker=existing/'keep';marker.write_text('keep')
            with self.assertRaises(ValueError):self.make(root,output=existing)
            (root/'radio.sqlite').write_text('station')
            with self.assertRaises(ValueError):self.make(root)
            self.assertEqual(marker.read_text(),'keep');self.assertFalse((root/'new').exists())

class OwnedProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.driver=self.root/'driver with spaces'
        self.driver.write_text('#!'+sys.executable+'\n'+DRIVER.split('\n',1)[1]);self.driver.chmod(0o755)

    def command(self,mode):
        output=self.root/mode
        env={**os.environ,'RADIO_TEST_DRIVER_MODE':mode,'RADIO_TEST_DRIVER_PID':str(self.root/(mode+'.pid')),'RADIO_TEST_DRIVER_PHASE':str(self.root/(mode+'.phase'))}
        args=[sys.executable,'-m','radio.firefox_smoke','--driver',str(self.driver),'--firefox',sys.executable,'--output',str(output),'--timeout','1']
        return args,env,output

    def assert_receipt(self,mode,output,expected_state='failed',expected_checks=0):
        result=json.loads((output/'result.json').read_text())
        self.assertEqual(result['state'],expected_state);self.assertFalse(result['pass']);self.assertEqual(len(result['checks']),expected_checks)
        self.assertTrue(result['cleanup']['driver_reaped']);self.assertFalse((output/'.profiles').exists())
        self.assertEqual(output.stat().st_mode&0o777,0o700)
        self.assertNotIn(SECRET,(output/'result.json').read_text())
        pid=int((self.root/(mode+'.pid')).read_text())
        with self.assertRaises(ProcessLookupError):os.kill(pid,0)
        return result

    def test_protocol_errors_caps_and_depth_fail_without_false_pass(self):
        for mode in ['error','oversize','nested','missing']:
            with self.subTest(mode=mode):
                args,env,out=self.command(mode)
                p=subprocess.run(args,env=env,capture_output=True,text=True,timeout=6)
                self.assertEqual(p.returncode,1,p.stderr);self.assertNotIn(SECRET,p.stdout+p.stderr)
                self.assert_receipt(mode,out)

    def test_nonlocal_redirect_fails_before_playback_controls(self):
        args,env,out=self.command('redirect')
        p=subprocess.run(args,env=env,capture_output=True,text=True,timeout=6)
        self.assertEqual(p.returncode,1,p.stderr)
        result=self.assert_receipt('redirect',out)
        self.assertEqual(result['failure']['stage'],'navigate')

    def test_redirect_between_idle_and_click_is_blocked(self):
        args,env,out=self.command('redirect_late')
        p=subprocess.run(args,env=env,capture_output=True,text=True,timeout=6)
        self.assertEqual(p.returncode,1,p.stderr)
        self.assert_receipt('redirect_late',out,expected_checks=1)
        self.assertFalse((self.root/'redirect_late.phase.clicked').exists(),'must not click after navigation left the allowed origin')

    def test_whole_deadline_bounds_stalled_and_dripping_http(self):
        for mode in ['stall','drip']:
            with self.subTest(mode=mode):
                args,env,out=self.command(mode);start=time.monotonic()
                p=subprocess.run(args,env=env,capture_output=True,text=True,timeout=6)
                self.assertEqual(p.returncode,1,p.stderr);self.assertLess(time.monotonic()-start,4)
                result=self.assert_receipt(mode,out)
                self.assertEqual(result['failure']['kind'],'deadline')

    def test_startup_response_inside_whole_budget_is_not_cut_at_fifteen_seconds(self):
        args,env,out=self.command('redirect_slow');args[-1]='22'
        p=subprocess.run(args,env=env,capture_output=True,text=True,timeout=27)
        self.assertEqual(p.returncode,1,p.stderr)
        result=self.assert_receipt('redirect_slow',out)
        self.assertEqual(result.get('browser',{}).get('name'),'firefox')
        self.assertEqual(result['failure']['stage'],'navigate')

    def test_sigterm_cancels_http_and_reaps_owned_driver(self):
        args,env,out=self.command('stall');args[-1]='60'
        p=subprocess.Popen(args,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            deadline=time.monotonic()+5
            while not (self.root/'stall.phase').exists():
                if p.poll() is not None or time.monotonic()>deadline:self.fail('driver did not reach HTTP request')
                time.sleep(.02)
            start=time.monotonic();p.terminate();stdout,stderr=p.communicate(timeout=5)
            self.assertEqual(p.returncode,130,stderr);self.assertLess(time.monotonic()-start,3)
            self.assert_receipt('stall',out,'cancelled')
        finally:
            if p.poll() is None:p.kill();p.communicate()


class AcquisitionSignalTests(unittest.TestCase):
    def test_signal_at_popen_return_cannot_escape_owned_cleanup(self):
        for signum,expected in [(signal.SIGTERM,130),(signal.SIGINT,130),(signal.SIGALRM,1)]:
            with self.subTest(signal=signum),tempfile.TemporaryDirectory() as directory:
                root=Path(directory)
                driver=root/'sleeping-driver'
                driver.write_text('#!'+sys.executable+'\nimport time; time.sleep(30)\n');driver.chmod(0o755)
                options=Options(driver=driver,firefox=Path(sys.executable),output=root/'result',timeout=60)
                created=[]
                original_trace=sys.gettrace()
                def trace(frame,event,arg):
                    if event=='return' and frame.f_code is subprocess.Popen.__init__.__code__ and not created:
                        created.append(frame.f_locals['self'])
                        os.kill(os.getpid(),signum)
                    return trace
                try:
                    try:
                        sys.settrace(trace)
                        code=run(options)
                    finally:
                        sys.settrace(original_trace)
                    self.assertEqual(code,expected)
                    report=json.loads((options.output/'result.json').read_text())
                    self.assertFalse(report['pass']);self.assertTrue(report['cleanup']['driver_reaped'])
                    self.assertTrue(report['cleanup']['profiles_removed'])
                    self.assertEqual(len(created),1)
                    with self.assertRaises(ProcessLookupError):os.kill(created[0].pid,0)
                finally:
                    sys.settrace(original_trace)
                    for process in created:terminate_process(process,.1)


class MediaDiagnosticTests(unittest.TestCase):
    def test_snapshot_keeps_only_known_bounded_media_fields(self):
        from radio import firefox_smoke as smoke
        value=dict(player_state='playing',current_time=2.5,ready_state=4,network_state=2,paused=False,error_code=None,last_error_code=4,play_error_name='NotSupportedError',url=SECRET,message=SECRET,html=SECRET)
        expected=dict(player_state='playing',current_time=2.5,ready_state=4,network_state=2,paused=False,error_code=None,last_error_code=4,play_error_name='NotSupportedError')
        self.assertEqual(smoke.media_snapshot(value),expected)
        for bad in [float('nan'),float('inf'),10**400,-1]:
            self.assertNotIn('current_time',smoke.media_snapshot({**value,'current_time':bad}))
        unknown=smoke.media_snapshot(dict(player_state=SECRET,ready_state=900,network_state=-1,paused=SECRET,error_code=SECRET,play_error_name=SECRET))
        self.assertNotIn(SECRET,json.dumps(unknown));self.assertEqual(unknown,{})
