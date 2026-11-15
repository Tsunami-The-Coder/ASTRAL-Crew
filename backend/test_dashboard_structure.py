"""Guard the HTML/API handoff against accidental conflict-editor damage."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / 'ui/astral-prototype/index.html'

class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=[]
        self.main_count=0
        self.scripts=[]
    def handle_starttag(self,tag,attrs):
        attributes=dict(attrs)
        if 'id' in attributes:self.ids.append(attributes['id'])
        if tag=='main':self.main_count+=1
        if tag=='script' and 'src' in attributes:self.scripts.append(attributes['src'])

class DashboardStructureTests(unittest.TestCase):
    def test_unique_controls_and_required_pages(self):
        page=Elements();page.feed(PAGE.read_text())
        duplicates=[name for name,count in Counter(page.ids).items() if count>1]
        self.assertEqual(duplicates,[], 'Duplicated IDs break chart and button binding')
        self.assertEqual(page.main_count,1)
        for name in ('overview','crew','flagged','hazards','biology','about','sources'):
            self.assertIn('page-'+name,page.ids)
        for name in ('member-checkin-form','member-generate','member-checkin-submit','mission-recheck','mission-crew-chart','member-processing'):
            self.assertIn(name,page.ids)
    def test_bootstrap_json_and_script_assets(self):
        source=PAGE.read_text();page=Elements();page.feed(source)
        for marker in ('<<<<<<<','=======','>>>>>>>'):
            self.assertNotIn(marker,source)
        match=re.search(r'<script type="application/json" id="mission-demo-data">(.*?)</script>',source,re.S)
        self.assertIsNotNone(match)
        self.assertEqual(json.loads(match.group(1))['export_version'],'internal-review-v1')
        expected={'crew-dashboard.js','demo-connection.js','demo-playback.js','test-lab.js','member-checkin.js','interface-polish.js'}
        self.assertEqual({src.split('?')[0] for src in page.scripts},expected)
        self.assertEqual(len(page.scripts),len(expected))
        for src in page.scripts:self.assertTrue((PAGE.parent/src.split('?')[0]).is_file(),src)
