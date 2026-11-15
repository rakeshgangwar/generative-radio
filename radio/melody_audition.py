"""Offline same-font comparison of version2 and sparse melodic connections."""
import argparse
from datetime import datetime,timezone
import html
import json
from pathlib import Path
import subprocess
import time

from .arrangement import arrangement_for
from .compose import compose,midi
from .config import Config
from .render import render,render_notes,analyze
from .melodic_connections import connect_melody
from .audition import (validate_inputs,digest,digest_bytes,engine_versions,write_report,
                      stitch,measure,shared_level,check_levels,command)


def report_html(report):
    labels={'baseline':'Version 2','connections':'Melodic connections'}
    sections=[]
    for key,name in labels.items():
        v=report['variants'][key]
        sections.append(f'<section><h2>{name}</h2><audio controls preload="none" aria-label="Listen to {name}" src="{key}/listen.mp3"></audio>'
                        f'<p>{v["final_loudness"]["integrated_lufs"]:.2f} LUFS; {v["gain_db"]:.2f} dB level adjustment.</p>'
                        f'<a href="{key}/listen.wav">Download measured WAV</a></section>')
    moments=[]
    for item in report.get('changes',[]):
        seconds=int(item['sequence_seconds'])
        moments.append(f'<li><button type="button" disabled data-seek="{max(0,item["sequence_seconds"]-3):.6f}">Compare near {seconds//60}:{seconds%60:02d}</button> — segment {item["position"]}</li>')
    guide=('<h2>Places to compare</h2><p id="phrase-status" role="status">Choose a phrase, then press play on either version. Both players cue three seconds before the note. SoundFont release and MP3 timing can differ slightly.</p><noscript><p>Use the listed times with the native audio controls when JavaScript is off.</p></noscript><ul>'+''.join(moments)+'</ul>') if moments else '<p>No eligible connections were added for these positions; this comparison does not claim a musical change.</p>'
    font=html.escape(Path(report['font']['path']).name)
    comparison='The same SoundFont, different scores.' if report['added_notes'] else 'The same SoundFont, identical scores for these positions.'
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>Melody audition — Generative Radio</title><style>body{font:18px/1.6 system-ui;max-width:800px;margin:3rem auto;padding:0 1rem;color:#17344b;background:#d8e3ed}h1,h2{font-family:Palatino,serif}section{border-top:1px solid #4a6275;padding:1rem 0}audio{max-width:100%}a{color:inherit}button{font:inherit;color:inherit;background:none;border:0;padding:.2rem .15rem;min-height:44px;text-decoration:underline;cursor:pointer}button:focus-visible{outline:2px solid #17344b;outline-offset:3px}button:disabled{cursor:default;text-decoration:none}</style>'
            f'<h1>Two ways a melody can unfold.</h1><p>{comparison} Pause other audio first. '
            'Play one version at a time and compare the same moment. Levels are matched with attenuation only; metrics cannot decide which feels better.</p>'
            f'<p>Sound: {font}. Duration: {report["sequence_seconds"]:.1f} seconds. Shared level: {report["target_lufs"]:.2f} LUFS. '
            f'{report["added_notes"]} quiet connecting notes. This is an offline experiment; the station is unchanged.</p>'
            +''.join(sections)+guide+'<p><a href="report.json">Measurements, score changes and source fingerprints</a></p>'
            '<script>const tracks=[...document.querySelectorAll("audio")],targets=new Map();for(const track of tracks){track.addEventListener("play",()=>{for(const other of tracks)if(other!==track)other.pause();});track.addEventListener("loadedmetadata",()=>{if(targets.has(track))track.currentTime=targets.get(track);});}for(const button of document.querySelectorAll("[data-seek]")){button.disabled=false;button.addEventListener("click",()=>{const target=Number(button.dataset.seek);if(!Number.isFinite(target)||target<0)return;for(const track of tracks){track.pause();targets.set(track,target);if(track.readyState>=1)track.currentTime=target;else{track.preload="metadata";track.load();}}document.querySelector("#phrase-status").textContent="Both players are cued three seconds before this note. Press play on either version.";});}</script></html>')


def audition_melody(output,soundfont,station_seed=42,positions=(1,2,3),seconds=120,bpm=60):
    # The two score variants intentionally share one font; reuse comparison bounds.
    fonts=validate_inputs({'baseline':soundfont,'connections':soundfont},positions,seconds,bpm,station_seed)
    if fonts['baseline']!=fonts['connections']:
        raise ValueError('SoundFont changed during validation')
    font=fonts['baseline'];output=Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    parent=output.parent.resolve(strict=True)
    if any((d/'radio.sqlite').exists() or (d/'radio.sqlite').is_symlink() for d in [parent,*parent.parents]):
        raise ValueError('Choose an audition output outside station data')
    metadata={'path':str(font),'size_bytes':font.stat().st_size,'sha256':digest(font)}
    output.mkdir()
    report={'version':1,'status':'running','created_at':datetime.now(timezone.utc).isoformat(),
            'experiment':{'name':'melodic-connections','version':1,'scope':'offline-only'},
            'font':metadata,'station_seed':station_seed,'positions':list(positions),
            'segment_seconds':seconds,'bpm':bpm,
            'sequence_seconds':len(positions)*seconds-(len(positions)-1)*5,
            'added_notes':0,'shortened_tails':0,'changes':[],'variants':{}}
    write_report(output,report)
    try:
        report['engines']=engine_versions()
        report['source_sha256']={name:digest(Path(__file__).with_name(name)) for name in ['melody_audition.py','melodic_connections.py','audition.py','compose.py','arrangement.py','render.py']}
        scores={}
        for index,position in enumerate(positions):
            a=arrangement_for(station_seed,position);base=compose(station_seed+position,seconds,bpm,a)
            connected=connect_melody(base,seconds,bpm,a)
            added=connected[len(base):]
            shortened=sum(left.duration!=right.duration for left,right in zip(base,connected))
            scores[position]=(a,base,connected,shortened)
            report['added_notes']+=len(added);report['shortened_tails']+=shortened
            for note in added:
                report['changes'].append({'position':position,'segment_seconds':note.start,
                                          'sequence_seconds':index*(seconds-5)+note.start,
                                          'pitch':note.pitch,'duration':note.duration,'velocity':note.velocity})
        for label in ('baseline','connections'):
            data=output/label;data.mkdir()
            config=Config.from_env({'RADIO_DATA':str(data),'BPM':str(bpm),'SOUNDFONT':str(font)})
            variant={'font_sha256':metadata['sha256'],'segments':[]};report['variants'][label]=variant;paths=[]
            for position in positions:
                a,base,connected,shortened=scores[position];notes=base if label=='baseline' else connected
                expected=digest_bytes(midi(notes,seconds,bpm,programs=a.programs));started=time.monotonic()
                if label=='baseline':path,metrics=render(config,station_seed+position,seconds,position,arrangement=a)
                else:path,metrics=render_notes(config,notes,seconds,position,arrangement=a)
                actual=digest(data/'midi'/f'{position}.mid')
                if actual!=expected:raise ValueError('Rendered score differs from its audition score')
                variant['segments'].append({'position':position,'seed':station_seed+position,
                                            'midi_sha256':actual,'added_notes':len(notes)-len(base),
                                            'shortened_tails':shortened if label=='connections' else 0,
                                            'render_seconds':time.monotonic()-started,'analysis':metrics})
                paths.append(path);write_report(output,report)
            if digest(font)!=metadata['sha256']:raise ValueError('SoundFont changed during the audition')
            stitch(paths,data/'work/sequence.wav');variant['input_loudness']=measure(data/'work/sequence.wav')
        target=shared_level([v['input_loudness'] for v in report['variants'].values()]);report['target_lufs']=target
        for label,variant in report['variants'].items():
            data=output/label;gain=target-variant['input_loudness']['integrated_lufs'];variant['gain_db']=gain
            master=data/'listen.wav'
            command(['ffmpeg','-nostdin','-v','error','-y','-i',str(data/'work/sequence.wav'),'-af',f'volume={gain:.8f}dB','-ar','44100','-ac','2','-c:a','pcm_s16le',str(master)])
            variant['final_analysis']=analyze(master);variant['final_loudness']=measure(master)
            if abs(variant['final_analysis']['duration']-report['sequence_seconds'])>.1:
                raise ValueError('Unexpected comparison duration')
            command(['ffmpeg','-nostdin','-v','error','-y','-i',str(master),'-c:a','libmp3lame','-b:a','128k',str(data/'listen.mp3')])
            (data/'work/sequence.wav').unlink()
        check_levels([v['final_loudness'] for v in report['variants'].values()],target)
        if any(v['gain_db']>0 for v in report['variants'].values()):raise ValueError('Positive gain is not allowed')
        if digest(font)!=metadata['sha256']:raise ValueError('SoundFont changed before completion')
        (output/'index.html').write_text(report_html(report));report['status']='complete';write_report(output,report)
        return report
    except Exception as error:
        report['status']='failed';report['error']=f'{type(error).__name__}: {error}';write_report(output,report);raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--soundfont',type=Path,default=Path('/usr/share/sounds/sf2/TimGM6mb.sf2'))
    parser.add_argument('--station-seed',type=int,default=42)
    parser.add_argument('--positions',type=int,nargs='+',default=[1,2,3])
    parser.add_argument('--seconds',type=int,default=120);parser.add_argument('--bpm',type=int,default=60)
    args=parser.parse_args()
    try:report=audition_melody(args.output,args.soundfont,args.station_seed,args.positions,args.seconds,args.bpm)
    except (ValueError,OSError,RuntimeError,subprocess.TimeoutExpired) as error:parser.exit(1,f'Melody audition failed: {error}\n')
    print(json.dumps({'output':str(args.output.absolute()),'status':report['status'],'sequence_seconds':report['sequence_seconds'],'added_notes':report['added_notes'],'target_lufs':report['target_lufs']},indent=2))


if __name__=='__main__':main()
