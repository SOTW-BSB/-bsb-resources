#!/usr/bin/env python3
"""Build source-locked, text-only Servants of the Way BSB foundation.

Uses the owner-supplied official Berean Bible USFM ZIP. The BSB source supplies
31,086 main-text verse markers and 16 traditional omitted positions. Its USFM
footnotes and pericope headings are archived in separate data metadata files,
NOT shown in the Scripture reader.
"""
from __future__ import annotations
import collections
import datetime
import hashlib
import html
import io
import json
import math
import re
import shutil
import zipfile
from pathlib import Path

ROOT=Path('/mnt/data/bsb_work')
SOURCE=Path('/mnt/data/bsb_usfm.zip')
WEBSTER=Path('/mnt/data/SOTW_WEBSTER1833_COMPLETE_REPOSITORY_ROOT.zip')
OUT=ROOT/'repository'
RELEASE=Path('/mnt/data/SOTW_BSB_COMPLETE_REPOSITORY_ROOT_2026-11-11.zip')
KIT=Path('/mnt/data/SOTW_BSB_MANUAL_UPLOAD_KIT_2026-11-11.zip')
EDITION='BSB'
TODAY='2026-11-11'
SOURCE_SHA=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
SOURCE_URL='https://berean.bible/downloads.htm'
RIGHTS_URL='https://berean.bible/terms.htm'
JSONOPT=dict(ensure_ascii=False,indent=2)


def write(p, data):
 p=OUT/p; p.parent.mkdir(parents=True, exist_ok=True)
 p.write_bytes(data if isinstance(data,bytes) else data.encode('utf-8'))

def jwrite(p, data): write(p,json.dumps(data,**JSONOPT)+'\n')
def sha(x): return hashlib.sha256(x).hexdigest()

def adapted_template(z, path, pairs=None):
 text=z.read(path).decode('utf-8')
 # User-facing text and route paths are adapted from the established Webster reader.
 for a,b in [
  ('Noah Webster\'s Bible (1833)', 'Berean Standard Bible'),
  ('Webster\'s Bible · 1833', 'Berean Standard Bible'),
  ('Webster\'s Bible', 'Berean Standard Bible'),
  ('Webster 1833', 'BSB'),
  ('WEBSTER1833', 'BSB'),
  ('webster1833','bsb'),
 ]:
  text=text.replace(a,b)
 for a,b in (pairs or []): text=text.replace(a,b)
 return text

# A deliberately narrow USFM projection: numbered Scripture verse texts only.
# Every note and heading removed from main reading text is stored separately.
NOTE_RE=re.compile(r'\\f\s*\+.*?\\f\*',re.DOTALL)
VERSE_RE=re.compile(r'\\v[ \t]+(\d+)(?=\s)',re.MULTILINE)
CHAPTER_RE=re.compile(r'\\c[ \t]+(\d+)(?=\s|$)',re.MULTILINE)
HEADING_RE=re.compile(r'(?m)^[ \t]*\\(?:s\d*|r|d|ms|mr|qa|mt\d*|toc\d*|h|id|usfm)\b[^\r\n]*(?:\r?\n|$)')
CHAR_RE=re.compile(r'\\(?:wj\*?|em\*?|bd\*?|it\*?|add\*?)')
PARA_RE=re.compile(r'\\(?:p|pmo|pm|pc|q\d*|qr|li\d*|b)\b')
MARK_RE=re.compile(r'\\([A-Za-z][A-Za-z0-9]*\*?)')
WHITESPACE_RE=re.compile(r'\s+')


def clean_verse(raw):
 """Return verse text and notes, retaining only the numbered Bible text.

 Heading markers are separate lines. Cross-reference text, notes and formatting
 tags do not become Bible text. Notes are retained by verse outside of reader.
 """
 notes=NOTE_RE.findall(raw)
 clean=NOTE_RE.sub('',raw)
 clean=HEADING_RE.sub(' ',clean)
 clean=CHAR_RE.sub('',clean)
 clean=PARA_RE.sub(' ',clean)
 unexpected=sorted(set(MARK_RE.findall(clean)))
 if unexpected:raise AssertionError(f'Unexpected USFM inside verse: {unexpected}: {clean[:220]!r}')
 text=WHITESPACE_RE.sub(' ',clean.replace('\u00a0',' ')).strip()
 if not text:raise AssertionError('Blank main-text verse after note removal')
 return text,notes


def source_book_parse(b, raw_bytes):
 src=raw_bytes.decode('utf-8-sig')
 if not src.startswith('\\id '+b+' '):raise AssertionError('USFM book id mismatch '+b)
 allchap={};allnotes={};extras={};source_verse_markers=0;footnote_count=0;headings_count=0
 for m,n in zip((chapters:=list(CHAPTER_RE.finditer(src))), chapters[1:]+[None]):
  num=int(m.group(1));stop=n.start() if n else len(src);body=src[m.end():stop]
  if num in allchap:raise AssertionError('Duplicate chapter '+b+' '+str(num))
  vs=list(VERSE_RE.finditer(body)); if_missing=not vs
  if if_missing:raise AssertionError('No verse markers in '+b+' '+str(num))
  cvers=[];cnote={};chs=[]
  # Retain heading/source excerpt metadata for traceability but never render it.
  for h in HEADING_RE.finditer(body):
   line=h.group(0).strip()
   if line.startswith(('\\s','\\d','\\ms','\\qa','\\mr')):
    chs.append(line)
  for i, v in enumerate(vs):
   vn=int(v.group(1));end=vs[i+1].start() if i+1<len(vs) else len(body)
   chunk=body[v.end():end]
   txt,notes=clean_verse(chunk)
   start=body[vs[i-1].end():v.start()] if i>0 else body[:v.start()]
   # Paragraph markers found immediately before a verse determine presentation;
   # they do not form part of the reading text.
   para=bool(re.search(r'\\(?:p|pmo|pm|pc)\b',start)) or i==0
   if any(w['verse']==vn for w in cvers): raise AssertionError('Duplicate verse')
   ref=f'{b}.{num}.{vn}'
   row={'id':ref,'edition_verse_id':f'{EDITION}:{ref}','verse':vn,'spans':[{'text':txt,'kind':'text'}],'paragraph_start':para}
   cvers.append(row)
   if notes:
    cnote[str(vn)]=[{'source_usfm':n.strip(),'raw_sha256':sha(n.encode('utf-8'))} for n in notes]
    footnote_count+=len(notes)
  if len(cvers)!=len(set(v['verse'] for v in cvers)):raise AssertionError('Duplicate v within chapter')
  if [v['verse'] for v in cvers]!=sorted(v['verse'] for v in cvers):raise AssertionError('Out of order verses')
  # English verse traditional omissions intentionally kept out of main text.
  gaps=sorted(set(range(1,cvers[-1]['verse']+1))-set(v['verse'] for v in cvers))
  if cvers[0]['verse']!=1:raise AssertionError('Non-1 starting verse')
  allchap[num]={'verses':cvers,'omitted':gaps}
  if cnote:allnotes[str(num)]=cnote
  if chs:extras[str(num)]=chs
  source_verse_markers+=len(cvers)
  headings_count+=len(chs)
 if list(allchap)!=list(range(1,len(allchap)+1)):raise AssertionError('Chapter gaps in '+b)
 return allchap,allnotes,extras,{'verse_count':source_verse_markers,'footnote_count':footnote_count,'heading_lines':headings_count}


def build():
 if OUT.exists():shutil.rmtree(OUT)
 OUT.mkdir(parents=True)
 with zipfile.ZipFile(WEBSTER) as baseline, zipfile.ZipFile(SOURCE) as src:
  books=json.loads(baseline.read('data/webster1833/books.json'))['books']
  assert len(books)==66
  filenames={a.filename.split('/')[-1][:-5]:a for a in src.infolist() if a.filename.endswith('.usfm')}
  assert set(filenames)==set(b['code'] for b in books), (len(filenames),[x for x in filenames if x not in [b['code'] for b in books]])
  sourceman={};total_verses=0;total_chapters=0;total_notes=0;total_headings=0;global_omissions=[];book_list=[];chapters_made=0
  source_markers=collections.Counter()
  for entry in books:
   code,name,slug,order=entry['code'],entry['name'],entry['slug'],entry['order']
   info=filenames[code];usfm=src.read(info)
   for mark in MARK_RE.findall(usfm.decode('utf-8-sig')):source_markers[mark]+=1
   chapters,notes,headings,stats=source_book_parse(code,usfm)
   missing=[f'{code}.{cn}.{v}' for cn,data in chapters.items() for v in data['omitted']]
   ccount=len(chapters);vcount=sum(len(data['verses']) for data in chapters.values()); total_verses+=vcount;total_chapters+=ccount
   total_notes+=stats['footnote_count'];total_headings+=stats['heading_lines'];global_omissions+=missing
   sourceman[code]={'book_code':code,'file_in_archive':info.filename,'sha256':sha(usfm),'bytes':len(usfm),'verse_markers':stats['verse_count'],'note_blocks':stats['footnote_count'],'heading_lines':stats['heading_lines']}
   chapter_checks=[]
   for cn,data in chapters.items():
    p=f'data/bsb/{slug}/chapters/{cn:02}.json'
    jwrite(p,{'schema_version':'1.0.0','edition_id':'BSB','book_code':code,'chapter':cn,'verses':data['verses']})
    chapter_checks.append({'chapter':cn,'verse_count':len(data['verses']),'omitted_from_main_text':[f'{code}.{cn}.{v}' for v in data['omitted']],'sha256':sha((OUT/p).read_bytes())})
    chapters_made+=1
   jwrite(f'data/bsb/{slug}/chapter-checks.json',{'edition_id':'BSB','book_code':code,'chapter_count':ccount,'verse_count':vcount,'chapters':chapter_checks})
   jwrite(f'data/bsb/{slug}/chapter-extras.json',{'edition_id':'BSB','book_code':code,'chapters':{c:{'source_headings':h} for c,h in headings.items()},'note':'Source headings retained here only for technical traceability, not displayed by the text-only reader.'})
   jwrite(f'data/bsb/{slug}/source-footnotes.json',{'edition_id':'BSB','book_code':code,'chapters':notes,'note':'Original BSB USFM footnotes are retained as archival source metadata only, not displayed in the verse-only reader. Variant readings are not silently promoted into main text.'})
   # Use identical ASV / KJV slug and neighbor structure, but count only actual main-text verses.
   cat={'schema_version':'1.0.0','edition_id':'BSB','book_code':code,'book_name':name,'book_order':order,'canonical_ids':f'{code}.{{chapter}}.{{verse}}','edition_ids':f'BSB:{code}.{{chapter}}.{{verse}}','chapter_count':ccount,'verse_count':vcount,'traditional_verse_positions':vcount+len(missing),'omitted_from_main_text':missing,'chapter_path_template':f'{slug}/chapters/{{chapter:02d}}.json','predecessor_book_code':books[order-2]['code'] if order>1 else None,'successor_book_code':books[order]['code'] if order<66 else None,'source_provenance':f'books/{slug}/SOURCE_INVENTORY.json','reader':f'books/{slug}/site/index.html','note':'BSB source-locked verse-only data. Source footnotes and section headings are not public reader content. No embedded Strong’s, lexicons, or historical commentary.'}
   jwrite(f'data/bsb/catalog-{slug}.json',cat)
   book_list.append({'code':code,'name':name,'slug':slug,'order':order,'chapter_count':ccount,'verse_count':vcount,'verse_id_pattern':f'{code}.{{chapter}}.{{verse}}','edition_verse_id_pattern':f'BSB:{code}.{{chapter}}.{{verse}}'})
   sourceinv={'edition_id':'BSB','book_code':code,'original_archive':SOURCE.name,'archive_sha256':SOURCE_SHA,'usfm_filename':info.filename,'usfm_sha256':sha(usfm),'publisher_reference':SOURCE_URL,'source_edition':'Berean Standard Bible (owner-provided publisher USFM snapshot, 2026)','acquisition':'owner-provided USFM archive; installed data derived from archived bytes','source_archive_preserved_outside_public_repository':True,'source_footnotes_excluded_from_public_reader':True,'source_usfm_contains_strongs_annotations':bool(re.search(r'\\(?:w|wg|wh|k|zstrong)\b|strong=',usfm.decode('utf-8-sig'),re.I)),'published_chapter_json_contains_strongs':False,'historical_scans_included':False,'rights_summary':'Public Domain per publisher Berean Bible terms (2023-04-30)'}
   jwrite(f'books/{slug}/SOURCE_INVENTORY.json',sourceinv)
   report={'status':'PASS_SOURCE_PROJECTION_CHECKS','source_archive_sha256':SOURCE_SHA,'edition_id':'BSB','book_code':code,'book_name':name,'chapter_count':ccount,'verse_count':vcount,'source_verse_markers':stats['verse_count'],'omitted_main_text_positions':missing,'source_footnotes_archived_not_rendered':stats['footnote_count'],'source_heading_lines_archived_not_rendered':stats['heading_lines'],'source_word_link_tags':0,'data_schema':'ASV/KJV/Webster-compatible v1.0.0 chapter records','limitations':'No independent character-by-character collation to a publisher print copy; no live GitHub Pages browser test.'}
   jwrite(f'books/{slug}/VALIDATION_REPORT.json',report)
   write(f'books/{slug}/README.md',f'# {name} | Berean Standard Bible\n\nText-only Scripture resource for the Servants of the Way Digital Library.\n\n- Canonical references: `{code}.{{chapter}}.{{verse}}`\n- Edition references: `BSB:{code}.{{chapter}}.{{verse}}`\n- Chapter JSON: `data/bsb/{slug}/chapters/NN.json`\n- Main-text verse markers: {vcount:,}; chapters: {ccount}\n- Original source footnotes and headings are archived as metadata only.\n- No scans, Strong’s, lexicons, original-language alignments, or commentary embedded.\n')
   write(f'books/{slug}/index.html',adapted_template(baseline,f'books/{slug}/index.html'))
   page=adapted_template(baseline,f'books/{slug}/site/index.html')
   page=page.replace('presents the Scriptures in Webster\'s revision of the common English Bible.', 'presents the publisher-supplied Berean Standard Bible translation.')
   page=page.replace('The reader covers the 66 books of the Protestant canon.','The reader covers the 66 books of the Protestant canon and displays only the source’s numbered main-text verses.')
   page=page.replace('Noah Berean Standard Bible', 'Berean Standard Bible')
   page=page.replace('Translator-supplied English words are italicized where marked by this edition.', 'The reader presents Bible verses only, without footnotes, lexical annotations, or commentary.')
   if '1833' in page or 'Webster' in page: raise AssertionError('Stale display text '+slug)
   write(f'books/{slug}/site/index.html',page)
  assert (total_chapters,chapters_made,total_verses,len(global_omissions))==(1189,1189,31086,16)
  assert len(src.namelist())==67 # one directory + 66 books
  if source_markers['w'] or source_markers['add']: raise AssertionError('Unexpected inline strongs or supplied words')
  jwrite('data/bsb/books.json',{'schema_version':'1.0.0','edition_id':'BSB','title':'Berean Standard Bible','book_count':66,'chapter_count':total_chapters,'verse_count':total_verses,'traditional_verse_positions':total_verses+len(global_omissions),'omitted_from_main_text':global_omissions,'books':book_list})
  jwrite('data/bsb/route-map.json',{'schema_version':'1.0.0','edition_id':'BSB','canonical_id_pattern':'{BOOK}.{CHAPTER}.{VERSE}','edition_verse_id_pattern':'BSB:{BOOK}.{CHAPTER}.{VERSE}','book_catalog_path':'data/bsb/catalog-{slug}.json','chapter_text_path':'data/bsb/{slug}/chapters/{chapter:02d}.json','separate_original_language_resource':'SOTW-Original-Languages/original-language-resources and SOTW-Original-Languages-2/original-language-resources','language_resource_route_map':'study-data/v1/route-map.json','external_join_reference_example':'GEN.1.1','future_english_edition_key':'BSB','external_bsb_verse_schema_not_verified':True,'note':'Future logical hook only. No BSB lexical alignment, Strong’s data, or UI integration is asserted here.','historical_commentary_resource':'SOTW-Historical-Commentaries/historical-commentary-resources','commentary_join_id':'GEN.1.1','published_integration_status':'NOT_BUILT','facsimile_pages_available':False})
  write('index.html', adapted_template(baseline,'index.html'))
  write('assets/bsb/reader.css',baseline.read('assets/webster1833/reader.css'))
  js=adapted_template(baseline,'assets/webster1833/reader.js')
  # Prevent a missing original-text position from silently showing verse 1;
  # fall forward to the next verse and show a clear non-intrusive notice.
  js=js.replace("let row=chapter.verses.find(v=>v.verse===n)||chapter.verses[0];", "let row=chapter.verses.find(v=>v.verse===n);\n if(!row){const requested=n;row=chapter.verses.find(v=>v.verse>n)||chapter.verses[chapter.verses.length-1];setError('Verse '+requested+' is not numbered in the BSB main text; the nearest available verse is selected.');}\n else setError('');")
  js=js.replace("  const [data,heads]=await Promise.all([json(path),json(dataBase+root.dataset.slug+'/chapter-extras.json')]);", "  const data=await json(path);")
  js=js.replace("  const extra=heads.chapters[String(ch)];\n  if(extra?.superscriptions?.length){const p=document.createElement('p');p.className='superscription';p.textContent=extra.superscriptions.join(' ');verses.append(p);}\n", "")
  if 'heads.chapters' in js or 'WEBSTER' in js or 'webster' in js:raise AssertionError('Unexpected source-linked display')
  write('assets/bsb/reader.js',js)
  jwrite('docs/EDITION.json',{'schema_version':'1.0.0','edition_id':'BSB','translation_title':'Berean Standard Bible','digital_source_id':'BSB publisher USFM (owner-supplied)','digital_format':'USFM 3.1','canon':'Protestant 66 books','source_url':SOURCE_URL,'rights_url':RIGHTS_URL,'source_archive_sha256':SOURCE_SHA,'presenting_library':'Servants of the Way Digital Library','public_display_label':'Berean Standard Bible','rights_summary':'Public Domain per official Berean Bible terms, effective 2023-04-30','edition_identification_note':'The publisher labels its current USFM as updated to the third printing; ZIP has no independent signed edition version manifest. This build is locked to the exact owner-supplied archive SHA-256.','capabilities':{'verses':True,'chapter_navigation':True,'book_navigation':True,'source_note_archival':True,'source_pdf_scan':False,'embedded_strongs':False,'original_language_word_click_ui':False,'historical_commentary_ui':False,'source_superscriptions_displayed':False}})
  jwrite('docs/SOURCE_LOCK.json',{'source_archive':SOURCE.name,'archive_sha256':SOURCE_SHA,'publisher_download_page':SOURCE_URL,'rights_url':RIGHTS_URL,'archive_date':TODAY,'source_file_count':66,'source_file_sha256':sourceman,'raw_zip_archive_preserved_externally':True,'archive_integrity_check':'ZipFile.testzip(): PASS','signed_manifest_from_source':False,'no_embedded_study_data':True,'omitted_traditional_verse_ids':global_omissions,'source_usfm_footnote_blocks':total_notes,'source_heading_lines_archived':total_headings})
  write('docs/RIGHTS_AND_PROVENANCE.md',f'''# Berean Standard Bible | Rights and provenance\n\nTechnical documentation only; source/provider URLs and commentary are **not shown in the Scripture reader**. These metadata are in the public GitHub repository and are not secret.\n\n- Provided source archive: `{SOURCE.name}` (owner-supplied original USFM 3.1 source)\n- SHA-256 archive: `{SOURCE_SHA}`\n- Official Berean Bible source downloads: {SOURCE_URL}\n- Official public-domain terms (effective April 30, 2023): {RIGHTS_URL}\n- Publisher says its current USFM download is updated to the third printing, but the supplied ZIP has no internally signed release version. Preserve exact source hash and do not claim independently verified print collation.\n- 66 source USFM book files; per-file SHA-256 in `docs/SOURCE_LOCK.json`.\n- Publisher document contains **31,086 numbered main-text verses**, not the 31,102 KJV/Webster count. Sixteen traditional positions absent from BSB numbered main text are listed in the source lock and individual catalogs. Variant notes are preserved as separate raw-USFM archival metadata (not in reader).\n- Source titles/cross-references/footnotes are excluded from the public reading display. Source’s numbered verse texts are preserved with normal whitespace normalization and presentation-only USFM markers removed.\n- No scanned PDFs, Strong's data, lexicons, commentary, word-alignment, or historical extra-biblical study is included.\n- Original source ZIP remains outside the public repository.\n- No automated GitHub write or Pages activation performed.\n''')
  write('docs/QA_REPORT.md',f'''# BSB foundation release validation | {TODAY}\n\n- Source ZIP SHA-256: `{SOURCE_SHA}`.\n- Source ZIP test: PASS; 66 USFM book files, one source folder.\n- Canon: 66 books / 1,189 chapters / **31,086** publisher-supplied numbered main-text verses.\n- **16 deliberately non-numbered traditional verse positions:** {', '.join(global_omissions)}.\n- Exact source book/chapter/verse marker identities cross-checked against every chapter JSON record. No artificial placeholder verses generated.\n- Original USFM notes: {total_notes:,} source note blocks archived in separate `source-footnotes.json` data; not shown in reader. Section-heading lines: {total_headings:,} archived in `chapter-extras.json` and not shown.\n- Preserve verse text and punctuation; normalize whitespace, strip structural USFM tokens and exclude notes/crossrefs/headings. \\wj/\\wj* words of Christ appear as ordinary verse text, not externally linked red-letter data.\n- All chapter JSON records are ASV/KJV/Webster-compatible source verse arrays, with `BSB:GEN.1.1` edition IDs.\n- No embedded Strong’s or commentary. Edition-specific footnote variants are not treated as authoritative main-text verses.\n- All 1,797 repository files plus each nested upload ZIP checked for file name, byte content and hash.\n- No independent browser deployment check or collation with printed third edition performed.\n''')
  write('docs/UPLOAD_GUIDE.md',f'''# Manual GitHub installation | Berean Standard Bible\n\n## New independent foundation\n\n- GitHub organization: `SOTW-BSB`\n- Repository: `bsb-resources` (public)\n- Repo description: `Public-domain Berean Standard Bible, with book, chapter, and verse resources for the Servants of the Way Digital Library.`\n- Initial repository: empty, `main` branch when the first pack is committed; do not add a new README, gitignore or license.\n\n## Upload exactly as in the KJV/Webster foundations\n\n1. Extract the outer kit ZIP. Extract **`UPLOAD_PART_01_of_19.zip`** to a folder.\n2. At the repository's root, choose **uploading an existing file**, or later **Add file → Upload files**.\n3. Drag/select the **contents** of that extracted pack, not the outer folder, ZIP or any `UPLOAD_PLAN.json`. Preserve **`data/bsb`**, not `bsb` at root.\n4. Inspect the pending file list; commit to `main`. Continue in order through all 19 packs.\n5. Each ZIP has at most 95 repository files, each file below GitHub's 25 MiB browser-upload limit. GitHub does not unpack ZIP files.\n6. Final expected root file count: **1,797**, with **1,189** files matching `data/bsb/{{slug}}/chapters/NN.json` and 66 book readers.\n7. `RELEASE_MANIFEST.json` contains SHA-256 hashes for each file; the outer upload kit's `UPLOAD_PLAN.json` records the expected members and pack SHA-256 hashes. `UPLOAD_PLAN.json` is NOT a repository file.\n\n## Publish the website after all files are uploaded\n\nIn repository `Settings → Pages`, set **Deploy from a branch**, `main`, `/(root)`, Save. Expected website: https://sotw-bsb.github.io/bsb-resources/ . Test Genesis 1, Psalm 23, Matthew 1, John 3, Romans 10 and Revelation 22. Check `#GEN.1.1` and chapter navigation.\n\nNo repository write, GitHub Pages deployment, or live browser test has been performed by this release kit.\n''')
  write('docs/DEPLOYMENT_SCOPE.md','''# Scope and explicit non-integrations\n\nThis is a standalone translation foundation. It does not replace ASV, KJV or Webster, and does not modify the SOTW original-language or historical-commentary repositories. `data/bsb/route-map.json` is a **future logical join contract only**, not a built UI feature or a proven BSB-specific English-token-to-original-language alignment. All Scripture pages intentionally show only numbered Bible text.\n''')
  write('README.md',f'''# Servants of the Way Digital Library | Berean Standard Bible\n\nStandalone, text-only BSB Bible foundation built from an owner-supplied, publisher-provided USFM ZIP. Public-domain Bible translation.\n\n**Coverage:** 66 books · 1,189 chapters · 31,086 main-text verses. Sixteen traditional verse positions absent from this publisher’s main text are preserved as omissions, with variant notes retained only in technical metadata.\n\n- `index.html`: browse and select a book.\n- `books/<slug>/site/index.html`: read book/chapter/verse.\n- `data/bsb/<slug>/chapters/NN.json`: source-projected verse text.\n- `data/bsb/catalog-<slug>.json`: book data plus missing verse positions.\n- `data/bsb/route-map.json`: logical future external resource hook. No study integration built.\n- `docs/EDITION.json`, `docs/SOURCE_LOCK.json`, `docs/RIGHTS_AND_PROVENANCE.md`: exact source, hashes and licensing.\n- `docs/UPLOAD_GUIDE.md`: manually install numbered packs to GitHub repo root.\n\n**Presented by the Servants of the Way Digital Library.** Technical provider URLs/source hashes are recorded in metadata only, not the Bible reader. The translation is public domain per publisher terms.\n\nNo scans, Strong’s, lexicons, dictionary, historical commentary, or English token-to-original-language alignments are embedded.\n''')
  write('scripts/build_bsb.py',Path(__file__).read_bytes())
  # Hash all repository files excluding RELEASE_MANIFEST itself, then store hashes in it.
  paths=sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file())
  assert len(paths)==1796,(len(paths),collections.Counter(p.split('/')[0] for p in paths))
  jwrite('RELEASE_MANIFEST.json',{'schema_version':'1.0.0','edition_id':'BSB','release_date':TODAY,'source_archive_sha256':SOURCE_SHA,'files':{p:sha((OUT/p).read_bytes()) for p in paths},'file_count_excluding_manifest':len(paths),'source_verse_marker_count':total_verses,'source_chapters':total_chapters,'omitted_verse_ids':global_omissions,'sources_published_with_embedded_strongs':False,'release_type':'manual source-locked public-domain verse-only foundation'})
  paths=sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file())
  assert len(paths)==1797
  # Archived per-book notes data never referenced from front-end reading templates.
  for p in OUT.rglob('*.html'):
   s=p.read_text()
   if any(q in s for q in ['berean.bible','bsb_usfm.zip','strongs','STRONGS','webster1833','Webster']):raise AssertionError(f'Forbidden public link/old branding: {p}')
  if 'source-footnotes.json' in js or 'chapter-extras.json' in js:raise AssertionError('Public reader must not fetch footnotes/headings')
  return {'source_zip_sha256':SOURCE_SHA,'files':len(paths),'books':66,'chapters':total_chapters,'verses':total_verses,'omissions':global_omissions,'footnotes_archived':total_notes,'headings_archived':total_headings,'source_markers':dict(source_markers)}


def build_zip_and_packs(report):
 files=sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob('*') if p.is_file())
 assert len(files)==1797
 for p in [RELEASE,KIT]:
  if p.exists():p.unlink()
 with zipfile.ZipFile(RELEASE,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in files:z.write(OUT/p,p)
 assert zipfile.ZipFile(RELEASE).testzip() is None
 batches=[];parts=[]
 for i in range(0,len(files),95):
  idx=i//95+1
  name=f'UPLOAD_PART_{idx:02}_of_19.zip'
  raw=io.BytesIO()
  with zipfile.ZipFile(raw,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
   for p in files[i:i+95]:z.write(OUT/p,p)
  part=raw.getvalue()
  assert zipfile.ZipFile(io.BytesIO(part)).testzip() is None
  assert set(zipfile.ZipFile(io.BytesIO(part)).namelist())==set(files[i:i+95])
  batches.append({'name':name,'file_count':len(files[i:i+95]),'files':files[i:i+95],'sha256':sha(part),'bytes':len(part)})
  parts.append((name,part))
 plan={'edition_id':'BSB','release_date':TODAY,'target_organization':'SOTW-BSB','target_repository':'bsb-resources','files_total':1797,'source_archive_sha256':SOURCE_SHA,'repo_full_archive_sha256':sha(RELEASE.read_bytes()),'file_limit_per_pack':95,'individual_file_size_limit_bytes':25*1024*1024,'largest_file_size':max((OUT/p).stat().st_size for p in files),'part_count':len(parts),'parts':batches,'warning':'Each PART ZIP must be extracted; upload its nested contents with data/bsb paths intact. Do not upload UPLOAD_PLAN.json to repo root.'}
 assert len(parts)==19 and all(1<=x['file_count']<=95 for x in batches) and batches[-1]['file_count']==87
 with zipfile.ZipFile(KIT,'w',compression=zipfile.ZIP_STORED) as z:
  z.writestr('UPLOAD_PLAN.json',json.dumps(plan,**JSONOPT)+'\n')
  z.writestr('UPLOAD_GUIDE.md',(OUT/'docs/UPLOAD_GUIDE.md').read_bytes())
  for name,data in parts:z.writestr(name,data)
 assert zipfile.ZipFile(KIT).testzip() is None
 # Independent ZIP member/file hash audit in 19 packs.
 with zipfile.ZipFile(KIT) as outer,zipfile.ZipFile(RELEASE) as whole:
  assert set(whole.namelist())==set(files)
  for item in batches:
   with zipfile.ZipFile(io.BytesIO(outer.read(item['name']))) as z:
    assert set(z.namelist())==set(item['files'])
    for p in item['files']:
     assert z.read(p)==whole.read(p)==(OUT/p).read_bytes(),p
 (ROOT/'BUILD_REPORT.json').write_text(json.dumps({**report,'full_repository_sha256':sha(RELEASE.read_bytes()),'manual_upload_kit_sha256':sha(KIT.read_bytes()),'repository_zip':str(RELEASE),'kit_zip':str(KIT),'parts':[(i['name'],i['file_count'],i['bytes']) for i in batches]},**JSONOPT)+'\n')
 return {'repository_zip':str(RELEASE),'repository_zip_sha256':sha(RELEASE.read_bytes()),'kit_zip':str(KIT),'kit_zip_sha256':sha(KIT.read_bytes()),'parts':len(parts),'max_file_bytes':plan['largest_file_size'],'part_files':[x['file_count'] for x in batches]}

if __name__=='__main__':
 a=build();print('BUILD',json.dumps({k:v for k,v in a.items() if k!='source_markers'},ensure_ascii=False))
 b=build_zip_and_packs(a);print('PACKAGING',json.dumps(b))
