# HelloAO Berean interlinear import for SOTW

## Purpose

Import **Berean's existing BSB original-language associations** from the HelloAO Free Use Bible API and pair their Strong's IDs with SOTW's existing dictionaries. This is not an alignment generator. No STEPBible definitions are fetched.

**Source repository:** `SOTW-BSB/-bsb-resources`. The script belongs at `scripts/import_helloao_bsb_interlinear.py`. Its source data belongs under `data/bsb/helloao-interlinear/v1/`. The existing publisher-verified three-verse pilot at `data/bsb/word-alignment/v1/` is left unchanged.

## API (GET, not POST)

- Book catalog: `https://bible.helloao.org/api/d/bsb-interlinear/books.json`
- Example chapter: `https://bible.helloao.org/api/d/bsb-interlinear/JHN/3.json`
- All chapter paths: `/api/d/bsb-interlinear/{BOOK}/{CHAPTER}.json` for the 66 books and 1,189 chapters.
- Publisher rights: https://berean.bible/terms.htm (public domain)
- API format: https://bible.helloao.org/docs/reference/datasets/#interlinear-datasets

Each verse's original HelloAO word objects are preserved verbatim in `words`, including `pos`, `bsbPos`, `language`, `text`, `transliteration`, `parsing`, `parsingFull`, `strongs`, and `gloss`. HelloAO's `gloss` gives Berean's English translation phrase; `bsbPos` gives its ordering, **not an absolute English token offset**. The importer does not invent token positions, substitute KJV mappings, or reinterpret Berean's phrases.

## Run (requires Python 3 and internet)

From repository root:

```bash
python3 scripts/import_helloao_bsb_interlinear.py --book JHN --chapter 3
python3 scripts/import_helloao_bsb_interlinear.py --book GEN
python3 scripts/import_helloao_bsb_interlinear.py --all
```

If source data is already in `data/bsb/helloao-interlinear/v1/`, it is preserved by default. `--replace` explicitly refreshes only those HelloAO cache files. The importer updates only its own `manifest.json`. It never writes to the published pilot, existing Bible verses, original-language v1, dictionary, or mobile-reader code.

### GitHub Actions (no automatic publishing)

Under **Actions → Import HelloAO BSB interlinear (manual)**, choose `one_chapter`, `one_book`, or `all_books`. The job downloads via API, builds the sidecars, and uploads a downloadable `helloao-bsb-interlinear-source` artifact. It does **not** commit files, modify the reader, or deploy. A separate owner-authorized review/installation step is needed to publish the artifact as SOTW data.

## Existing SOTW dictionaries (linked, not recopied)

- Original languages route map: https://github.com/SOTW-Original-Languages/original-language-resources/blob/main/study-data/v1/route-map.json
- Strong's lexicon shards: `study-data/v1/lexicon/{H_OR_G}/{H_OR_G}{FIRST_5DIGITS}-{LAST_5DIGITS}.json` in the SOTW Original Languages Part 1 repository, as described by that route map. The `strongs` value (`H7225`, `G3439`) is the join key. Continue using SOTW's existing James Strong definitions, not HelloAO's separate STEPBible lexicon.
- English dictionary: https://github.com/SOTW-Original-Languages/original-language-resources/blob/main/webster1828.json for separately tapped English headwords. Its digital transcription uses CC BY-SA 4.0 and already has a license file at repo root.
- Current BSB displayed English text: `data/bsb/{slug}/chapters/{NN}.json` in this BSB repository, unchanged.

**Status:** This is a source-data importer only. It does not make the new material appear in the Word-by-Word reader by itself. The existing three-verse pilot and mobile-reader behavior remain untouched until a separately authorized integration.
