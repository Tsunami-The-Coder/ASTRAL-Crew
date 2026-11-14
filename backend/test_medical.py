import json
import tempfile
import unittest
from pathlib import Path

from backend.crew import demo_profiles
from backend.medical import resource_catalog
from backend.service import MissionService
from backend.simulator import generate_scenario


class MedicalTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder=Path(folder.name)
        self.service=MissionService(self.folder/'mission.sqlite3')
        self.service.initialize()
        self.service.store.register_synthetic_profiles(demo_profiles())

    def test_bundled_catalog_honestly_has_no_clinical_content(self):
        catalog=self.service.medical_resources()
        self.assertEqual(catalog['availability'],'no_reviewed_content')
        self.assertEqual(catalog['resources'],[])

    def test_incidents_per_crew_and_append_notes_survive_reopen(self):
        original=self.service.store.history()
        for profile in demo_profiles():
            identifier=self.service.record_medical_incident(profile['crew_id'],summary='Synthetic demo observation.')
            self.service.record_medical_note(identifier,reviewer='Demo reviewer',note='Observation reviewed in simulation.')
        reopened=MissionService(self.service.store.path)
        reopened.initialize()
        self.assertEqual(len(reopened.medical_incidents()),5)
        one=reopened.medical_incidents(crew_id='AST-05')
        self.assertEqual(len(one),1)
        self.assertEqual(one[0]['data_origin'],'synthetic')
        self.assertEqual(len(one[0]['notes']),1)
        self.assertEqual(self.service.store.history(),original)

    def test_source_snapshot_must_contain_crew(self):
        snapshot=self.service.store.save_synthetic('2026-11-14T12:00:00Z',generate_scenario(crew_count=4)[0])
        with self.assertRaises(ValueError):
            self.service.record_medical_incident('AST-05',summary='Demo',snapshot_id=snapshot)
        identifier=self.service.record_medical_incident('AST-01',summary='Demo',snapshot_id=snapshot)
        self.assertEqual(self.service.medical_incidents()[0]['snapshot_id'],snapshot)
        self.assertEqual(identifier,1)

    def test_bad_inputs_and_unknown_ids_rejected(self):
        for crew,summary in (('AST-99','Demo'),('AST-01',' ')):
            with self.assertRaises(ValueError):
                self.service.record_medical_incident(crew,summary=summary)
        with self.assertRaises(ValueError):
            self.service.record_medical_incident('AST-01',summary='Demo',snapshot_id=999)
        with self.assertRaises(ValueError):
            self.service.record_medical_note(999,reviewer='Demo',note='Demo')
        with self.assertRaises(ValueError):
            self.service.medical_incidents(limit=True)
        self.assertEqual(self.service.medical_incidents(),[])

    def test_pending_content_hidden_and_approval_metadata_required(self):
        path=self.folder/'catalog.json'
        entry=dict(resource_id='test',title='Test fixture',version='v1',
                   source_url='https://example.org/test',reuse_terms='Test metadata only',
                   review_status='pending',offline_content='Unreviewed fixture text')
        path.write_text(json.dumps(dict(catalog_version='test',resources=[entry])))
        self.assertIsNone(resource_catalog(path)['resources'][0]['offline_content'])
        entry['review_status']='approved'
        path.write_text(json.dumps(dict(catalog_version='test',resources=[entry])))
        with self.assertRaises(ValueError):
            resource_catalog(path)
        entry.update(reviewer='Test reviewer',reviewed_at='2026-11-14T12:00:00Z')
        path.write_text(json.dumps(dict(catalog_version='test',resources=[entry])))
        self.assertEqual(resource_catalog(path)['availability'],'available')

    def test_missing_or_malformed_catalog_is_explicit(self):
        path=self.folder/'bad.json'
        with self.assertRaises(ValueError):
            resource_catalog(path)
        path.write_text('not json')
        with self.assertRaises(ValueError):
            resource_catalog(path)
