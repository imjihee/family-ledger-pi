import os
import unittest
from datetime import date
from unittest.mock import Mock
import weekly_report

class WeeklyReportTests(unittest.TestCase):
 def test_thursday_bounds(self):
  self.assertEqual(weekly_report.week_bounds(date(2026,9,3)),(date(2026,8,31),date(2026,9,3),date(2026,8,24),date(2026,8,30)))
 def test_monday_bounds(self):
  self.assertEqual(weekly_report.week_bounds(date(2026,9,7)),(date(2026,9,7),date(2026,9,7),date(2026,8,31),date(2026,9,6)))
 def test_zero_skips_api_and_fixed_template(self):
  stats={"current":{"total":0,"period":{"start":"2026-08-31","end":"2026-09-03"}},"previous":{"total":100},"change_percent":-100}
  factory=Mock(); self.assertEqual(weekly_report.generate_analysis(stats,factory),''); factory.assert_not_called()
  self.assertIn('이번 주 지출이 없습니다.',weekly_report.build_report_message(stats,'ignored'))
 def test_previous_zero_omits_change_line(self):
  stats={"current":{"total":100,"category_totals":{"식비":100},"period":{"start":"2026-08-31","end":"2026-09-03"}},"previous":{"total":0},"change_percent":None}
  msg=weekly_report.build_report_message(stats,'분석'); self.assertNotIn('전주 대비',msg); self.assertIn('식비: 100원',msg)
 def test_nonzero_calls_openai_and_template_numbers_are_python(self):
  os.environ["OPENAI_API_KEY"]="test-key"; client=Mock(); client.responses.create.return_value=Mock(output_text='분석')
  stats={"current":{"total":100,"category_totals":{"식비":100},"period":{"start":"2026-08-31","end":"2026-09-03"}},"previous":{"total":50},"change_percent":100}
  analysis=weekly_report.generate_analysis(stats,lambda **kwargs:client); msg=weekly_report.build_report_message(stats,analysis)
  client.responses.create.assert_called_once(); self.assertIn('100원',msg); self.assertIn('분석',msg)
if __name__=="__main__": unittest.main()
