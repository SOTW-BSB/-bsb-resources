#!/usr/bin/env python3
"""Fail-closed verifier for the staged 66-book HelloAO BSB interlinear artifact.

Works on the unpacked Action artifact. Does not alter source data, pilot,
Bible text, or reader. Source hashes and SOTW book/chapter coverage must agree.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

EXPECTED_CHAPTERS = 1189
EXPECTED_BOOKS = 66
EXPECTED_WORDS = 443625
DATASET = "bsb-interlinear"
MANIFEST_SCHEMA = "sotw-bsb-helloao-interlinear-source-manifest/1.0.0"
CHAPTER_SCHEMA = "sotw-bsb-helloao-interlinear-source/1.0.0"
SOURCE_ROOT = "https://bible.helloao.org/api/d/bsb-interlinear/"
FILE_RE = re.compile(r"chapters/([A-Z0-9]{3})/([0-9]{2,3})\.json\Z")


def read_json(path):
    return json.loads(path.read_bytes())


def fail(message):
    raise ValueError(message)


def verify(root: Path, catalog: Path, expected_words=EXPECTED_WORDS):
    if not root.is_dir():
        fail(f"Staged root directory missing: {root}")
    if not (root / "manifest.json").is_file():
        fail("Staged manifest.json missing")
    manifest = read_json(root / "manifest.json")
    if manifest.get("schema") != MANIFEST_SCHEMA or manifest.get("dataset") != DATASET:
        fail("Unexpected manifest schema or dataset")
    if manifest.get("chapters_imported") != EXPECTED_CHAPTERS:
        fail("Manifest must list all 1,189 chapters")
    if manifest.get("original_language_words_imported") != expected_words:
        fail("Manifest word count differs from the verified original import")
    if manifest.get("status") != "STAGED_SOURCE_DATA_NOT_READER_CONNECTED":
        fail("Unexpected source staging status")

    book_catalog = read_json(catalog)
    if book_catalog.get("edition_id") != "BSB":
        fail("Not the BSB local catalog")
    books = book_catalog.get("books")
    if not isinstance(books, list) or len(books) != EXPECTED_BOOKS:
        fail("Local catalog does not list exactly 66 books")
    chapters_by_book = {}
    for book in books:
        code, count = book.get("code"), book.get("chapter_count")
        if not re.fullmatch(r"[A-Z0-9]{3}", str(code)) or type(count) is not int or count < 1:
            fail("Invalid canonical BSB book/catalog chapter count")
        if code in chapters_by_book:
            fail("Duplicate book in canonical BSB catalog")
        chapters_by_book[code] = count
    if sum(chapters_by_book.values()) != EXPECTED_CHAPTERS:
        fail("Unexpected canonical book/chapter structure")

    entries = manifest.get("files")
    if not isinstance(entries, list) or len(entries) != EXPECTED_CHAPTERS:
        fail("Missing or surplus manifest chapter entries")
    expected_paths = {f"chapters/{book}/{ch:02d}.json"
                      for book, count in chapters_by_book.items()
                      for ch in range(1, count+1)}
    listed_paths = set()
    total_words = 0
    total_verses = 0
    for entry in entries:
        if not isinstance(entry, dict):
            fail("Invalid manifest entry")
        relative = entry.get("path")
        if not isinstance(relative, str) or relative not in expected_paths:
            fail(f"Unexpected chapter entry path: {relative}")
        if relative in listed_paths:
            fail(f"Duplicate chapter in manifest: {relative}")
        listed_paths.add(relative)
        match = FILE_RE.fullmatch(relative)
        if not match:
            fail(f"Malformed chapter path: {relative}")
        code, chapter_num = match.group(1), int(match.group(2))
        chapter_path = root / relative
        if not chapter_path.is_file() or chapter_path.is_symlink():
            fail(f"Chapter not a regular JSON file: {relative}")
        payload = chapter_path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != entry.get("sha256"):
            fail(f"Chapter SHA-256 mismatch: {relative}")
        chapter = json.loads(payload)
        if chapter.get("schema") != CHAPTER_SCHEMA or chapter.get("edition_id") != "BSB":
            fail(f"Unexpected chapter schema or edition: {relative}")
        if chapter.get("book_code") != code or chapter.get("chapter") != chapter_num:
            fail(f"Chapter identity mismatch: {relative}")
        src = chapter.get("source", {})
        if (src.get("dataset") != DATASET or src.get("provider") != "HelloAO Free Use Bible API"
                or src.get("publisher") != "Berean Bible"
                or src.get("url") != SOURCE_ROOT + f"{code}/{chapter_num}.json"
                or not re.fullmatch(r"[0-9a-f]{64}", str(src.get("response_sha256")))):
            fail(f"Unacceptable source provenance: {relative}")
        verses = chapter.get("verses")
        if not isinstance(verses, list) or not verses:
            fail(f"Missing verses in {relative}")
        verse_ids = set()
        chapter_words = 0
        for verse in verses:
            v = verse.get("verse")
            if type(v) is not int or v < 1 or v > 200 or v in verse_ids:
                fail(f"Invalid/duplicate verse in {relative}")
            if verse.get("id") != f"{code}.{chapter_num}.{v}":
                fail(f"Verse identity mismatch in {relative}")
            verse_ids.add(v)
            words = verse.get("words")
            if not isinstance(words, list) or not all(isinstance(w, dict) for w in words):
                fail(f"Invalid native word structure in {relative}")
            chapter_words += len(words)
        if chapter_words != entry.get("words"):
            fail(f"Original-language word count mismatch: {relative}")
        total_words += chapter_words
        total_verses += len(verses)
    if listed_paths != expected_paths:
        fail("Manifest omits canonical BSB chapters")
    actual_paths = {path.relative_to(root).as_posix()
                    for path in (root / "chapters").rglob("*.json")}
    if actual_paths != expected_paths:
        fail(f"Unlisted or missing on-disk chapter files: {len(actual_paths)} found")
    if total_words != expected_words:
        fail(f"Incorrect total original-language words: {total_words}")
    all_files = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    extra = all_files - expected_paths - {"manifest.json", "source.json"}
    if extra:
        fail(f"Unexpected files in source artifact: {sorted(extra)[:4]}")
    return {
        "status": "PASS_SOURCE_PUBLISH_CHECKS",
        "edition": "BSB", "provider": "HelloAO Free Use Bible API",
        "books": len(chapters_by_book), "chapters": len(listed_paths),
        "verses": total_verses, "original_language_words": total_words,
        "sha256_verified_chapters": len(listed_paths),
        "note": "Original-language association source only, NOT independently verified English-token offsets."
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-dir", required=True, type=Path)
    p.add_argument("--bsb-book-catalog", required=True, type=Path)
    a = p.parse_args(argv)
    try:
        print(json.dumps(verify(a.source_dir, a.bsb_book_catalog), indent=2, sort_keys=True))
    except (ValueError, TypeError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(f"BSB SOURCE PUBLICATION BLOCKED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
