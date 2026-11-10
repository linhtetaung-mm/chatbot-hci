"""Data-loss and scoring regressions; use synthetic records only."""
import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from tools.combine_data import blind, combine, kappa, score


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def csv(self, name, rows, columns=None):
        path = self.root / name
        with path.open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=columns or list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        return str(path)

    def read(self, name):
        with (self.root / 'out' / name).open(newline='') as f:
            return list(csv.DictReader(f))

    def blind_args(self, rows):
        return SimpleNamespace(final=self.csv('final.csv', rows), id_column=None,
                               answer_column=None, scenario_column=None, out=str(self.root / 'out'))

    def test_both_google_form_branches_survive_and_key_is_not_replaced(self):
        args = self.blind_args([
            {'Study ID': 'p1', 'A: Imagine this happened': 'Answer A', 'B: Imagine this happened': ''},
            {'Study ID': 'P02', 'A: Imagine this happened': '', 'B: Imagine this happened': 'Answer B'},
        ])
        with redirect_stdout(io.StringIO()):
            blind(args)
        rows = self.read('coders_scenarios.csv')
        self.assertEqual({r['answer'] for r in rows}, {'Answer A', 'Answer B'})
        self.assertNotIn('study_id', rows[0])
        key = (self.root / 'out/coders_key.csv').read_bytes()
        with self.assertRaisesRegex(SystemExit, 'already exist'):
            blind(args)
        self.assertEqual((self.root / 'out/coders_key.csv').read_bytes(), key)

    def test_ambiguous_or_blank_answers_fail_before_creating_key(self):
        for a, b in [('', ''), ('A', 'B')]:
            with self.subTest(a=a, b=b):
                args = self.blind_args([{'Study ID': 'P01', 'A: Imagine this happened': a, 'B: Imagine this happened': b}])
                with self.assertRaisesRegex(SystemExit, 'exactly one'):
                    blind(args)
                self.assertFalse((self.root / 'out/coders_key.csv').exists())

    def test_duplicate_final_uses_same_last_response_policy(self):
        args = self.blind_args([
            {'Study ID': 'P01', 'Imagine this happened': 'old'},
            {'Study ID': 'p1', 'Imagine this happened': 'corrected'},
        ])
        with redirect_stdout(io.StringIO()):
            blind(args)
        self.assertEqual([r['answer'] for r in self.read('coders_scenarios.csv')], ['corrected'])

    def test_no_variation_kappa_is_undefined_and_invalid_scores_rejected(self):
        self.assertIsNone(kappa([3, 3], [3, 3]))
        self.assertEqual(kappa([0, 1, 2, 3], [0, 1, 2, 3]), 1)
        for value in ['1.9', '-1', '4', 'nan', 'bad']:
            with self.subTest(value=value), self.assertRaises(SystemExit):
                score(value, 'S123', 'coder1')
        self.assertEqual(score('2.0', 'S123', 'coder1'), 2)
        self.assertIsNone(score('', 'S123', 'coder1'))

    def test_zero_chat_participant_is_retained_from_roster(self):
        chats = self.csv('chats.csv', [], ['study_id', 'test_account', 'status'])
        export = self.root / 'records.json'
        export.write_text(json.dumps({'testers': [
            {'study_id': 'P01', 'locked': 1, 'active_style': 'guide', 'memory': 'fresh'},
            {'study_id': 'P02', 'locked': 1, 'active_style': 'reassure', 'memory': 'persistent'},
            {'study_id': None, 'locked': 0, 'active_style': 'guide', 'memory': 'fresh'},
        ]}))
        baseline = self.csv('base.csv', [{'Study ID': 'P01', 'Example item': '5'}])
        args = SimpleNamespace(chats=chats, participants=str(export), baseline=baseline, final=None,
                               scores=None, key=None, id_column=None, out=str(self.root / 'out'))
        with redirect_stdout(io.StringIO()):
            combine(args)
        rows = self.read('person_level.csv')
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]['chats_finished'], '0')
        self.assertEqual(rows[1]['style'], 'reassure')
        self.assertEqual(rows[1]['avg_distress_change'], '')
        self.assertEqual(rows[1]['has_baseline'], '0')

    def test_form_only_ids_remain_visible_without_invented_conditions(self):
        args = SimpleNamespace(chats=self.csv('chats.csv', [], ['study_id', 'status']), participants=None,
                               baseline=self.csv('base.csv', [{'Study ID': 'P99'}]), final=None,
                               scores=None, key=None, id_column=None, out=str(self.root / 'out'))
        log = io.StringIO()
        with redirect_stdout(log):
            combine(args)
        row = self.read('person_level.csv')[0]
        self.assertEqual((row['study_id'], row['style']), ('P99', ''))
        self.assertIn('assignment is unknown', log.getvalue())

    def test_open_chats_are_not_counted_as_stopped(self):
        row = {'study_id':'P01','status':'open','style':'guide','memory':'fresh','safety_stop':'0'}
        args = SimpleNamespace(chats=self.csv('chats.csv', [row]), participants=None,
                               baseline=None, final=None, scores=None, key=None,
                               id_column=None, out=str(self.root / 'out'))
        with redirect_stdout(io.StringIO()):
            combine(args)
        output = self.read('person_level.csv')[0]
        self.assertEqual((output['chats_stopped'],output['chats_open']),('0','1'))

    def test_constant_coder_scores_print_undefined_without_crashing(self):
        args = SimpleNamespace(chats=self.csv('chats.csv', [], ['study_id','status']), participants=None,
                               baseline=self.csv('base.csv', [{'Study ID':'P01'}]), final=None,
                               scores=self.csv('scores.csv',[{'code':'S123','coder1':'3','coder2':'3','final':'3'}]),
                               key=self.csv('key.csv',[{'code':'S123','study_id':'P01'}]),
                               id_column=None, out=str(self.root / 'out'))
        log = io.StringIO()
        with redirect_stdout(log):
            combine(args)
        self.assertIn('undefined (no marginal variation)',log.getvalue())
        self.assertEqual(self.read('person_level.csv')[0]['scenario_score'],'3')
