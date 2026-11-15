import base64
import tempfile
import unittest
from pathlib import Path
import numpy as np
from backend.demo_engine import DemoEngine
from backend.test_lab import run_test, sample_wav, decode_wav

class SampleLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.engine = DemoEngine(Path(cls.temp.name)/'lab.sqlite3', Path(__file__).resolve().parents[1]/'models/wearable/model.json')
    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()
    def test_voice_samples_and_silence(self):
        for sample in ('calm','aroused'):
            result=run_test(self.engine,{'kind':'voice','sample':sample})
            self.assertIsNotNone(result['result']['record'])
        result=run_test(self.engine,{'kind':'voice','sample':'silence'})
        self.assertIsNone(result['result']['record'])
        self.assertEqual(result['result']['details']['status'],'no_speech')
    def test_wearable_and_missing(self):
        for sample in ('rest','elevated','movement'):
            result=run_test(self.engine,{'kind':'wearable','sample':sample})
            self.assertIsNotNone(result['result']['stress_score'])
        result=run_test(self.engine,{'kind':'wearable','sample':'missing'})
        self.assertIsNone(result['result']['stress_score'])
    def test_upload_validation(self):
        with self.assertRaises(ValueError): decode_wav('broken')
        with self.assertRaises(ValueError): run_test(self.engine,{'kind':'voice','sample':'upload','baseline_wavs':[]})
        with self.assertRaises(ValueError): run_test(self.engine,{'kind':'wearable','sample':'upload','signals':{}})
        encoded=base64.b64encode(sample_wav('calm')).decode()
        self.assertEqual(len(decode_wav(encoded)),48000)
        result=run_test(self.engine,{'kind':'voice','sample':'upload','baseline_wavs':[encoded]*5,'test_wav':encoded})
        self.assertEqual(result['origin'],'uploaded recording')
        self.assertIsNotNone(result['result']['record'])
    def test_recorded_wrist_shape(self):
        result=run_test(self.engine,{'kind':'wearable','sample':'upload','signals':{
            'BVP':np.sin(2*np.pi*np.arange(3840)/64).tolist(),
            'EDA':[2.0]*240,'ACC':[[0,0,64]]*1920}})
        self.assertEqual(result['result']['data_origin'],'replayed')
        self.assertIsNotNone(result['result']['stress_score'])

    def test_nasa_audio_features_without_stress_claim(self):
        for sample in ('artemis-terminator','artemis-closest'):
            result=run_test(self.engine,{'kind':'voice','sample':sample})
            self.assertEqual(result['result']['status'],'features_extracted')
            self.assertIsNone(result['result']['stress_score'])
            self.assertIn('f0_mean_hz',result['result']['features'])
            self.assertEqual(result['source']['credit'],'NASA')
