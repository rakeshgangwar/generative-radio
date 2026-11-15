import hashlib
import json
import math
from collections import Counter
from dataclasses import replace
from pathlib import Path
import unittest

from radio.arrangement import arrangement_for
from radio.compose import Note,compose,midi
from radio.melodic_connections import connect_melody


def fixture(seconds=20,left=64,right=67):
    pads=[Note(0,seconds-1,p,35,0) for p in (55,60,64,71)]
    return pads+[Note(0,seconds-1,36,32,1),Note(5,.5,left,40,2),Note(9.5,1,right,40,2)]


def plan(profile=2):
    return replace(arrangement_for(42,2),profile=profile,phrase_bars=6)


class MelodicConnectionsTests(unittest.TestCase):
    def test_clear_gap_inserts_quiet_step_and_preserves_every_anchor(self):
        for left,right in [(64,67),(67,64)]:
            original=fixture(left=left,right=right);before=list(original)
            result=connect_melody(original,20,60,plan())
            self.assertEqual(original,before)
            self.assertEqual(result[:len(original)],original)
            self.assertEqual(result[len(original):],[Note(8.75,.5,65,35,2)])

    def test_no_additions_for_repeat_small_step_large_leap_or_no_gap(self):
        for left,right in [(64,64),(64,65),(60,67)]:
            notes=fixture(left=left,right=right)
            self.assertEqual(connect_melody(notes,20,60,plan()),notes)
        notes=fixture();notes[-2]=replace(notes[-2],start=8,duration=1.4)
        self.assertEqual(connect_melody(notes,20,60,plan()),notes)

    def test_sparse_profile_quiet_edges_and_phrase_cap(self):
        notes=fixture()
        self.assertEqual(connect_melody(notes,20,60,plan(0)),notes)
        notes=fixture(80)[:-2]+[Note(at,.5,pitch,40,2) for at,pitch in [(14,64),(17.5,67),(26,64),(29.5,67),(50,64),(53.5,67)]]
        self.assertEqual(len(connect_melody(notes,80,60,plan(2)))-len(notes),3)
        self.assertEqual(len(connect_melody(notes,80,60,plan(1)))-len(notes),2)
        notes=fixture();notes[-2]=replace(notes[-2],start=1);notes[-1]=replace(notes[-1],start=3.5)
        self.assertEqual(connect_melody(notes,20,60,plan()),notes)

    def test_whole_bar_rest_and_harmony_change_are_preserved(self):
        notes=fixture(40);notes[-2]=replace(notes[-2],start=19,duration=.25);notes[-1]=replace(notes[-1],start=24.5)
        self.assertEqual(connect_melody(notes,40,60,plan()),notes)
        notes=[Note(0,8,p,35,0) for p in (55,60,64,71)]+[Note(8,11,p,35,0) for p in (53,57,60,64)]+[Note(5,.5,60,40,2),Note(8.5,1,64,40,2)]
        self.assertEqual(connect_melody(notes,20,60,plan()),notes)
        notes=fixture();notes=[n for n in notes if not (n.channel==0 and n.pitch in (55,71))]
        self.assertEqual(connect_melody(notes,20,60,plan()),notes)

    def test_invalid_bounded_inputs_fail_without_mutation(self):
        notes=fixture()
        for seconds in (19,1801,True,float('nan'),float('inf')):
            with self.subTest(seconds=seconds),self.assertRaises(ValueError):connect_melody(notes,seconds,60,plan())
        for bpm in (39,91,True,60.0):
            with self.subTest(bpm=bpm),self.assertRaises(ValueError):connect_melody(notes,20,bpm,plan())
        for bad in (replace(plan(),version=1),replace(plan(),phrase_bars=5),replace(plan(),profile=3),None):
            with self.assertRaises(ValueError):connect_melody(notes,20,60,bad)
        for bad in (replace(notes[-1],start=-1),replace(notes[-1],duration=0),replace(notes[-1],pitch=128),replace(notes[-1],velocity=0),replace(notes[-1],channel=3),replace(notes[-1],start=float('nan'))):
            with self.assertRaises(ValueError):connect_melody([bad],20,60,plan())
        with self.assertRaises(ValueError):connect_melody([notes[0]]*4097,20,60,plan())
        with self.assertRaises(ValueError):connect_melody(iter(notes),20,60,plan())
        self.assertEqual(connect_melody([],20,60,plan()),[])

    def test_bounded_tail_trim_makes_room_without_moving_anchors(self):
        original=fixture();original[-2]=replace(original[-2],duration=4)
        before=list(original);result=connect_melody(original,20,60,plan())
        self.assertEqual(original,before)
        self.assertEqual(len(result),len(original)+1)
        self.assertAlmostEqual(result[-3].duration,3.65)
        self.assertEqual(result[-1],Note(8.75,.5,65,35,2))
        self.assertEqual((result[-3].start,result[-3].pitch,result[-3].velocity),(5,64,40))
        self.assertEqual(result[-2],original[-1])

    def test_existing_default_and_explicit_legacy_midi_hashes_are_unchanged(self):
        data=json.loads((Path(__file__).parent/'fixtures/melody-baseline-midi.json').read_text())
        self.assertEqual(len(data['cases']),24)
        for case in data['cases']:
            a=arrangement_for(case['station_seed'],case['position']) if case['version'] else None
            if case['version']==1:a=replace(a,version=1,phrase_bars=0)
            content=midi(compose(case['station_seed']+case['position'],case['seconds'],case['bpm'],a),case['seconds'],case['bpm'],programs=a.programs if a else None)
            self.assertEqual(hashlib.sha256(content).hexdigest(),case['sha256'],case)

    def test_bounded_real_score_matrix_is_deterministic_and_preserves_breaths(self):
        total=0
        for seed in (42,20261114):
            for position in range(1,65):
                for seconds,bpm in ((20,40),(120,90)):
                    a=arrangement_for(seed,position);original=compose(seed+position,seconds,bpm,a)
                    result=connect_melody(original,seconds,bpm,a)
                    self.assertEqual(result,connect_melody(original,seconds,bpm,a))
                    for before,after in zip(original,result[:len(original)]):
                        self.assertEqual((after.start,after.pitch,after.velocity,after.channel),(before.start,before.pitch,before.velocity,before.channel))
                        self.assertLessEqual(after.duration,before.duration)
                        if before.duration!=after.duration:
                            self.assertEqual(after.channel,2)
                            self.assertGreaterEqual(after.duration,max(.5*60/bpm,before.duration*.5)-1e-8)
                    extra=result[len(original):];total+=len(extra)
                    self.assertFalse(extra if a.profile==0 else False)
                    groups=Counter()
                    for note in extra:
                        beat=60/bpm;bar_index=int(note.start/(4*beat));group=bar_index//a.phrase_bars
                        self.assertNotEqual(bar_index%a.phrase_bars,a.phrase_bars-1)
                        self.assertIn(note.pitch%12,{0,2,4,5,7,9,11});self.assertEqual(note.channel,2)
                        self.assertGreaterEqual(note.start,seconds*.2-1e-8)
                        if a.profile==1:self.assertEqual(group%2,0)
                        groups[group]+=1
                    self.assertTrue(all(count<=1 for count in groups.values()))
                    melody=sorted((n for n in result if n.channel==2),key=lambda n:n.start)
                    self.assertTrue(all(n.duration>0 and n.start+n.duration<=seconds for n in result))
                    self.assertTrue(all(left.start+left.duration<=right.start+1e-8 for left,right in zip(melody,melody[1:])))
        self.assertGreater(total,0,'Experiment must create real connections, not only pass invariants')


if __name__=='__main__':unittest.main()
