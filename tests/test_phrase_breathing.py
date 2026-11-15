import hashlib
import json
import math
import unittest
from collections import defaultdict
from dataclasses import asdict
from types import SimpleNamespace

from radio.arrangement import arrangement_for
from radio.compose import compose, midi


FIXTURES = {'1': {'midi': '7c25a36b9399cc1cfdfde81c88919b15929a52c14920a4eda4e94e99f8d67bba',
       'plan': '743d913b22cbe5976c28a1a7947dcb968c3aa8ebcae9d8c63a774dcd3d9f88dc'},
 '2': {'midi': '5193d60c03a941c316f9f5c3e45da91b50d4d58d5995d6b020111616a7fa7955',
       'plan': '1f8526cac40c7422470e3920e3d908163d6282de5ad829effd4c15d666e32ea2'},
 '3': {'midi': 'b3e0c88546459e5ab5391ddde123ab77a6177365137d7979fab2d6a1ac0e0bb7',
       'plan': '02265369a303673b9e2dbb2b6b481215572b85b7911f64e9379257e825be2d2f'},
 '4': {'midi': '602ed09a888924566ce60655bb64c0a6645f1823f8335d4c2be96ccf4eba6012',
       'plan': 'a043de4cbf6f20ca25ec622acbb2e679bcdb82b7e935fe595ec929c08bda46ff'},
 '5': {'midi': '95bdeed70b7b2bb0372891fb61a97973f38b1355c392190c02ee92fad2465c53',
       'plan': '9253a167ea8ec20133b8362bd3b4f3d7846c0d55539294a5a08d278042adf4d2'},
 '9': {'midi': '8548d0ad38675c40f35feb6d66fc1af3f38ee310cc1cd32cded7ffa5c93db9d4',
       'plan': 'b86e9d0d562b878f5a8dd05d079724a0ec2a1439a8853890f24621fe7b960ab5'},
 '12': {'midi': '7a9a533a903db99bb5df94c104b4584446eda11bb852e2cc51af591d23c4c66c',
        'plan': '1f0a37bcf0f16ca97aae613c9cabd5604a4501ff4adb6aea3213a0f54b48df42'}}


def explicit_plan(plan, version=2, phrase_bars=6):
    fields = asdict(plan)
    fields.update(version=version, phrase_bars=phrase_bars)
    return SimpleNamespace(**fields)


class PhraseBreathingTests(unittest.TestCase):
    def test_new_plans_schedule_balanced_chapter_shared_phrases(self):
        chapters = defaultdict(list)
        for position in range(1, 241):
            p = arrangement_for(42, position)
            self.assertEqual(p.version, 2)
            self.assertIn(getattr(p, 'phrase_bars', 0), (6, 8, 10))
            chapters[p.chapter].append(p)
        lengths = []
        for plans in chapters.values():
            self.assertEqual(len({p.phrase_bars for p in plans}), 1)
            lengths.append(plans[0].phrase_bars)
        for start in range(0, len(lengths), 3):
            self.assertEqual(set(lengths[start:start+3]), {6, 8, 10})
        self.assertTrue(all(a != b for a, b in zip(lengths, lengths[1:])))
        for position in (10**12, 1, 44, 10**18, 2):
            p = arrangement_for(-17, position)
            self.assertEqual(p, arrangement_for(-17, position))
            self.assertIn(p.phrase_bars, (6, 8, 10))

    def test_existing_choices_and_version_one_midi_are_unchanged(self):
        for position, fixture in FIXTURES.items():
            position = int(position)
            plan = arrangement_for(20261114, position)
            fields = asdict(plan)
            fields.pop('version')
            fields.pop('phrase_bars', None)
            self.assertEqual(hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest(), fixture['plan'])
            old = explicit_plan(plan, version=1, phrase_bars=0)
            score = midi(compose(20261114+position, 120, 60, old), 120, 60, old.programs)
            self.assertEqual(hashlib.sha256(score).hexdigest(), fixture['midi'])
        self.assertEqual(hashlib.sha256(midi(compose(42,120,60),120,60)).hexdigest(),
                         'b67795342a7544bdb82cdb645c3bcc35b3ea97da98e195e64ea9f3f48a7eb0bc')

    def test_all_stages_have_complete_rests_without_tails_and_keep_harmony(self):
        stages = {}
        for position in range(1, 25):
            plan = arrangement_for(42, position)
            stages.setdefault(plan.stage, plan)
        self.assertEqual(set(stages), {'arrival','unfold','bloom','settle','release'})
        for stage, base in stages.items():
            for bars in (6, 8, 10):
                for bpm in (40, 60, 90):
                    for seconds in (20, 120, 600):
                        with self.subTest(stage=stage,bars=bars,bpm=bpm,seconds=seconds):
                            plan = explicit_plan(base, phrase_bars=bars)
                            notes = compose(42+base.position, seconds, bpm, plan)
                            beat = 60/bpm; bar = 4*beat
                            self.assertTrue(any(n.channel == 2 for n in notes))
                            for note in notes:
                                self.assertTrue(all(math.isfinite(v) for v in (note.start,note.duration)))
                                self.assertTrue(0 <= note.start < seconds)
                                self.assertTrue(0 < note.duration <= seconds-note.start+1e-6)
                                self.assertTrue(36 <= note.pitch <= 84)
                                self.assertTrue(0 < note.velocity <= 60)
                            end = bars*bar
                            while end <= seconds-2:
                                start = end-bar
                                for n in (n for n in notes if n.channel == 2):
                                    self.assertFalse(n.start < end and n.start+n.duration > start-.1*beat+1e-6,
                                                     (start,end,n))
                                self.assertTrue(any(n.channel == 0 and n.start < end and n.start+n.duration > start for n in notes))
                                end += bars*bar

    def test_invalid_version_two_phrase_lengths_are_rejected(self):
        for value in (0,-1,True,6.0,7,'6',None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                compose(43,120,60,explicit_plan(arrangement_for(42,1),phrase_bars=value))

    def test_unknown_plan_versions_are_rejected(self):
        for version in (0,3,-1,True,2.0):
            with self.subTest(version=version), self.assertRaises(ValueError):
                compose(43,120,60,explicit_plan(arrangement_for(42,1),version=version))

    def test_positional_constructor_keeps_version_one_and_disables_new_phrasing(self):
        plan = arrangement_for(42,1)
        fields = asdict(plan);fields.pop('phrase_bars',None);fields['version']=1
        old = type(plan)(*fields.values())
        self.assertEqual(old.version,1)
        self.assertEqual(getattr(old,'phrase_bars',0),0)
        self.assertEqual(compose(43,120,60,old), compose(43,120,60,explicit_plan(plan,version=1,phrase_bars=10)))
