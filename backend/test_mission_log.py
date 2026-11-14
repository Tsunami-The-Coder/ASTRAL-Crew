import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from backend.crew import demo_profiles
from backend.cross_analysis import analyze_snapshot
from backend.mission_log import MissionLog
from backend.simulator import generate_scenario
from backend.storage import SnapshotStore


class MissionLogTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / 'mission.sqlite3'
        self.log = MissionLog(self.path)
        self.log.initialize()
        self.store = SnapshotStore(self.path)
        samples = generate_scenario('co2_rise')
        self.first = self.store.save_synthetic('2026-11-14T12:00:00Z',samples[0])
        self.last = self.store.save_synthetic('2026-11-14T12:11:00Z',samples[-1])
        self.report = analyze_snapshot(samples[-1],demo_profiles(),previous=samples[0])

    def test_saved_evidence_and_reviews_survive_reopen_without_changing_telemetry(self):
        original = self.store.history()
        identifier = self.log.save_analysis(self.last,self.report,previous_snapshot_id=self.first)
        self.log.add_review(identifier,reviewer='Demo reviewer',decision='follow_up',note='Verify readings.')
        self.log.add_review(identifier,reviewer='Demo reviewer',decision='acknowledged',note='Review recorded.')
        reopened = MissionLog(self.path)
        reopened.initialize()
        entries = reopened.entries()
        self.assertEqual(entries[0]['report'],self.report)
        self.assertEqual(entries[0]['snapshot_id'],self.last)
        self.assertEqual(len(entries[0]['reviews']),2)
        self.assertTrue(entries[0]['report']['needs_review'])
        self.assertEqual(self.store.history(),original)

    def test_missing_or_reversed_sources_are_rejected(self):
        for current,previous in ((999,self.first),(self.last,999),(self.first,self.last),(self.last,self.last)):
            with self.subTest(current=current,previous=previous),self.assertRaises(ValueError):
                self.log.save_analysis(current,self.report,previous_snapshot_id=previous)
        self.assertEqual(self.log.entries(),[])

    def test_bad_reviews_do_not_append(self):
        identifier = self.log.save_analysis(self.last,self.report)
        for kwargs in (dict(reviewer='',decision='acknowledged',note='check'),
                       dict(reviewer='demo',decision='automatic_override',note='check'),
                       dict(reviewer='demo',decision='follow_up',note=' ')):
            with self.assertRaises(ValueError):
                self.log.add_review(identifier,**kwargs)
        with self.assertRaises(ValueError):
            self.log.add_review(999,reviewer='demo',decision='follow_up',note='check')
        self.assertEqual(self.log.entries()[0]['reviews'],[])

    def test_malformed_report_rejected(self):
        for report in ({},dict(self.report,data_origin='measured'),dict(self.report,extra=float('nan'))):
            with self.assertRaises(ValueError):
                self.log.save_analysis(self.last,report)
        self.assertEqual(self.log.entries(),[])

    def test_limit_and_empty_log(self):
        self.assertEqual(self.log.entries(),[])
        for _ in range(3):
            self.log.save_analysis(self.last,self.report)
        self.assertEqual([entry['id'] for entry in self.log.entries(limit=2)],[2,3])
        with self.assertRaises(ValueError):
            self.log.entries(limit=True)

    def test_cli_full_flow_for_all_scenarios(self):
        for scenario in ('baseline','co2_rise','missing_sensor','faulty_sensor'):
            with self.subTest(scenario=scenario):
                path = self.path.parent / (scenario+'.sqlite3')
                def run(module,*arguments):
                    return subprocess.run([sys.executable,'-m',module,'--database',str(path),*arguments],
                                          check=True,capture_output=True,text=True).stdout
                run('backend.simulator','--scenario',scenario)
                run('backend.cross_analysis','--save')
                entries = json.loads(run('backend.mission_log'))
                self.assertEqual(len(entries),1)
                self.assertEqual(len(entries[0]['report']['crew']),5)
                reviewed = json.loads(run('backend.mission_log','--analysis-id','1',
                    '--reviewer','Test reviewer','--decision','follow_up','--note','Synthetic test only.'))
                self.assertEqual(len(reviewed[0]['reviews']),1)
                self.assertEqual(reviewed[0]['report'],entries[0]['report'])
