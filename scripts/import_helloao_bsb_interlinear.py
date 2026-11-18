#!/usr/bin/env python3
"""Import publisher-authored HelloAO BSB interlinear rows; do not derive new alignments.

This produces separate SOTW source sidecars, not player-ready English token spans.
The accepted data/bsb/word-alignment/v1 pilot remains untouched.
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://bible.helloao.org"
DATASET = "bsb-interlinear"
REPO = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO / "data/bsb/helloao-interlinear/v1"


def get_json(api_path):
    url = BASE + api_path
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "SOTW-BSB-Interlinear-Import/1.0"})
    for attempt in range(3):
        try:
            with urlopen(req, timeout=35) as response:
                body = response.read()
            return json.loads(body), hashlib.sha256(body).hexdigest(), url
        except (URLError, HTTPError, TimeoutError, ValueError) as exc:
            if attempt == 2:
                raise RuntimeError(f"Cannot retrieve {url}: {exc}") from exc
            time.sleep(2 ** attempt)
    raise AssertionError("Unreachable")


def build_sidecar(book, chapter, payload, source_hash, url):
    if payload.get("dataset", {}).get("id") != DATASET:
        raise ValueError(f"Incorrect dataset returned for {book} {chapter}")
    if payload.get("book", {}).get("id") != book:
        raise ValueError(f"Incorrect book returned for {book} {chapter}")
    chapter_data = payload.get("chapter", {})
    if chapter_data.get("number") != chapter:
        raise ValueError(f"Incorrect chapter returned for {book} {chapter}")
    content = chapter_data.get("content")
    if not isinstance(content, list):
        raise ValueError("API chapter has no verse list")
    verses = []
    seen = set()
    for entry in content:
        number = entry.get("verse")
        words = entry.get("words")
        if not isinstance(number, int) or number < 1 or number in seen:
            raise ValueError(f"Invalid or duplicate verse number in {book} {chapter}")
        if not isinstance(words, list) or not all(isinstance(w, dict) for w in words):
            raise ValueError(f"Missing interlinear words in {book}.{chapter}.{number}")
        seen.add(number)
        # Preserve HelloAO's native pos, bsbPos, gloss, morphology and Strong's.
        # Do not recalculate, reposition, or use STEPBible definitions.
        verses.append({"id": f"{book}.{chapter}.{number}", "verse": number, "words": words})
    return {
        "schema": "sotw-bsb-helloao-interlinear-source/1.0.0",
        "status": "STAGED_SOURCE_DATA_NOT_READER_CONNECTED",
        "edition_id": "BSB",
        "book_code": book,
        "chapter": chapter,
        "source": {
            "provider": "HelloAO Free Use Bible API",
            "publisher": "Berean Bible",
            "dataset": DATASET,
            "url": url,
            "response_sha256": source_hash,
            "rights_url": "https://berean.bible/terms.htm"
        },
        "verses": verses
    }


def save_json(path, data, replace):
    if path.exists() and not replace:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(encoded)
    temporary.replace(path)
    return True


def refresh_manifest(root):
    chapter_files = sorted(root.glob("chapters/*/[0-9][0-9]*.json"))
    entries = []
    words = 0
    for file in chapter_files:
        raw = file.read_bytes()
        chapter = json.loads(raw)
        count = sum(len(v["words"]) for v in chapter["verses"])
        words += count
        entries.append({"path": file.relative_to(root).as_posix(), "sha256": hashlib.sha256(raw).hexdigest(), "words": count})
    manifest = {
        "schema": "sotw-bsb-helloao-interlinear-source-manifest/1.0.0",
        "status": "STAGED_SOURCE_DATA_NOT_READER_CONNECTED",
        "provider": "HelloAO Free Use Bible API",
        "dataset": DATASET,
        "rights": "https://berean.bible/terms.htm",
        "chapters_imported": len(entries),
        "original_language_words_imported": words,
        "files": entries,
        "lexicon_reference": {
            "route_map": "https://raw.githubusercontent.com/SOTW-Original-Languages/original-language-resources/main/study-data/v1/route-map.json",
            "dictionary_policy": "SOTW existing Strong's entries only; do not fetch stepbible-lexicon"
        },
        "english_dictionary_reference": {
            "url": "https://raw.githubusercontent.com/SOTW-Original-Languages/original-language-resources/main/webster1828.json",
            "license": "CC BY-SA 4.0",
            "lookup": "separate exact English headword lookup; not a source of original-language alignment"
        },
        "note": "HelloAO publisher gloss and bsbPos are preserved as supplied; bsbPos is not an English token offset. Does not modify published pilot."
    }
    save_json(root / "manifest.json", manifest, replace=True)
    return len(entries), words


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--book", metavar="CODE", help="HelloAO book code, e.g. JHN or GEN")
    group.add_argument("--all", action="store_true", help="Import all 66 books (1,189 chapters)")
    parser.add_argument("--chapter", type=int, help="Single chapter; requires --book")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--replace", action="store_true", help="Explicitly refresh existing HelloAO sidecars")
    args = parser.parse_args(argv)
    if args.chapter is not None and (args.all or args.chapter < 1):
        parser.error("--chapter requires --book and a positive number")
    book_list, _, _ = get_json(f"/api/d/{DATASET}/books.json")
    if book_list.get("dataset", {}).get("id") != DATASET:
        raise ValueError("Wrong dataset returned for books catalog")
    available = {b["id"]: b["numberOfChapters"] for b in book_list["books"]}
    if args.all:
        if len(available) != 66 or sum(available.values()) != 1189:
            raise ValueError("Unexpected HelloAO book/chapter catalog; stop instead of incomplete import")
        chosen = [(book, chapter) for book, n in available.items() for chapter in range(1, n + 1)]
    else:
        book = args.book.upper()
        if book not in available:
            parser.error(f"Unknown book {book}")
        if args.chapter is not None and args.chapter > available[book]:
            parser.error(f"Chapter {args.chapter} exceeds {book} chapter count")
        chapters = [args.chapter] if args.chapter else range(1, available[book] + 1)
        chosen = [(book, chapter) for chapter in chapters]
    made = skipped = 0
    root = args.output_dir
    for book, chapter in chosen:
        target = root / "chapters" / book / f"{chapter:02d}.json"
        if target.exists() and not args.replace:
            skipped += 1
            continue
        payload, digest, url = get_json(f"/api/d/{DATASET}/{book}/{chapter}.json")
        sidecar = build_sidecar(book, chapter, payload, digest, url)
        if save_json(target, sidecar, replace=args.replace):
            made += 1
            print(f"Imported {book} {chapter}: {len(sidecar['verses'])} verses")
        if args.all:
            time.sleep(0.10)
    count, words = refresh_manifest(root)
    print(f"New: {made}; existing preserved: {skipped}; staged chapters: {count}; original-language words: {words}")
    print("The existing pilot, reader, BSB text, and SOTW dictionaries were not changed.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as exc:
        print(f"IMPORT STOPPED: {exc}", file=sys.stderr)
        sys.exit(1)
