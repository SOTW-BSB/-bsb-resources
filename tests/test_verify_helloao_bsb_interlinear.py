"""Offline gate tests: complete fixture, tampering, partial artifact and extra files."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "verifier", Path(__file__).resolve().parents[1] / "scripts/verify_helloao_bsb_interlinear.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.catalog = self.root / "books.json"
        self.data = self.root / "v1"
        (self.data / "chapters" / "JHN").mkdir(parents=True)
        self.catalog.write_text(json.dumps({"edition_id": "BSB", "books": [
            {"code": "JHN", "chapter_count": 1}
        ]}))
        self.chapter = {"schema": module.CHAPTER_SCHEMA, "edition_id": "BSB",
                        "book_code": "JHN", "chapter": 1,
                        "source": {"provider": "HelloAO Free Use Bible API", "publisher": "Berean Bible",
                                   "dataset": module.DATASET, "url": module.SOURCE_ROOT + "JHN/1.json",
                                   "response_sha256": "a" * 64},
                        "verses": [{"verse": 1, "id": "JHN.1.1", "words": [{"strongs": "G3056"}]}]}
        self.target = self.data / "chapters" / "JHN" / "01.json"
        self.target.write_text(json.dumps(self.chapter))
        self.manifest = {"schema": module.MANIFEST_SCHEMA, "dataset": module.DATASET,
                         "status": "STAGED_SOURCE_DATA_NOT_READER_CONNECTED",
                         "chapters_imported": 1, "original_language_words_imported": 1,
                         "files": [{"path": "chapters/JHN/01.json",
                                    "sha256": module.hashlib.sha256(self.target.read_bytes()).hexdigest(),
                                    "words": 1}]}
        (self.data / "manifest.json").write_text(json.dumps(self.manifest))

    def test_complete_fixture_against_reduced_expectations(self):
        original, books = module.EXPECTED_CHAPTERS, module.EXPECTED_BOOKS
        try:
            module.EXPECTED_CHAPTERS, module.EXPECTED_BOOKS = 1, 1
            result = module.verify(self.data, self.catalog, expected_words=1)
            self.assertEqual(result["sha256_verified_chapters"], 1)
        finally:
            module.EXPECTED_CHAPTERS, module.EXPECTED_BOOKS = original, books

    def test_tampered_file_fails_even_when_manifest_count_is_complete(self):
        original, books = module.EXPECTED_CHAPTERS, module.EXPECTED_BOOKS
        try:
            module.EXPECTED_CHAPTERS, module.EXPECTED_BOOKS = 1, 1
            self.target.write_text(self.target.read_text().replace("G3056", "G1234"))
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                module.verify(self.data, self.catalog, expected_words=1)
        finally:
            module.EXPECTED_CHAPTERS, module.EXPECTED_BOOKS = original, books

    def test_incomplete_artifact_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "1,189"):
            module.verify(self.data, self.catalog)

    def test_unlisted_file_is_rejected(self):
        original, books = module.EXPECTED_CHAPTERS, module.EXPECTED_BOOKS
        try:
            module.EXPECTED_CHAPTERS, module.EXPECTED_BOOKS = 1, 1
            (self.data / "extra.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "Unexpected files"):
                module.verify(self.data, self.catalog, expected_words=1)
        finally:
            module.EXPECTED_CHAPTERS, module.EXPECTED_BOOKS = original, books


if __name__ == "__main__":
    unittest.main()
