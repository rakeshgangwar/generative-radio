"""Offline current/resting profile comparison; never changes the station."""
import argparse
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess
import time
import json

from .arrangement import arrangement_for
from .compose import compose, midi
from .config import Config
from .render import render_notes, analyze
from .audition import (validate_inputs, digest, digest_bytes, engine_versions,
                       write_report, stitch, measure, shared_level, check_levels,
                       command, report_html)


def score_for(profile, station_seed, position, seconds):
    if (profile not in ('current', 'resting') or type(station_seed) is not int
            or type(position) is not int or position < 1 or type(seconds) is not int
            or not 20 <= seconds <= 1800):
        raise ValueError('Use a declared profile, integer seed, positive position and 20–1800 seconds.')
    arrangement = arrangement_for(station_seed, position)
    bpm = 60
    if profile == 'resting':
        bpm = 52
        arrangement = replace(arrangement, profile=0, programs=(89, 32, 4))
    return arrangement, compose(station_seed + position, seconds, bpm, arrangement), bpm


def audition_profile(output, soundfont, station_seed=42,
                     positions=tuple(range(1, 13)), seconds=120):
    fonts = validate_inputs({'current': soundfont, 'resting': soundfont},
                            positions, seconds, 60, station_seed)
    if fonts['current'] != fonts['resting']:
        raise ValueError('SoundFont changed during validation')
    font = fonts['current']
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    parent = output.parent.resolve(strict=True)
    if any((p / 'radio.sqlite').exists() or (p / 'radio.sqlite').is_symlink()
           for p in (parent, *parent.parents)):
        raise ValueError('Choose an audition output outside station data')
    metadata = {'path': str(font), 'size_bytes': font.stat().st_size, 'sha256': digest(font)}
    output.mkdir(mode=0o700)
    report = {'version': 1, 'status': 'running',
              'created_at': datetime.now(timezone.utc).isoformat(),
              'experiment': {'name': 'resting-profile', 'version': 1, 'scope': 'offline-only'},
              'font': metadata, 'station_seed': station_seed, 'positions': list(positions),
              'segment_seconds': seconds,
              'sequence_seconds': len(positions) * seconds - (len(positions) - 1) * 5,
              'variants': {}}
    write_report(output, report)
    try:
        report['engines'] = engine_versions()
        report['source_sha256'] = {name: digest(Path(__file__).with_name(name)) for name in
                                  ('profile_audition.py', 'compose.py', 'arrangement.py',
                                   'render.py', 'config.py', 'audition.py')}
        for label in ('current', 'resting'):
            data = output / label
            data.mkdir()
            bpm = 60 if label == 'current' else 52
            config = Config.from_env({'RADIO_DATA': str(data), 'BPM': str(bpm),
                                      'SOUNDFONT': str(font)})
            variant = {'bpm': bpm, 'font_sha256': metadata['sha256'], 'segments': []}
            report['variants'][label] = variant
            paths = []
            for position in positions:
                arrangement, notes, tempo = score_for(label, station_seed, position, seconds)
                if tempo != config.bpm:
                    raise ValueError('Score and renderer tempo differ')
                expected = digest_bytes(midi(notes, seconds, tempo, programs=arrangement.programs))
                started = time.monotonic()
                path, metrics = render_notes(config, notes, seconds, position, arrangement=arrangement)
                actual = digest(data / 'midi' / f'{position}.mid')
                if actual != expected:
                    raise ValueError('Rendered MIDI differs from the intended profile score')
                variant['segments'].append({'position': position, 'seed': station_seed + position,
                                            'profile': arrangement.profile,
                                            'programs': list(arrangement.programs),
                                            'lead_attacks': sum(n.channel == 2 for n in notes),
                                            'midi_sha256': actual,
                                            'render_seconds': time.monotonic() - started,
                                            'analysis': metrics})
                paths.append(path)
                write_report(output, report)
            if digest(font) != metadata['sha256']:
                raise ValueError('SoundFont changed during the comparison')
            stitch(paths, data / 'work' / 'sequence.wav')
            variant['input_loudness'] = measure(data / 'work' / 'sequence.wav')
            write_report(output, report)
        target = shared_level([v['input_loudness'] for v in report['variants'].values()])
        report['target_lufs'] = target
        for label, variant in report['variants'].items():
            data = output / label
            gain = target - variant['input_loudness']['integrated_lufs']
            if gain > 0:
                raise ValueError('Comparison matching must not add gain')
            variant['gain_db'] = gain
            master = data / 'listen.wav'
            command(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(data / 'work' / 'sequence.wav'),
                     '-af', f'volume={gain:.8f}dB', '-ar', '44100', '-ac', '2',
                     '-c:a', 'pcm_s16le', str(master)])
            variant['final_analysis'] = analyze(master)
            variant['final_loudness'] = measure(master)
            if abs(variant['final_analysis']['duration'] - report['sequence_seconds']) > .1:
                raise ValueError('Unexpected comparison duration')
            silence = command(['ffmpeg', '-nostdin', '-hide_banner', '-nostats', '-i', str(master),
                               '-af', 'silencedetect=noise=-50dB:d=2', '-f', 'null', '-'])
            log = data / 'silence-analysis.log'
            log.write_text(silence.stderr)
            if re.search(r'^\[(?:Parsed_)?silencedetect(?:_\d+)? @ [^\]\r\n]+\]\s+silence_start:',
                         silence.stderr, re.MULTILINE):
                raise ValueError('Comparison contains silence at -50dB lasting two seconds')
            variant['no_silence_at_minus50dbfs_for_two_seconds'] = True
            variant['silence_analysis_sha256'] = digest(log)
            variant['wav_sha256'] = digest(master)
            command(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(master),
                     '-c:a', 'libmp3lame', '-b:a', '128k', str(data / 'listen.mp3')])
            variant['mp3_sha256'] = digest(data / 'listen.mp3')
            (data / 'work' / 'sequence.wav').unlink()
            write_report(output, report)
        check_levels([v['final_loudness'] for v in report['variants'].values()], target)
        if digest(font) != metadata['sha256']:
            raise ValueError('SoundFont changed before completion')
        description = ('The same chapters and SoundFont, with current and resting profiles. '
                       'Different pulse changes note and chord timing: compare overall feel, not identical notes. '
                       'This is an offline candidate; the station is unchanged. Pause other audio first. '
                       'When scripts are disabled, pause the other player manually.')
        page = report_html(report, description=description)
        (output / 'index.html').write_text(page)
        report['status'] = 'complete'
        write_report(output, report)
        return report
    except BaseException as error:
        report['status'] = 'cancelled' if isinstance(error, KeyboardInterrupt) else 'failed'
        report['error'] = f'{type(error).__name__}: {error}'[:1600]
        (output / 'index.html').unlink(missing_ok=True)
        write_report(output, report)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--soundfont', type=Path, default=Path('/usr/share/sounds/sf2/TimGM6mb.sf2'))
    parser.add_argument('--station-seed', type=int, default=42)
    parser.add_argument('--positions', type=int, nargs='+', default=list(range(1, 13)))
    parser.add_argument('--seconds', type=int, default=120)
    args = parser.parse_args()
    try:
        report = audition_profile(args.output, args.soundfont, args.station_seed, args.positions, args.seconds)
    except (ValueError, OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f'Profile audition failed: {error}\n')
    print(json.dumps({'output': str(args.output.absolute()), 'status': report['status'],
                      'sequence_seconds': report['sequence_seconds'],
                      'target_lufs': report['target_lufs']}, indent=2))


if __name__ == '__main__':
    main()
