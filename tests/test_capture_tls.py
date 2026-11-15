import array
import functools
import http.server
import math
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import tempfile
import threading
import unittest
import wave


TOOLS=all(shutil.which(name) for name in ['ffmpeg','ffprobe','openssl','curl'])

@unittest.skipUnless(TOOLS,'TLS capture tests require FFmpeg, curl and OpenSSL')
class TLSCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=tempfile.TemporaryDirectory();root=Path(cls.fixture.name)
        cls.cert=root/'ca.pem';key=root/'key.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1',
                        '-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost',
                        '-keyout',str(key),'-out',str(cls.cert)],check=True,capture_output=True)
        with wave.open(str(root/'input.wav'),'wb') as audio:
            audio.setparams((2,2,44100,0,'NONE','not compressed'))
            values=array.array('h',[int(6000*math.sin(2*math.pi*220*i/44100)) for i in range(88200) for _ in range(2)])
            audio.writeframes(values.tobytes())
        class Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self,*_):pass
        class Server(http.server.ThreadingHTTPServer):
            daemon_threads=True
            def handle_error(self,*_):pass  # Clients intentionally stop after one second.
        cls.server=Server(('127.0.0.1',0),functools.partial(Handler,directory=str(root)))
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(cls.cert,key)
        cls.server.socket=context.wrap_socket(cls.server.socket,server_side=True)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.port=cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=2);cls.fixture.cleanup()

    def capture(self,trusted=False,hostname='localhost'):
        with tempfile.TemporaryDirectory() as temp:
            env=os.environ|{'RADIO_STREAM_URL':f'https://{hostname}:{self.port}/input.wav'}
            env.pop('RADIO_TLS_CA_FILE',None)
            if trusted:env['RADIO_TLS_CA_FILE']=str(self.cert)
            script=Path(__file__).resolve().parents[1]/'scripts/capture.sh'
            return subprocess.run(['sh',str(script),'1'],cwd=temp,env=env,capture_output=True,text=True,timeout=15)

    def test_untrusted_https_is_rejected(self):
        result=self.capture();self.assertNotEqual(result.returncode,0,'Untrusted TLS was accepted')
        self.assertNotIn('Recording:',result.stdout)

    def test_trusted_https_is_recorded(self):
        result=self.capture(trusted=True);self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Recording:',result.stdout)

    def test_valid_ca_with_wrong_hostname_is_rejected(self):
        result=self.capture(trusted=True,hostname='127.0.0.1')
        self.assertNotEqual(result.returncode,0,'TLS hostname mismatch was accepted')
        self.assertNotIn('Recording:',result.stdout)


if __name__=='__main__':unittest.main()
