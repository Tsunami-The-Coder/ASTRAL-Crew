import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.crew import demo_profiles
from backend.cross_analysis import analyze_snapshot
from backend.service import MissionService
from backend.simulator import generate_scenario


class RunSafetyTests(unittest.TestCase):
    def test_run_filter_before_limit_and_strict_comparison(self):
        with tempfile.TemporaryDirectory() as folder:
            service=MissionService(Path(folder)/'mission.sqlite3')
            service.initialize()
            samples=generate_scenario('co2_rise')
            for index,sample in enumerate((samples[0],samples[-1])):
                sample['run_id']='first'
                service.store.save_synthetic(f'2026-11-14T12:{index:02}:00Z',sample)
            other=generate_scenario()[-1]
            other['run_id']='second'
            service.store.save_synthetic('2026-11-14T12:02:00Z',other)
            selected=service.history(run_id='first',limit=1)
            self.assertEqual(len(selected),1)
            self.assertEqual(selected[0]['payload']['run_id'],'first')
            self.assertEqual(service.history(run_id='absent'),[])
            with self.assertRaises(ValueError):
                analyze_snapshot(other,demo_profiles(),previous=samples[0])
            with self.assertRaises(ValueError):
                analyze_snapshot(samples[0],demo_profiles(),previous=samples[-1])
            with self.assertRaises(ValueError):
                service.history(run_id=' ')

    def test_freshness_boundary_future_and_historical_analysis(self):
        with tempfile.TemporaryDirectory() as folder:
            timestamp=datetime(2026,11,14,12,tzinfo=timezone.utc)
            service=MissionService(Path(folder)/'mission.sqlite3',clock=lambda:timestamp)
            service.initialize()
            sample=generate_scenario()[-1]
            identifier=service.store.save_synthetic(timestamp.isoformat(),sample)
            service.log.save_analysis(identifier,analyze_snapshot(sample,demo_profiles()))
            self.assertEqual(service.overview()['freshness']['status'],'fresh')
            service.clock=lambda:timestamp+timedelta(seconds=300)
            self.assertIsNotNone(service.overview()['current_analysis'])
            service.clock=lambda:timestamp+timedelta(seconds=301)
            view=service.overview()
            self.assertEqual(view['freshness']['status'],'stale')
            self.assertIsNone(view['current_analysis'])
            self.assertIsNotNone(view['historical_analysis'])
            service.clock=lambda:timestamp-timedelta(seconds=1)
            self.assertEqual(service.overview()['freshness']['status'],'future')
            self.assertIsNone(service.overview()['current_analysis'])
            service.clock=lambda:datetime(2026,11,14)
            with self.assertRaises(ValueError):
                service.overview()

    def test_invalid_freshness_policy(self):
        for seconds in (0,-1,True,float('nan')):
            with self.assertRaises(ValueError):
                MissionService(max_age_seconds=seconds)

    def test_cli_selects_run_in_database_with_repeated_runs(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'mission.sqlite3'
            for _ in range(2):
                subprocess.run([sys.executable,'-m','backend.simulator','--database',str(path),
                                '--scenario','pressure_drop'],check=True,stdout=subprocess.DEVNULL)
            service=MissionService(path)
            rows=service.history()
            runs={row['payload']['run_id'] for row in rows}
            self.assertEqual(len(runs),2)
            for run_id in runs:
                result=subprocess.run([sys.executable,'-m','backend.cross_analysis','--database',str(path),
                                       '--run-id',run_id],check=True,capture_output=True,text=True)
                self.assertEqual(json.loads(result.stdout)['findings'][0]['code'],'CABIN_PRESSURE_DROP')
