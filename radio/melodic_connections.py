"""Audition-only stepwise connections; preserve score anchors and phrase rests."""
import math
from dataclasses import replace

from .arrangement import Arrangement
from .compose import Note


def connect_melody(notes, seconds, bpm, arrangement) -> list[Note]:
    if (type(seconds) not in (int, float) or not math.isfinite(seconds)
            or not 20 <= seconds <= 1800 or type(bpm) is not int or not 40 <= bpm <= 90
            or not isinstance(arrangement, Arrangement)
            or type(arrangement.version) is not int or arrangement.version != 2
            or type(arrangement.phrase_bars) is not int or arrangement.phrase_bars not in (6, 8, 10)
            or type(arrangement.profile) is not int or arrangement.profile not in (0, 1, 2)
            or not isinstance(notes,(list, tuple)) or len(notes) > 4096):
        raise ValueError('Expected a bounded version2 score for the offline experiment')
    original = list(notes)
    for note in original:
        if (not isinstance(note, Note)
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in (note.start,note.duration))
                or note.start < 0 or note.duration <= 0 or note.start + note.duration > seconds
                or type(note.pitch) is not int or not 0 <= note.pitch <= 127
                or type(note.velocity) is not int or not 1 <= note.velocity <= 127
                or type(note.channel) is not int or not 0 <= note.channel <= 2):
            raise ValueError('Invalid score note')
    if arrangement.profile == 0:
        return original
    melody = sorted(((index, note) for index, note in enumerate(original) if note.channel == 2),
                    key=lambda item: item[1].start)
    pads=[n for n in original if n.channel==0]
    def field(at):
        return {n.pitch%12 for n in pads if n.start<=at<n.start+n.duration}
    beat = 60 / bpm
    bar = 4 * beat
    phrase_bars = arrangement.phrase_bars
    added = []
    used = set()
    for (previous_index, previous), (_, target) in zip(melody, melody[1:]):
        if abs(target.pitch-previous.pitch) not in (3, 4):
            continue
        pitches=[p for p in range(min(previous.pitch,target.pitch)+1,max(previous.pitch,target.pitch)) if p%12 in {0,2,4,5,7,9,11}]
        if len(pitches)!=1 or max(abs(pitches[0]-previous.pitch),abs(pitches[0]-target.pitch))>2:
            continue
        at = target.start - .75 * beat
        duration = .5 * beat
        shortened = min(previous.duration, at - .1 * beat - previous.start)
        if ((shortened < previous.duration and shortened < max(.5 * beat, previous.duration * .5) - 1e-9)
                or shortened <= 0
                or at+duration>target.start-.1*beat+1e-9
                or at<seconds*.2 or target.start>seconds*.8
                or not .2<=(at/beat)%1<=.8):
            continue
        first_bar = int(at // bar)
        last_bar = int((at + duration - 1e-9) // bar)
        target_bar = int(target.start // bar)
        group=target_bar//phrase_bars
        if (int(previous.start // bar) // phrase_bars != group
                or first_bar//phrase_bars!=group or group in used
                or any(index%phrase_bars==phrase_bars-1 for index in (first_bar,last_bar,target_bar))
                or (arrangement.profile==1 and group%2)):
            continue
        active=field(at)
        if len(active)<3 or active!=field(target.start) or not {previous.pitch%12,target.pitch%12}<=active:
            continue
        if shortened < previous.duration:
            original[previous_index] = replace(previous, duration=shortened)
        added.append(Note(at,duration,pitches[0],max(1,target.velocity-5),2))
        used.add(group)
    return original+added
