"""Offline, identical-score SoundFont comparisons. Never opens the station database."""
import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import time
from urllib.parse import quote

from .arrangement import arrangement_for
from .compose import compose, midi
from .config import Config
from .render import render, analyze


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate_inputs(fonts, positions, seconds, bpm, station_seed):
    if not isinstance(fonts, dict) or not 2 <= len(fonts) <= 4:
        raise ValueError('Supply two to four labeled local SoundFonts.')
    if (type(seconds) is not int or not 20 <= seconds <= 1800
            or type(bpm) is not int or not 40 <= bpm <= 90 or type(station_seed) is not int
            or not isinstance(positions, (list, tuple)) or not 1 <= len(positions) <= 24
            or any(type(p) is not int or p < 1 for p in positions)
            or len(set(positions)) != len(positions) or seconds * len(positions) > 1800):
        raise ValueError('Use unique positive positions, 20–1800 seconds, at most 30 nominal minutes per font and 40–90 BPM.')
    normalized = {}
    for label, source in fonts.items():
        if not isinstance(label, str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,31}', label):
            raise ValueError('Font labels must be short lowercase ASCII identifiers.')
        path = Path(source).resolve(strict=True)
        if not path.is_file() or path.suffix.lower() not in {'.sf2', '.sf3'}:
            raise ValueError('SoundFonts must be readable regular local sf2/sf3 files.')
        with path.open('rb') as stream:
            stream.read(1)
        normalized[label] = path
    return normalized


def shared_level(measurements):
    if not measurements:
        raise ValueError('No loudness measurements.')
    target = -22.0
    for measured in measurements:
        try:
            integrated, peak = (float(measured[key]) for key in ['integrated_lufs', 'true_peak_dbfs'])
        except (KeyError, ValueError, TypeError):
            raise ValueError('Invalid loudness measurement.') from None
        if not math.isfinite(integrated) or not math.isfinite(peak):
            raise ValueError('Nonfinite loudness measurement.')
        target = min(target, integrated, integrated - max(0, peak + 3))
    return target


def check_levels(measurements, target):
    shared_level(measurements)
    levels = [float(item['integrated_lufs']) for item in measurements]
    if (not math.isfinite(target) or max(levels) - min(levels) > .200001
            or any(abs(level - target) > .200001 for level in levels)
            or any(float(item['true_peak_dbfs']) > -2.9 for item in measurements)):
        raise ValueError('Final variants do not share a safe matched listening level.')


def command(arguments, timeout=180):
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'{arguments[0]} failed: {result.stderr[-1500:]}')
    return result


def engine_versions():
    return {name: command([name, flag], timeout=10).stdout[:1000]
            for name, flag in [('fluidsynth', '--version'), ('ffmpeg', '-version')]}


def measure(path):
    result = command(['ffmpeg', '-nostdin', '-hide_banner', '-nostats', '-i', str(path),
                      '-af', 'loudnorm=I=-22:TP=-3:LRA=9:print_format=json', '-f', 'null', '-'])
    try:
        data, _ = json.JSONDecoder().raw_decode(result.stderr[result.stderr.rindex('{'):])
        measured = {'integrated_lufs': float(data['input_i']), 'true_peak_dbfs': float(data['input_tp'])}
    except (ValueError, KeyError, TypeError):
        raise ValueError('FFmpeg did not provide valid loudness measurements.') from None
    shared_level([measured])  # Reject missing/nonfinite measurements before any level decision.
    return measured


def stitch(paths, output):
    if len(paths) == 1:
        shutil.copyfile(paths[0], output)
        return
    args = ['ffmpeg', '-nostdin', '-v', 'error', '-y']
    for path in paths:
        args += ['-i', str(path)]
    filters, previous = [], '[0:a]'
    for i in range(1, len(paths)):
        filters.append(f'{previous}[{i}:a]acrossfade=d=5:c1=tri:c2=tri[a{i}]')
        previous = f'[a{i}]'
    command(args + ['-filter_complex', ';'.join(filters), '-map', previous,
                    '-ar', '44100', '-ac', '2', '-c:a', 'pcm_s16le', str(output)])


def report_html(report, *, description=None):
    intro = ('The same musical score, different sound libraries.' if description is None
             else html.escape(description))
    sections = []
    for label, variant in report['variants'].items():
        name = html.escape(label, quote=True)
        source = quote(label, safe='') + '/listen.mp3'
        sections.append(f'<section><h2>{name}</h2><audio controls preload="none" aria-label="Listen to {name}" src="{source}"></audio>'
                        f'<p>{variant["final_loudness"]["integrated_lufs"]:.2f} LUFS; '
                        f'{variant["gain_db"]:.2f} dB level adjustment.</p>'
                        f'<a href="{quote(label, safe="")}/listen.wav">Download measured WAV</a></section>')
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>Sound comparison — Generative Radio</title><style>body{font:18px/1.6 system-ui;max-width:800px;margin:3rem auto;padding:0 1rem;color:#17344b;background:#d8e3ed}section{border-top:1px solid #4a6275;padding:1rem 0}audio{max-width:100%}a{color:inherit}</style>'
            '<h1>A closer listen</h1><p>' + intro + ' '
            'Play one version at a time and compare the same moment. Levels are matched with attenuation only; '
            'metrics cannot decide which feels better.</p>'
            f'<p>Duration: {report["sequence_seconds"]:.1f} seconds. Shared level: {report["target_lufs"]:.2f} LUFS. '
            'The MP3 is a convenient copy; the WAV is the measured master.</p>' + ''.join(sections) +
            '<p><a href="report.json">Measurements, source fingerprints and engine versions</a></p>'
            '<script>const tracks=[...document.querySelectorAll("audio")];for(const track of tracks)track.addEventListener("play",()=>{for(const other of tracks)if(other!==track)other.pause();});</script></html>')


def write_report(output, report):
    temporary = output / '.report.json.tmp'
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    temporary.replace(output / 'report.json')


def audition(output, fonts, station_seed=42, positions=(1, 2, 3), seconds=120, bpm=60):
    fonts = validate_inputs(fonts, positions, seconds, bpm, station_seed)
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    parent = output.parent.resolve(strict=True)
    if any((directory / 'radio.sqlite').exists() for directory in [parent, *parent.parents]):
        raise ValueError('Choose a comparison output outside station data.')
    metadata = {name: {'path': str(path), 'size_bytes': path.stat().st_size, 'sha256': digest(path)}
                for name, path in fonts.items()}
    output.mkdir()  # Exclusive, including existing directories and broken symlinks.
    report = {'version': 1, 'status': 'running', 'created_at': datetime.now(timezone.utc).isoformat(),
              'station_seed': station_seed, 'positions': list(positions), 'segment_seconds': seconds, 'bpm': bpm,
              'sequence_seconds': len(positions) * seconds - (len(positions) - 1) * 5, 'variants': {}}
    write_report(output, report)
    try:
        report['engines'] = engine_versions()
        report['source_sha256'] = {name: digest(Path(__file__).with_name(name))
                                   for name in ['audition.py', 'compose.py', 'arrangement.py', 'render.py']}
        expected = {}
        for position in positions:
            arrangement = arrangement_for(station_seed, position)
            expected[position] = digest_bytes(midi(compose(station_seed + position, seconds, bpm, arrangement),
                                                   seconds, bpm, programs=arrangement.programs))
        for label, font in fonts.items():
            data = output / label
            data.mkdir()
            config = Config.from_env({'RADIO_DATA': str(data), 'BPM': str(bpm), 'SOUNDFONT': str(font)})
            variant = {'font': metadata[label], 'segments': []}
            report['variants'][label] = variant
            paths = []
            for position in positions:
                started = time.monotonic()
                path, metrics = render(config, station_seed + position, seconds, position,
                                       arrangement=arrangement_for(station_seed, position))
                score_hash = digest(data / 'midi' / f'{position}.mid')
                if score_hash != expected[position]:
                    raise ValueError('A rendered score differs from the comparison score.')
                variant['segments'].append({'position': position, 'seed': station_seed + position,
                                            'midi_sha256': score_hash, 'render_seconds': time.monotonic() - started,
                                            'analysis': metrics})
                paths.append(path)
                write_report(output, report)
            if digest(font) != metadata[label]['sha256']:
                raise ValueError('A SoundFont changed during the comparison.')
            unmatched = data / 'work' / 'sequence.wav'
            stitch(paths, unmatched)
            variant['input_loudness'] = measure(unmatched)
        target = shared_level([v['input_loudness'] for v in report['variants'].values()])
        report['target_lufs'] = target
        for label, variant in report['variants'].items():
            data = output / label
            gain = target - variant['input_loudness']['integrated_lufs']
            variant['gain_db'] = gain
            master = data / 'listen.wav'
            command(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(data / 'work' / 'sequence.wav'),
                     '-af', f'volume={gain:.8f}dB', '-ar', '44100', '-ac', '2', '-c:a', 'pcm_s16le', str(master)])
            variant['final_analysis'] = analyze(master)
            variant['final_loudness'] = measure(master)
            if (abs(variant['final_analysis']['duration'] - report['sequence_seconds']) > .1
                    or abs(variant['final_loudness']['integrated_lufs'] - target) > .2
                    or variant['final_loudness']['true_peak_dbfs'] > -2.9 or gain > 0):
                raise ValueError('Final comparison failed duration, level matching or peak checks.')
            command(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(master),
                     '-c:a', 'libmp3lame', '-b:a', '128k', str(data / 'listen.mp3')])
            (data / 'work' / 'sequence.wav').unlink()
        check_levels([v['final_loudness'] for v in report['variants'].values()], target)
        (output / 'index.html').write_text(report_html(report))
        report['status'] = 'complete'
        write_report(output, report)
        return report
    except Exception as error:
        report['status'] = 'failed'
        report['error'] = f'{type(error).__name__}: {error}'
        write_report(output, report)
        raise


def digest_bytes(content):
    return hashlib.sha256(content).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--font', action='append', required=True, metavar='LABEL=PATH')
    parser.add_argument('--station-seed', type=int, default=42)
    parser.add_argument('--positions', type=int, nargs='+', default=[1, 2, 3])
    parser.add_argument('--seconds', type=int, default=120)
    parser.add_argument('--bpm', type=int, default=60)
    args = parser.parse_args()
    fonts = {}
    for value in args.font:
        label, separator, path = value.partition('=')
        if not separator or label in fonts:
            parser.error('Supply distinct LABEL=PATH font entries.')
        fonts[label] = Path(path)
    try:
        report = audition(args.output, fonts, args.station_seed, args.positions, args.seconds, args.bpm)
    except (ValueError, OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f'Audition failed: {error}\n')
    print(json.dumps({'output': str(args.output.absolute()), 'status': report['status'],
                      'target_lufs': report['target_lufs'], 'sequence_seconds': report['sequence_seconds']}, indent=2))


if __name__ == '__main__':
    main()
