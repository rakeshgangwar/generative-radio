import hashlib
import random
import unittest
from collections import Counter, defaultdict

from radio.arrangement import arrangement_for, PROGRESSIONS
from radio.compose import compose, midi


class ArrangementTests(unittest.TestCase):
    def test_plans_are_deterministic_and_independent_of_call_order_or_age(self):
        positions=[1,2,6,11,57,10**12]
        state=random.getstate()
        expected={n:arrangement_for(42,n) for n in positions}
        for n in reversed(positions):
            self.assertEqual(arrangement_for(42,n),expected[n])
        self.assertEqual(random.getstate(),state)
        self.assertNotEqual([arrangement_for(43,n) for n in positions],list(expected.values()))

    def test_invalid_identity_is_rejected(self):
        for seed,position in [(42,0),(42,-1),(42,1.5),(42,True),(True,1),('42',1)]:
            with self.subTest(seed=seed,position=position), self.assertRaises(ValueError):
                arrangement_for(seed,position)

    def test_harmonic_paths_are_balanced_and_never_repeat_at_adjacent_positions(self):
        for seed in [0,42,20261114,-7]:
            paths=[arrangement_for(seed,n).progression for n in range(1,501)]
            self.assertTrue(all(a!=b for a,b in zip(paths,paths[1:])))
            for start in range(0,500,5):
                self.assertEqual(set(paths[start:start+5]),set(PROGRESSIONS))
            old=[arrangement_for(seed,10**12+n).progression for n in range(20)]
            self.assertTrue(all(a!=b for a,b in zip(old,old[1:])))

    def test_chapters_vary_length_share_a_theme_and_have_a_quiet_arc(self):
        groups=defaultdict(list)
        for n in range(1,241):
            plan=arrangement_for(42,n)
            self.assertEqual(plan.position,n)
            self.assertEqual(plan.version,2)
            groups[plan.chapter].append(plan)
        self.assertEqual({len(group) for group in groups.values()},{3,4,5})
        self.assertEqual(list(groups),list(range(1,len(groups)+1)))
        palettes=[]
        for chapter,group in groups.items():
            self.assertEqual([p.chapter_segment for p in group],list(range(1,len(group)+1)))
            self.assertTrue(all(p.chapter_segments==len(group) for p in group))
            for attribute in ['motif','register','programs','rhythm_order']:
                self.assertEqual(len({getattr(p,attribute) for p in group}),1,attribute)
            self.assertEqual(group[0].stage,'arrival')
            self.assertEqual(group[-1].stage,'release')
            self.assertEqual(group[0].profile,0)
            self.assertEqual(group[-1].profile,0)
            self.assertIn(2,[p.profile for p in group[1:-1]])
            palettes.append(group[0].programs)
        self.assertTrue(all(a!=b for a,b in zip(palettes,palettes[1:])))
        self.assertEqual(set(palettes),{(89,32,4),(94,32,4),(89,32,11)})

    def test_legacy_midi_remains_bit_identical(self):
        score=midi(compose(42,120,60),120,60)
        self.assertEqual(hashlib.sha256(score).hexdigest(),
                         'b67795342a7544bdb82cdb645c3bcc35b3ea97da98e195e64ea9f3f48a7eb0bc')

    def test_planned_notes_remain_safe_and_deterministic_across_bounds(self):
        for position in range(1,25):
            for seconds,bpm in [(20,40),(20,90),(120,60),(600,40),(600,90)]:
                with self.subTest(position=position,seconds=seconds,bpm=bpm):
                    plan=arrangement_for(42,position)
                    notes=compose(42+position,seconds,bpm,arrangement=plan)
                    self.assertTrue(notes)
                    self.assertEqual(notes,compose(42+position,seconds,bpm,arrangement=plan))
                    for note in notes:
                        self.assertTrue(0<=note.start<seconds)
                        self.assertTrue(0<note.duration<=seconds-note.start+.00001)
                        self.assertTrue(36<=note.pitch<=84)
                        self.assertIn(note.pitch%12,{0,2,4,5,7,9,11})
                        self.assertTrue(0<note.velocity<=60)
                    for channel in [0,1,2]:
                        ends={}
                        for note in sorted((n for n in notes if n.channel==channel),key=lambda n:n.start):
                            self.assertGreaterEqual(note.start+.00001,ends.get(note.pitch,0))
                            ends[note.pitch]=note.start+note.duration
                    melody=sorted((n for n in notes if n.channel==2),key=lambda n:n.start)
                    self.assertTrue(all(abs(a.pitch-b.pitch)<=7 for a,b in zip(melody,melody[1:])))

    def test_first_melody_pitches_broaden_without_raising_note_density(self):
        starts=[];counts=[]
        for n in range(1,257):
            notes=compose(20261114+n,120,60,arrangement=arrangement_for(20261114,n))
            melody=sorted((x for x in notes if x.channel==2),key=lambda n:n.start)
            starts.append(melody[0].pitch);counts.append(len(melody))
        self.assertGreaterEqual(len(set(starts)),5)
        self.assertLess(Counter(starts)[69]/len(starts),.6)
        self.assertLessEqual(max(counts),60)
        self.assertLess(min(counts),36)  # actually leave space compared with baseline

    def test_midi_uses_the_planned_three_programs(self):
        for position in range(1,49):
            plan=arrangement_for(42,position)
            blob=midi([],20,60,programs=plan.programs)
            # SMF track begins after22bytes; tempo is7, each channel setup11.
            for channel,program in enumerate(plan.programs):
                offset=29+channel*11
                self.assertEqual(blob[offset:offset+3],bytes([0,0xC0|channel,program]))

    def test_bloom_has_more_melodic_attacks_than_arrival_and_release(self):
        groups=defaultdict(list)
        for position in range(1,49):
            plan=arrangement_for(42,position)
            count=sum(n.channel==2 for n in compose(42+position,120,60,arrangement=plan))
            groups[plan.chapter].append((plan,count))
        for group in groups.values():
            bloom=max(count for plan,count in group if plan.stage=='bloom')
            self.assertGreater(bloom,group[0][1])
            self.assertGreater(bloom,group[-1][1])

    def test_invalid_program_palettes_cannot_write_malformed_midi(self):
        for programs in [(89,32),(89,32,128),(89,32,-1),(89,32,True)]:
            with self.subTest(programs=programs),self.assertRaises(ValueError):
                midi([],20,60,programs=programs)


if __name__=='__main__':
    unittest.main()
