import http.server
import json
import math
import os
import signal
import sys
from unittest.mock import patch
from pathlib import Path
import shutil
import ssl
import subprocess
import tempfile
import threading
import time
import unittest

from radio.production import probe_https, ProductionError

TOOLS=all(shutil.which(name) for name in ['ffmpeg','curl','openssl'])


@unittest.skipUnless(TOOLS,'real HTTPS audio tools required')
class PublicListenerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();root=Path(cls.temp.name)
        cls.cert=root/'root.pem';key=root/'key.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost',
                        '-addext','subjectAltName=DNS:localhost','-keyout',str(key),'-out',str(cls.cert)],capture_output=True,check=True)
        for name,source in [('short','sine=frequency=220:sample_rate=44100'),('tone','sine=frequency=220:sample_rate=44100'),('silent','anullsrc=r=44100:cl=stereo')]:
            subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-f','lavfi','-i',source,'-t','1' if name=='short' else '5','-ac','2',
                            '-c:a','libmp3lame','-b:a','128k',str(root/(name+'.mp3'))],capture_output=True,check=True)
        cls.tone=(root/'tone.mp3').read_bytes();cls.silent=(root/'silent.mp3').read_bytes();cls.short=(root/'short.mp3').read_bytes()
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*_):pass
            def do_GET(self):
                if self.server.stall:time.sleep(3)
                elif self.server.delay:time.sleep(self.server.delay)
                self.server.requests.append(self.path)
                body=self.server.payload if self.path=='/radio.mp3' else b'<title>Generative Radio</title>'
                kind='audio/mpeg' if self.path=='/radio.mp3' else 'text/html'
                flood=self.server.flood and self.path=='/radio.mp3'
                if flood:body=body*8
                self.send_response(200);self.send_header('Content-Type',kind)
                if self.server.big_headers:self.send_header('X-Padding','x'*70000)
                if not flood:self.send_header('Content-Length',str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                    if flood:time.sleep(10)
                except (OSError,ssl.SSLError):pass
        class Server(http.server.ThreadingHTTPServer):
            daemon_threads=True
            def handle_error(self,*_):pass
        cls.server=Server(('127.0.0.1',0),Handler);cls.server.payload=cls.tone;cls.server.stall=False;cls.server.flood=False;cls.server.big_headers=False;cls.server.delay=0;cls.server.requests=[]
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(cls.cert,key)
        cls.server.socket=context.wrap_socket(cls.server.socket,server_side=True)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.origin=f'https://localhost:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=2);cls.temp.cleanup()

    def setUp(self):self.server.payload=self.tone;self.server.stall=False;self.server.flood=False;self.server.big_headers=False;self.server.delay=0;self.server.requests=[]

    def test_mp3_content_type_and_bytes_cannot_disguise_junk(self):
        self.server.payload=b'not an mp3'*2048
        with self.assertRaises(ProductionError):probe_https(self.origin,self.cert)

    def test_encoded_silence_is_not_verified_as_audible_stream(self):
        self.server.payload=self.silent
        with self.assertRaises(ProductionError):probe_https(self.origin,self.cert)

    def test_valid_trusted_audio_is_decoded_and_reported(self):
        result=probe_https(self.origin,self.cert)
        self.assertTrue(result['page_verified']);self.assertTrue(result['stream_verified'])
        self.assertAlmostEqual(result['decoded_seconds'],3,places=2);self.assertGreater(result['rms_dbfs'],-50)

    def test_untrusted_and_wrong_hostname_fail(self):
        with self.assertRaises(ProductionError):probe_https(self.origin)
        with self.assertRaises(ProductionError):probe_https(self.origin.replace('localhost','127.0.0.1'),self.cert)

    def test_short_real_mp3_is_incomplete(self):
        self.server.payload=self.short
        with self.assertRaises(ProductionError):probe_https(self.origin,self.cert)

    def test_unknown_length_body_never_exceeds_the_prefix_budget(self):
        from radio.listener_health import fetch,ListenerHealthError,SAMPLE_BYTES
        self.server.flood=True
        with tempfile.TemporaryDirectory() as temp:
            sample=Path(temp)/'sample.mp3';error=None
            try:fetch(self.origin,'/radio.mp3',sample,time.monotonic()+12,self.cert,stream=True)
            except ListenerHealthError as caught:error=caught
            self.assertTrue(sample.exists())
            self.assertLessEqual(sample.stat().st_size,SAMPLE_BYTES,'unknown-length download exceeded hard prefix budget')
            self.assertIsNone(error,'a complete bounded prefix should be usable')

    def test_large_headers_are_rejected_before_unbounded_storage(self):
        from radio.listener_health import probe,ListenerHealthError
        self.server.big_headers=True
        with self.assertRaises(ListenerHealthError) as error:probe(self.origin,self.cert)
        self.assertEqual(error.exception.kind,'response')

    def test_embedded_playlist_cannot_make_the_decoder_fetch_urls(self):
        self.server.payload=(b'#EXTM3U\n#EXT-X-TARGETDURATION:3\n#EXTINF:3,\n'+(self.origin+'/should-not-fetch').encode()+b'\n')*100
        with self.assertRaises(ProductionError):probe_https(self.origin,self.cert)
        self.assertNotIn('/should-not-fetch',self.server.requests)

    def test_two_slow_phases_do_not_each_get_a_new_deadline(self):
        from radio.listener_health import probe,ListenerHealthError
        self.server.delay=.65;started=time.monotonic()
        with self.assertRaises(ListenerHealthError):probe(self.origin,self.cert,timeout=1)
        self.assertLess(time.monotonic()-started,1.8)

    def test_real_header_hang_obeys_one_overall_deadline(self):
        from radio.listener_health import probe,ListenerHealthError
        self.server.stall=True;start=time.monotonic()
        with self.assertRaises(ListenerHealthError):probe(self.origin,self.cert,timeout=1)
        self.assertLess(time.monotonic()-start,2.5)

    def test_cli_returns_safe_json_and_cleans_owned_curl_on_sigterm(self):
        command=[sys.executable,'-m','radio.listener_health','--url',self.origin,'--ca-file',str(self.cert)]
        result=subprocess.run(command,capture_output=True,text=True,timeout=25)
        self.assertEqual(result.returncode,0,result.stderr);self.assertTrue(json.loads(result.stdout)['healthy'])
        secret='SecretThatMustNotBePrinted'
        invalid=subprocess.run([sys.executable,'-m','radio.listener_health','--url','https://user:'+secret+'@invalid.example'],capture_output=True,text=True,timeout=5)
        self.assertNotEqual(invalid.returncode,0);self.assertNotIn(secret,invalid.stdout+invalid.stderr)
        self.server.stall=True
        process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        child=None
        try:
            deadline=time.monotonic()+3
            while time.monotonic()<deadline and process.poll() is None:
                children=Path(f'/proc/{process.pid}/task/{process.pid}/children').read_text().split()
                if children:child=int(children[0]);break
                time.sleep(.02)
            self.assertIsNotNone(child,'CLI did not start its owned curl')
            process.send_signal(signal.SIGTERM);out,err=process.communicate(timeout=3)
            self.assertEqual(process.returncode,130,(out,err));self.assertEqual(json.loads(out)['kind'],'cancelled')
            self.assertFalse(Path(f'/proc/{child}').exists(),'owned curl survived cancellation')
        finally:
            if process.poll() is None:process.kill();process.communicate()


class PublicListenerPolicyTests(unittest.TestCase):
    def test_origin_rejection_happens_before_any_subprocess(self):
        from radio.listener_health import probe,ListenerHealthError
        for origin in ['http://radio.invalid','https://user:secret@radio.invalid','https://radio.invalid/path',
                       'https://radio.invalid?q=secret','https://radio.invalid/#fragment','https://radio.invalid:bad',
                       'https://[invalid','https://radio.invalid?','https://radio.invalid#','https://@radio.invalid','https://radio.invalid\n','https://radio.invalid:99999','https://réseau.invalid']:
            with self.subTest(origin=origin),patch('radio.listener_health.subprocess.Popen') as spawn:
                with self.assertRaises(ListenerHealthError):probe(origin)
                spawn.assert_not_called()

    def test_budget_and_missing_ca_fail_before_network(self):
        from radio.listener_health import probe,ListenerHealthError
        for budget in [0,.5,61,math.inf,math.nan,True]:
            with self.subTest(budget=budget),patch('radio.listener_health.subprocess.Popen') as spawn:
                with self.assertRaises(ListenerHealthError):probe('https://radio.invalid',timeout=budget)
                spawn.assert_not_called()
        with self.assertRaises(ListenerHealthError):probe('https://radio.invalid',ca_file='/definitely/not/a/ca.pem')

    def test_local_temporary_failure_has_safe_typed_diagnostics(self):
        from radio.listener_health import probe,ListenerHealthError
        with patch('radio.listener_health.tempfile.TemporaryDirectory',side_effect=OSError('SecretPathMarker')):
            with self.assertRaises(ListenerHealthError) as error:probe('https://radio.invalid')
        self.assertEqual(error.exception.kind,'tool');self.assertNotIn('SecretPathMarker',str(error.exception))

    def test_cli_argument_errors_are_safe_configuration_json(self):
        marker='SecretArgumentMarker'
        for args in [[],['--url','https://radio.invalid','--timeout',marker],
                     ['--url','https://radio.invalid','--unknown',marker]]:
            with self.subTest(args=args):
                result=subprocess.run([sys.executable,'-m','radio.listener_health',*args],capture_output=True,text=True,timeout=5)
                self.assertEqual(result.returncode,1)
                report=json.loads(result.stdout);self.assertFalse(report['healthy']);self.assertEqual(report['kind'],'configuration')
                self.assertNotIn(marker,result.stdout+result.stderr);self.assertEqual(result.stderr,'')
        help_result=subprocess.run([sys.executable,'-m','radio.listener_health','--help'],capture_output=True,text=True,timeout=5)
        self.assertEqual(help_result.returncode,0);self.assertIn('usage:',help_result.stdout)
