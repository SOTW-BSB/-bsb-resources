# BSB foundation release validation | 2026-11-11

- Source ZIP SHA-256: `f0c56438eb89c98e8f62c5c00461e25cc35b098ad5b179bc350cede759ee5f87`.
- Source ZIP test: PASS; 66 USFM book files, one source folder.
- Canon: 66 books / 1,189 chapters / **31,086** publisher-supplied numbered main-text verses.
- **16 deliberately non-numbered traditional verse positions:** MAT.17.21, MAT.18.11, MAT.23.14, MRK.7.16, MRK.9.44, MRK.9.46, MRK.11.26, MRK.15.28, LUK.17.36, LUK.23.17, JHN.5.4, ACT.8.37, ACT.15.34, ACT.24.7, ACT.28.29, ROM.16.24.
- Exact source book/chapter/verse marker identities cross-checked against every chapter JSON record. No artificial placeholder verses generated.
- Original USFM notes: 4,854 source note blocks archived in separate `source-footnotes.json` data; not shown in reader. Section-heading lines: 3,268 archived in `chapter-extras.json` and not shown.
- Preserve verse text and punctuation; normalize whitespace, strip structural USFM tokens and exclude notes/crossrefs/headings. \wj/\wj* words of Christ appear as ordinary verse text, not externally linked red-letter data.
- All chapter JSON records are ASV/KJV/Webster-compatible source verse arrays, with `BSB:GEN.1.1` edition IDs.
- No embedded Strong’s or commentary. Edition-specific footnote variants are not treated as authoritative main-text verses.
- All 1,797 repository files plus each nested upload ZIP checked for file name, byte content and hash.
- No independent browser deployment check or collation with printed third edition performed.
