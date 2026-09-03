import sqlite3
import unittest
from datetime import date
from unittest.mock import Mock
import weekly_report

class WeeklyReportTests(unittest.TestCase):
    def test_thursday_bounds(self):
        self.assertEqual(weekly_report.week_bounds(date(2026,9,3)), (date(2026,8,31),date(2026,9,3),date(2026,8,24),date(2026,8,30)))
    def test_monday_bounds(self):
        self.assertEqual(weekly_report.week_bounds(date(2026,9,7)), (date(2026,9,7),date(2026,9,7),date(2026,8,31),date(2026,9,6)))
    def test_zero_calls_openai_with_short_prompt(self):
        import os
        os.environ["OPENAI_API_KEY"]="test-key"
        response=Mock(output_text="이번 주 지출이 없습니다.")
        client=Mock(); client.responses.create.return_value=response
        stats={"current":{"total":0,"period":{"start":"2026-08-31","end":"2026-09-03"}},"previous":{"total":100},"change_percent":-100}
        self.assertEqual(weekly_report.generate_summary(stats,lambda **kwargs: client),"이번 주 지출이 없습니다.")
        client.responses.create.assert_called_once()
        self.assertIn("지출이 0원",client.responses.create.call_args.kwargs["input"])

    def test_nonzero_calls_openai(self):
        import os
        os.environ["OPENAI_API_KEY"]="test-key"
        response=Mock(output_text="분석 결과")
        client=Mock(); client.responses.create.return_value=response
        stats={"current":{"total":100,"period":{"start":"2026-08-31","end":"2026-09-03"}},"previous":{"total":50},"change_percent":100}
        self.assertEqual(weekly_report.generate_summary(stats,lambda **kwargs: client),"분석 결과")
        client.responses.create.assert_called_once()

if __name__=="__main__": unittest.main()
