import io
import json
import unittest
import zipfile
from unittest.mock import Mock, patch

from fastapi.exceptions import HTTPException

import sokoban_router


def records_archive(payload):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("records.json", json.dumps(payload))
    return buffer.getvalue()


class SokobanRecordsTests(unittest.TestCase):
    @patch(
        "sokoban_router.request_letslogic",
        return_value=Mock(content=records_archive([{"level_id": 12, "moves": 4}])),
    )
    def test_fetch_records_decodes_letslogic_archive(self, request):
        self.assertEqual(
            sokoban_router.fetch_sokoban_records(),
            [{"level_id": 12, "moves": 4}],
        )
        request.assert_called_once_with("records")

    @patch(
        "sokoban_router.request_letslogic",
        return_value=Mock(content=b"not a zip archive"),
    )
    def test_fetch_records_reports_invalid_archive(self, _request):
        with self.assertRaises(HTTPException) as raised:
            sokoban_router.fetch_sokoban_records()

        self.assertEqual(raised.exception.status_code, 502)

    @patch("sokoban_router.fetch_sokoban_records", return_value=[])
    def test_records_route_returns_records(self, _fetch_records):
        self.assertEqual(sokoban_router.sokoban_records(), {"records": []})


if __name__ == "__main__":
    unittest.main()
