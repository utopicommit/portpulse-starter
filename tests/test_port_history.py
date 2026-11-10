"""Local tests for the historical data transformation (no internet needed)."""
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from port_history import calculate_pbi, fetch_port_calls, find_port_id


class PortHistoryTests(unittest.TestCase):
    def test_pbi_doubles_when_recent_calls_double(self):
        # 28 baseline days at 10 calls/day, then 7 more days at 10,
        # then 7 days at 20. The final PBI should equal 200.
        dates = pd.date_range("2026-01-01", periods=42, freq="D")
        source = pd.DataFrame({"date": dates, "portcalls": [10] * 35 + [20] * 7})
        result = calculate_pbi(source)
        self.assertAlmostEqual(result.iloc[-1]["pbi"], 200.0)

    def test_missing_baseline_day_does_not_become_zero(self):
        dates = pd.date_range("2026-01-01", periods=42, freq="D")
        source = pd.DataFrame({"date": dates, "portcalls": [10] * 42})
        source = source[source.date != pd.Timestamp("2026-01-10")]
        result = calculate_pbi(source)
        self.assertTrue(pd.isna(result.iloc[-1]["pbi"]))

    @patch("port_history._get_rows")
    def test_port_lookup_uses_exact_port_name_and_country(self, mock_rows):
        mock_rows.return_value = [{"portname": "Karachi", "ISO3": "PAK", "portid": "port123"}]
        self.assertEqual(find_port_id("Karachi"), "port123")
        self.assertIn("ISO3 = 'PAK'", mock_rows.call_args.args[1]["where"])

    @patch("port_history._get_rows")
    @patch("port_history.find_port_id", return_value="port1114")
    def test_fetch_parses_and_sorts_dates(self, _, mock_rows):
        mock_rows.return_value = [
            {"date": "2026-11-04", "portcalls": 6},
            {"date": "2026-11-03", "portcalls": 4},
        ]
        result = fetch_port_calls("Rotterdam")
        self.assertEqual(result.iloc[0]["portcalls"], 4)
        self.assertEqual(str(result.iloc[-1]["date"].date()), "2026-11-04")


if __name__ == "__main__":
    unittest.main()
