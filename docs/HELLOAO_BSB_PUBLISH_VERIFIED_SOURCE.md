# Publish verified complete HelloAO BSB interlinear source

This workflow reuses the **completed** 66-book HelloAO import, not a new API download.

Successful source run: https://github.com/SOTW-BSB/-bsb-resources/actions/runs/44344550874

Artifact ID: 14445777054 (helloao-bsb-interlinear-source). Verified GitHub ZIP digest:
sha256:69c96f463ecc22da68946039979f9d66210703409269c8921527f087518bf4d1

From https://github.com/SOTW-BSB/-bsb-resources/actions/workflows/helloao-bsb-interlinear-import.yml select **Run workflow**, branch **main**, and mode **publish_interlinear**. Scope/book/chapter inputs are ignored in publish mode. Staging remains available with mode stage_api and the previous scope controls.

Publication verifies the exact source run, artifact ID, artifact digest and expiry, then hashes and checks all 1,189 chapters (66 canonical BSB books) and all 443,625 original-language word objects against the existing SOTW BSB book catalog. It refuses incomplete, modified, unrecognized or previously published source data, and refuses unsafe overwrites.

On passing those checks, it commits only data/bsb/helloao-interlinear/v1/chapters/, its manifest.json and the source.json status to the existing SOTW-BSB/-bsb-resources repository.

**This is published source, NOT live reader integration.** Never modify the accepted data/bsb/word-alignment/v1 pilot, Bible verses, dictionaries, SOTW UI, or CGBC player during this step. Keep HelloAO source gloss, Strong's, parsing and bsbPos as supplied. bsbPos is not a verified English word token offset.

The source artifact expires December 18, 2026. If expired or unavailable, run stage_api/all_books again, then deliberately re-pin the replacement artifact and digest. No silent fallback or full-corpus re-import occurs in publish mode.

GitHub push must be fast-forward and is never forced. Owner should inspect GitHub Actions PASS and main/data/bsb/helloao-interlinear/v1/manifest.json to confirm actual publication. Retain publisher terms: https://berean.bible/terms.htm and source documentation docs/HELLOAO_BSB_INTERLINEAR_IMPORT.md.


## November 18, 2026: publish extraction collision fixed

The first `publish_interlinear` run failed while unpacking `source.json` over the existing checked-in `data/bsb/helloao-interlinear/v1/source.json`. The source import itself was successful and no interlinear chapters were committed by that failed run. The workflow now downloads the pinned artifact into a separate `$RUNNER_TEMP/bsb-helloao-artifact` directory, verifies all 1,189 source chapters **there**, then copies only verified `chapters/` and `manifest.json` to the repository. The existing `source.json` is retained and its publication status is updated after verification. Existing word-alignment pilot, dictionaries and readers remain untouched.

Original failed run: https://github.com/SOTW-BSB/-bsb-resources/actions/runs/44355971873
