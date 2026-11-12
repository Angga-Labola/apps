import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from fastapi.exceptions import HTTPException

import sokoban


class SokobanApiTests(unittest.TestCase):
    @patch.dict(os.environ, {"SOKOBAN_KEY": "test-key"})
    @patch("sokoban.requests.post")
    def test_fetch_levels_posts_key_and_returns_level_list(self, post):
        levels = [{"id": 1, "name": "First level"}]
        response = Mock(ok=True)
        response.json.return_value = levels
        post.return_value = response

        self.assertEqual(sokoban.fetch_sokoban_levels(), levels)
        post.assert_called_once_with(
            f"{sokoban.LETSLOGIC_API_URL}/collection/{sokoban.SOKOBAN_COLLECTION_ID}",
            data={"key": "test-key"},
            timeout=8,
        )

    @patch.dict(os.environ, {}, clear=True)
    def test_fetch_levels_reports_missing_api_key(self):
        with self.assertRaises(HTTPException) as raised:
            sokoban.fetch_sokoban_levels()

        self.assertEqual(raised.exception.status_code, 503)

    @patch.dict(os.environ, {"SOKOBAN_KEY": "test-key"})
    @patch("sokoban.requests.post")
    def test_fetch_levels_unwraps_documented_levels_object(self, post):
        response = Mock(ok=True)
        response.json.return_value = {"levels": [{"id": 3}]}
        post.return_value = response

        self.assertEqual(sokoban.fetch_sokoban_levels(), [{"id": 3}])

    @patch.dict(os.environ, {"SOKOBAN_KEY": "test-key"})
    @patch("sokoban.requests.post")
    def test_fetch_levels_surfaces_upstream_errors(self, post):
        response = Mock(ok=False)
        post.return_value = response

        with self.assertRaises(HTTPException) as raised:
            sokoban.fetch_sokoban_levels()

        self.assertEqual(raised.exception.status_code, 502)

    @patch.dict(os.environ, {"SOKOBAN_KEY": "test-key"})
    @patch("sokoban.requests.post")
    def test_collection_download_returns_json_attachment(self, post):
        levels = [{"id": 8, "name": "Downloaded level"}]
        response = Mock(ok=True)
        response.json.return_value = levels
        post.return_value = response

        download = sokoban.download_sokoban_collection()

        self.assertIn("attachment;", download.headers["content-disposition"])
        self.assertEqual(json.loads(download.body), {
            "collection_id": sokoban.SOKOBAN_COLLECTION_ID,
            "levels": levels,
        })

    @patch("sokoban.fetch_sokoban_collections")
    def test_collection_list_returns_names_and_ids(self, fetch_collections):
        fetch_collections.return_value = [
            {"id": 12, "name": "Small puzzles", "levels": [1, 2]},
            {"id": "../outside", "name": "Invalid"},
        ]

        result = sokoban.sokoban_collections()

        self.assertEqual(result["collections"], [{
            "id": "12",
            "name": "Small puzzles",
            "description": "",
            "author": "",
            "level_count": 2,
        }])

    @patch("sokoban.fetch_sokoban_levels", return_value=[{"id": 1, "map": "@$."}])
    @patch.dict(os.environ, {}, clear=True)
    def test_download_saves_and_returns_playable_collection(self, _fetch_levels):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch.object(sokoban, "SOKOBAN_COLLECTIONS_DIR", sokoban.Path(temporary_directory)):
                downloaded = sokoban.save_sokoban_collection(
                    "44",
                    sokoban.CollectionDownloadRequest(
                        name="Test collection",
                        description="A short collection description.",
                        author="Puzzle author",
                    ),
                )
                saved = sokoban.get_saved_sokoban_collection("44")
                listed = sokoban.list_saved_sokoban_collections()

        self.assertEqual(downloaded["storage"], "local")
        self.assertEqual(downloaded["saved_file"], "44.json")
        self.assertEqual(saved["name"], "Test collection")
        self.assertEqual(saved["description"], "A short collection description.")
        self.assertEqual(saved["author"], "Puzzle author")
        self.assertEqual(saved["levels"], [{"id": 1, "map": "@$."}])
        self.assertEqual(listed["collections"][0]["collection_id"], "44")
        self.assertEqual(
            listed["collections"][0]["description"],
            "A short collection description.",
        )

    def test_download_rejects_non_numeric_collection_ids(self):
        with self.assertRaises(HTTPException) as raised:
            sokoban.save_sokoban_collection("../outside")

        self.assertEqual(raised.exception.status_code, 400)

    def test_vercel_download_saves_to_blob(self):
        uploaded = Mock(pathname="sokoban-collections/44.json")
        with (
            patch.dict(os.environ, {"VERCEL": "1"}),
            patch("sokoban.fetch_sokoban_levels", return_value=[{"id": 1, "map": "@$."}]),
            patch("sokoban.vercel_blob.put_blob", return_value=uploaded) as put_blob,
        ):
            result = sokoban.save_sokoban_collection(
                "44",
                sokoban.CollectionDownloadRequest(name="Test collection"),
            )

        self.assertEqual(result["storage"], "vercel_blob")
        self.assertEqual(result["saved_file"], "sokoban-collections/44.json")
        put_blob.assert_called_once()
        self.assertEqual(put_blob.call_args.args[0], "sokoban-collections/44.json")
        self.assertEqual(put_blob.call_args.kwargs["access"], "public")
        self.assertTrue(put_blob.call_args.kwargs["allow_overwrite"])

    def test_vercel_download_uses_configured_private_blob_access(self):
        uploaded = Mock(pathname="sokoban-collections/44.json")
        with (
            patch.dict(
                os.environ,
                {"VERCEL": "1", "SOKOBAN_BLOB_ACCESS": "private"},
            ),
            patch("sokoban.fetch_sokoban_levels", return_value=[{"id": 1, "map": "@$."}]),
            patch("sokoban.vercel_blob.put_blob", return_value=uploaded) as put_blob,
        ):
            sokoban.save_sokoban_collection(
                "44",
                sokoban.CollectionDownloadRequest(name="Test collection"),
            )

        self.assertEqual(put_blob.call_args.kwargs["access"], "private")

    def test_vercel_download_reports_blob_error_details(self):
        error = sokoban.BlobError(
            "The store is suspended.",
            status_code=400,
            code="store_suspended",
        )
        with (
            patch.dict(os.environ, {"VERCEL": "1"}),
            patch("sokoban.fetch_sokoban_levels", return_value=[{"id": 1, "map": "@$."}]),
            patch("sokoban.vercel_blob.put_blob", side_effect=error),
        ):
            with self.assertRaises(HTTPException) as raised:
                sokoban.save_sokoban_collection(
                    "44",
                    sokoban.CollectionDownloadRequest(name="Test collection"),
                )

        self.assertEqual(raised.exception.status_code, 502)
        self.assertIn("400, store_suspended", raised.exception.detail)
        self.assertIn("The store is suspended.", raised.exception.detail)

    def test_vercel_saved_collections_are_listed_from_blob(self):
        saved = {
            "collection_id": "44",
            "name": "Test collection",
            "description": "A description",
            "author": "Puzzle author",
            "levels": [{"id": 1}, {"id": 2}],
        }
        with (
            patch.dict(os.environ, {"VERCEL": "1"}),
            patch(
                "sokoban.vercel_blob.query_blobs",
                return_value=[
                    Mock(pathname="sokoban-collections/44.json"),
                    Mock(pathname="sokoban-collections/invalid.json"),
                ],
            ),
            patch(
                "sokoban.vercel_blob.get_blob",
                return_value=Mock(body=json.dumps(saved).encode("utf-8")),
            ) as get_blob,
        ):
            result = sokoban.list_saved_sokoban_collections()

        self.assertEqual(result["storage"], "vercel_blob")
        self.assertEqual(result["collections"], [{
            "collection_id": "44",
            "name": "Test collection",
            "description": "A description",
            "author": "Puzzle author",
            "level_count": 2,
        }])
        get_blob.assert_called_once_with(
            "sokoban-collections/44.json",
            access="public",
        )

    def test_vercel_saved_collection_can_be_opened_and_deleted(self):
        saved = {"collection_id": "44", "levels": [{"id": 1}]}
        with (
            patch.dict(os.environ, {"VERCEL": "1"}),
            patch(
                "sokoban.vercel_blob.get_blob",
                return_value=Mock(body=json.dumps(saved).encode("utf-8")),
            ) as get_blob,
            patch("sokoban.vercel_blob.delete_blob") as delete_blob,
        ):
            opened = sokoban.get_saved_sokoban_collection("44")
            deleted = sokoban.delete_saved_sokoban_collection("44")

        self.assertEqual(opened, saved)
        self.assertEqual(deleted, {"deleted": "44", "storage": "vercel_blob"})
        get_blob.assert_called_once_with(
            "sokoban-collections/44.json",
            access="public",
        )
        delete_blob.assert_called_once_with("sokoban-collections/44.json")

    def test_local_saved_collection_can_be_deleted(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = sokoban.Path(temporary_directory) / "44.json"
            path.write_text('{"levels": []}', encoding="utf-8")
            with (
                patch.dict(os.environ, {}, clear=True),
                patch.object(sokoban, "SOKOBAN_COLLECTIONS_DIR", sokoban.Path(temporary_directory)),
            ):
                result = sokoban.delete_saved_sokoban_collection("44")

            self.assertFalse(path.exists())

        self.assertEqual(result, {"deleted": "44", "storage": "local"})

    def test_delete_rejects_non_numeric_collection_ids(self):
        with self.assertRaises(HTTPException) as raised:
            sokoban.delete_saved_sokoban_collection("../outside")

        self.assertEqual(raised.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
