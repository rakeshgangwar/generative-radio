"""Real installed Icecast/libxslt/Liquidsoap metadata boundary, no public ports."""
import base64
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from radio.config import Config
from radio.store import Store

ROOT=Path(__file__).resolve().parents[1]
TOOLS=all(shutil.which(name) for name in ['ffmpeg','liquidsoap','icecast2'])


@unittest.skipUnless(TOOLS,'requires installed real Icecast/Liquidsoap/FFmpeg')
class ContextStreamTests(unittest.TestCase):
    def test_cached_fallback_source_remains_infallible(self):
        script=(ROOT/'deploy/radio.liq').read_text()
        fragment=script[script.index('security ='):script.index('# Finish the current fallback')]
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);audio=root/'fallback.wav'
            subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','sine=duration=1','-ar','44100','-ac','2','-c:a','pcm_s16le',str(audio)],check=True,capture_output=True)
            text='log.file.set(false)\nlog.stdout.set(false)\n'+fragment.replace('/data/audio/fallback.wav',str(audio))
            text+='\noutput.icecast(%mp3(bitrate=128),host="127.0.0.1",port=12345,password="fixture",mount="/test",security)\n'
            (root/'check.liq').write_text(text)
            result=subprocess.run(['liquidsoap','--check',str(root/'check.liq')],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_output_labels_prefetch_fallback_filtered_json_and_escaping(self):
        stylesheet=ROOT/'deploy/broadcast-context-json.xsl'
        self.assertTrue(stylesheet.is_file(),'public context stylesheet is missing')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);data=root/'room, blue:one';(data/'audio').mkdir(parents=True)
            c=Config(data,20,20,60,42,'unused');store=Store(data)
            for index in (1,2,3):
                subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i',f'sine=frequency={220*index}:duration=20','-ar','44100','-ac','2','-c:a','pcm_s16le',str(data/'audio'/f'{index}.wav')],check=True,capture_output=True)
            shutil.copyfile(data/'audio/3.wav',data/'audio/fallback.wav')
            for chapter in (17,29):
                store.enqueue(c);job=store.claim();analysis={'arrangement':{'version':2,'chapter':chapter,'stage':'unfold','programs':[89,32,4]}}
                store.finish(job,data/'audio'/f'{job["id"]}.wav',analysis)
            env={**os.environ,'RADIO_DATA':str(data)};uris=[]
            for _ in range(2):
                result=subprocess.run([sys.executable,'-m','radio','next','--annotate'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=5)
                self.assertEqual(result.returncode,0,result.stderr);uris.append(result.stdout.strip())
            self.assertEqual(store.db.execute("SELECT count(*) FROM jobs WHERE status='served'").fetchone()[0],2)
            store.db.close()
            playlist=root/'tracks.m3u';playlist.write_text('\n'.join(uris)+'\n')
            web=root/'web';web.mkdir();shutil.copyfile(stylesheet,web/stylesheet.name)
            for name in ['xml2json.xslt','status-json.xsl']:
                shutil.copyfile(Path('/usr/share/icecast2/web')/name,web/name)
            with socket.socket() as reservation:
                reservation.bind(('127.0.0.1',0));port=reservation.getsockname()[1]
            config=ET.fromstring('''<icecast><location>Fixture</location><admin>test@localhost</admin><hostname>localhost</hostname><limits><clients>30</clients><sources>2</sources><queue-size>524288</queue-size><client-timeout>5</client-timeout><header-timeout>5</header-timeout><source-timeout>5</source-timeout></limits><authentication><source-password>probe-source</source-password><relay-password>probe-source</relay-password><admin-user>admin</admin-user><admin-password>probe-admin</admin-password></authentication><listen-socket><port>0</port><bind-address>127.0.0.1</bind-address></listen-socket><fileserve>1</fileserve><paths><basedir>/tmp</basedir><logdir>/tmp</logdir><webroot/><adminroot>/usr/share/icecast2/admin</adminroot></paths><logging><accesslog>-</accesslog><errorlog>-</errorlog><loglevel>2</loglevel></logging><security><chroot>0</chroot></security></icecast>''')
            config.find('listen-socket/port').text=str(port);config.find('paths/webroot').text=str(web);ET.ElementTree(config).write(root/'icecast.xml',encoding='unicode')
            actors=[];logs=[]
            def start(args,name):
                f=(root/name).open('w');logs.append(f);p=subprocess.Popen(args,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);actors.append(p);return p
            def get(path='/broadcast-context-json.xsl'):
                with urllib.request.urlopen(f'http://127.0.0.1:{port}'+path,timeout=1) as r:
                    self.assertTrue(r.headers.get_content_type()=='application/json',r.headers)
                    body=r.read(4097);self.assertLessEqual(len(body),4096);return json.loads(body)
            def until(predicate,seconds=10,path="/broadcast-context-json.xsl"):
                end=time.monotonic()+seconds;last=None
                while time.monotonic()<end:
                    try:
                        last=get(path)
                        if predicate(last):return last
                    except (OSError,ValueError):pass
                    time.sleep(.1)
                tail='\n'.join((root/p).read_text()[-2500:] for p in ['source.log','icecast.log'] if (root/p).exists())
                self.fail(f'context condition not met; last={last}\n{tail}')
            def output(source,mount):
                return f'output.icecast(%mp3(bitrate=128,samplerate=44100,stereo=true),host="127.0.0.1",port={port},password="probe-source",mount={json.dumps(mount)},name="Fixture",{source})\n'
            def stop(p):
                if p.poll() is None:
                    os.killpg(p.pid,signal.SIGTERM)
                    try:p.wait(5)
                    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
            try:
                start(['icecast2','-c',str(root/'icecast.xml')],'icecast.log')
                absent=until(lambda p:p=={'version':1,'available':False,'title':''})
                fallback='annotate:title="A quiet interlude.",artist="Generative Radio":'+str(data/'audio/fallback.wav')
                script='log.file.set(false)\nlog.stdout.set(true)\nm=playlist(mode="normal",reload_mode="never",loop=false,prefetch=2,'+json.dumps(str(playlist))+')\nf=single('+json.dumps(fallback)+')\ns=mksafe(crossfade(duration=5.,fallback(track_sensitive=true,[m,f])))\n'+output('s','/radio.mp3')
                (root/'source.liq').write_text(script);source=start(['liquidsoap',str(root/'source.liq')],'source.log')
                first=until(lambda p:'Chapter 17' in p.get('title',''),15)
                self.assertEqual(set(first),{'version','available','title'});self.assertTrue(first['available'])
                with sqlite3.connect(data/'radio.sqlite') as db:self.assertEqual(db.execute("SELECT count(*) FROM jobs WHERE status='served'").fetchone()[0],2)
                second=until(lambda p:'Chapter 29' in p.get('title',''),25)
                interlude=until(lambda p:'A quiet interlude.' in p.get('title',''),25)
                poison='quote " backslash \\ tab\t line\n return\r snow ☃ <img src=x onerror=alert(1)> '+('z'*200)
                query=urllib.parse.urlencode({'mode':'updinfo','mount':'/radio.mp3','song':poison,'charset':'UTF-8'})
                req=urllib.request.Request(f'http://127.0.0.1:{port}/admin/metadata?'+query,headers={'Authorization':'Basic '+base64.b64encode(b'admin:probe-admin').decode()})
                with urllib.request.urlopen(req,timeout=2) as r:r.read(4096)
                # Icecast can entity-normalize non-ASCII admin metadata before XSLT.
                # Compare with its published stats, not the original HTTP form.
                stats=until(lambda p:'snow' in p['icestats'].get('source',{}).get('title',''),
                            5,path='/status-json.xsl')['icestats']['source']
                published=stats['title']
                self.assertIn('snow',published)
                self.assertIn('quote " backslash \\',published)
                escaped=until(lambda p:p.get('title')==published[:160],5)
                self.assertEqual(escaped,{'version':1,'available':True,'title':published[:160]})
                stop(source);until(lambda p:p['available'] is False,5)
                other_uri='annotate:title="Other mount private label",artist="Other":'+str(data/'audio/fallback.wav')
                other='log.file.set(false)\nlog.stdout.set(true)\ns=mksafe(single('+json.dumps(other_uri)+'))\n'+output('s','/other.mp3')
                (root/'other.liq').write_text(other);start(['liquidsoap',str(root/'other.liq')],'other.log')
                end=time.monotonic()+10
                while True:
                    stats=get('/status-json.xsl')['icestats'].get('source') or []
                    if isinstance(stats,dict):stats=[stats]
                    if any('Other mount' in x.get('title','') for x in stats):break
                    if time.monotonic()>end or actors[-1].poll() is not None:
                        self.fail(f'other mount failed; stats={stats}; exit={actors[-1].poll()}\n'+(root/'other.log').read_text()[-4000:])
                    time.sleep(.1)
                self.assertEqual(get(),absent)
            finally:
                for p in reversed(actors):stop(p)
                for f in logs:f.close()
