# Manual GitHub installation | Berean Standard Bible

## New independent foundation

- GitHub organization: `SOTW-BSB`
- Repository: `bsb-resources` (public)
- Repo description: `Public-domain Berean Standard Bible, with book, chapter, and verse resources for the Servants of the Way Digital Library.`
- Initial repository: empty, `main` branch when the first pack is committed; do not add a new README, gitignore or license.

## Upload exactly as in the KJV/Webster foundations

1. Extract the outer kit ZIP. Extract **`UPLOAD_PART_01_of_19.zip`** to a folder.
2. At the repository's root, choose **uploading an existing file**, or later **Add file → Upload files**.
3. Drag/select the **contents** of that extracted pack, not the outer folder, ZIP or any `UPLOAD_PLAN.json`. Preserve **`data/bsb`**, not `bsb` at root.
4. Inspect the pending file list; commit to `main`. Continue in order through all 19 packs.
5. Each ZIP has at most 95 repository files, each file below GitHub's 25 MiB browser-upload limit. GitHub does not unpack ZIP files.
6. Final expected root file count: **1,797**, with **1,189** files matching `data/bsb/{slug}/chapters/NN.json` and 66 book readers.
7. `RELEASE_MANIFEST.json` contains SHA-256 hashes for each file; the outer upload kit's `UPLOAD_PLAN.json` records the expected members and pack SHA-256 hashes. `UPLOAD_PLAN.json` is NOT a repository file.

## Publish the website after all files are uploaded

In repository `Settings → Pages`, set **Deploy from a branch**, `main`, `/(root)`, Save. Expected website: https://sotw-bsb.github.io/bsb-resources/ . Test Genesis 1, Psalm 23, Matthew 1, John 3, Romans 10 and Revelation 22. Check `#GEN.1.1` and chapter navigation.

No repository write, GitHub Pages deployment, or live browser test has been performed by this release kit.
