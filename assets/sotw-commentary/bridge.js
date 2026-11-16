/* SOTW Historical Commentary v3, translation-neutral, read-only bridge v1.
 * Copyright 2026 SOTW. This adapter does not embed, rewrite, or assign authorship to source commentary.
 * All P scope comes exclusively from the authoritative overlay. */
(()=>{'use strict';
const tag=document.currentScript;
const BOOK=(tag?.dataset.sotwBook||document.documentElement.dataset.book||'').toUpperCase();
const EDITION=(tag?.dataset.sotwEdition||'').toUpperCase();
const BASE='https://sotw-historical-commentaries.github.io/historical-commentary-resources/';
const AUTHORS=[['matthew-henry','Matthew Henry'],['john-calvin','John Calvin'],['adam-clarke','Adam Clarke'],['jamieson-fausset-brown','Jamieson, Fausset & Brown'],['keil-delitzsch','Keil & Delitzsch'],['john-gill','John Gill']];
const ALLOWED=['ASV1901','WEBSTER1833','BSB'];
if(!/^(?:[1-3]?[A-Z]{2,3})$/.test(BOOK)||!ALLOWED.includes(EDITION)||document.getElementById('sotw-historical-bridge'))return;
const el=(name,cls,txt)=>{const n=document.createElement(name);if(cls)n.className=cls;if(txt!==undefined)n.textContent=txt;return n;};
const api=path=>{const p=String(path).replace(/^\/+/, '');if(!p.startsWith('api/v3/')||p.includes('..')||/[?#]/.test(p))throw Error('Rejected non-canonical commentary resource path');return new URL(p,BASE).href;};
const cache=new Map();
async function read(path){if(!cache.has(path))cache.set(path,fetch(api(path),{mode:'cors',cache:'default'}).then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json();}).catch(e=>{cache.delete(path);throw e;}));return cache.get(path);}
const style=el('style');style.textContent=`
#sotw-historical-bridge{grid-column:1/-1;max-width:100%;box-sizing:border-box;margin:16px 0;background:white;border:1px solid #ccd9d3;border-radius:12px;padding:16px;color:#213b3e;font:14px/1.6 system-ui,sans-serif}
#sotw-historical-bridge *{box-sizing:border-box}#sotw-historical-bridge h2{margin:0 0 6px;font:600 20px Georgia,serif}
#sotw-historical-bridge p{margin:7px 0}#sotw-historical-bridge .sw-tabs,#sotw-historical-bridge .sw-authors,#sotw-historical-bridge .sw-list{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0}
#sotw-historical-bridge button{font:inherit;cursor:pointer;padding:7px 10px;background:#fff;color:#204b4a;border:1px solid #bacdc7;border-radius:7px}
#sotw-historical-bridge button[aria-pressed=true]{color:#fff;background:#235a54;border-color:#235a54}
#sotw-historical-bridge .sw-note{color:#526f71;font-size:12px}#sotw-historical-bridge .sw-source{margin-top:10px;font-size:12px;color:#496264;overflow-wrap:anywhere}
#sotw-historical-bridge .sw-entry{border-top:1px solid #e4eae6;padding:11px 0}#sotw-historical-bridge .sw-content{font:14px/1.72 Georgia,serif;white-space:pre-wrap;overflow-wrap:anywhere;max-height:38vh;overflow-y:auto;padding:10px;background:#f9faf8;border-radius:7px}
#sotw-historical-bridge a{color:#245e6b;overflow-wrap:anywhere}#sotw-historical-bridge .sw-error{color:#8a3f27}#sotw-historical-bridge .sw-status{min-height:20px}
@media(max-width:620px){#sotw-historical-bridge{padding:12px;margin:12px 0}#sotw-historical-bridge button{padding:7px}#sotw-historical-bridge .sw-content{max-height:48vh}}`;
document.head.append(style);
const box=el('section');box.id='sotw-historical-bridge';box.setAttribute('aria-label','Historical commentary and original author prefaces');
const heading=el('h2',null,'Historical Commentary');box.append(heading);
const caption=el('p','sw-note','Independent historical authors. Scripture text above remains '+(EDITION==='WEBSTER1833'?"Noah Webster’s Bible (1833)":EDITION==='ASV1901'?'ASV 1901':'BSB')+'.');box.append(caption);
const current=el('p','sw-status','Preparing source links…');current.setAttribute('aria-live','polite');box.append(current);
const tabs=el('div','sw-tabs');tabs.setAttribute('role','group');tabs.setAttribute('aria-label','Commentary scope');box.append(tabs);
const authors=el('div','sw-authors');authors.setAttribute('role','group');authors.setAttribute('aria-label','Historical author');box.append(authors);
const list=el('div','sw-list');box.append(list);
const result=el('div');box.append(result);
const attribution=el('p','sw-source');const sourceLink=el('a',null,'Original source and navigation data');sourceLink.href=api('api/v3/navigation-coverage/v1/books/'+BOOK+'.json');sourceLink.target='_blank';sourceLink.rel='noopener noreferrer';attribution.append(sourceLink,document.createTextNode(' · Historical sources stay in the independent SOTW library.'));box.append(attribution);
const main=document.querySelector('main');if(!main)return;
// ASV reader has a two-column grid; other readers have a single content column.
main.append(box);
const state={tab:'verse',author:'matthew-henry',ref:null,selectedSection:null,manifest:null,overlay:null,token:0};
function currentRef(){
 const chEl=document.getElementById('chapterSelect')||document.getElementById('chapter');
 const veEl=document.getElementById('verseSelect')||document.getElementById('verse');
 if(!chEl||!veEl||!chEl.value||!veEl.value)return null;
 const c=Number(chEl.value),v=Number(veEl.value);
 if(!Number.isSafeInteger(c)||c<1||!Number.isSafeInteger(v)||v<1)return null;
 if(!Array.from(veEl.options).some(o=>Number(o.value)===v))return null;
 // A BSB omitted verse never gets into the selection menu. Validate against the actual edition selection.
 const selectedText=document.getElementById('selectionId')?.textContent?.trim();
 if(selectedText&&selectedText!==`${BOOK}.${c}.${v}`)return null;
 return {book:BOOK,chapter:c,verse:v,id:`${BOOK}.${c}.${v}`};
}
function createButton(label,active,fn){const b=el('button',null,label);b.type='button';b.setAttribute('aria-pressed',String(!!active));b.addEventListener('click',fn);return b;}
function infoText(s){return s.title||s.role?.replace(/_/g,' ')||s.section_id;}
function nameFor(author){return AUTHORS.find(x=>x[0]===author)?.[1]||author;}
function compareRef(a,b){const re=/^([1-3]?[A-Z]{2,3})\.(\d+)\.(\d+)$/;const x=re.exec(a||''),y=re.exec(b||'');if(!x||!y||x[1]!==y[1])return null;return Number(x[2])-Number(y[2])||Number(x[3])-Number(y[3]);}
function eligible(s){return s.status==='active' && Array.isArray(s.eligible_books)&&s.eligible_books.includes(BOOK);}
function inPassage(s,ref){if(s.scope!=='passage'||!s.passage_start||!s.passage_end)return false;const lo=compareRef(ref,s.passage_start),hi=compareRef(ref,s.passage_end);return lo!==null&&hi!==null&&lo>=0&&hi<=0;}
function sectionInChapter(s,ref){if(s.scope==='chapter'){
  const p=(s.passage_start||'').split('.');return p[0]===BOOK&&Number(p[1])===ref.chapter;
 }if(s.scope==='passage'){
  const lo=compareRef(`${BOOK}.${ref.chapter}.1`,s.passage_end),hi=compareRef(`${BOOK}.${ref.chapter}.176`,s.passage_start);
  return lo!==null&&hi!==null&&lo<=0&&hi>=0;
 }return false;}
function sectionsFor(tab,ref){const all=Object.entries(state.overlay?.author_sections||{}).flatMap(([author,sects])=>sects.filter(eligible).map(s=>({...s,author_id:author})));
 if(tab==='book')return all.filter(s=>['work','volume','book_group','book'].includes(s.scope));
 if(tab==='chapter')return all.filter(s=>s.scope==='chapter'&&sectionInChapter(s,ref));
 if(tab==='passage')return all.filter(s=>inPassage(s,ref));
 return [];
}
function displayEntry(label,text,meta,path){const article=el('article','sw-entry');article.append(el('strong',null,label));const contents=el('div','sw-content',text||'(No text preserved for this source section.)');article.append(contents);const foot=el('div','sw-source',meta||'Original historical source');if(path){const a=el('a',null,'Read original JSON');a.href=api(path);a.target='_blank';a.rel='noopener noreferrer';foot.append(document.createTextNode(' · '),a);}article.append(foot);result.append(article);}
async function render(){const token=++state.token;result.replaceChildren();list.replaceChildren();tabs.replaceChildren();authors.replaceChildren();
 const ref=state.ref;if(!ref){current.textContent='Choose a numbered verse in the Bible reader to see the corresponding historical sources.';return;}
 current.textContent=ref.id+' · '+({verse:'Verse commentary',chapter:'Chapter introductions',book:'Book information & prefaces',passage:'Explicit passage sections'}[state.tab]);
 for(const [key,label] of [['verse','Verse'],['chapter','Chapter'],['book','Book & prefaces'],['passage','Passage']])tabs.append(createButton(label,state.tab===key,()=>{state.tab=key;state.selectedSection=null;render();}));
 for(const [id,label] of AUTHORS)authors.append(createButton(label,state.author===id,()=>{state.author=id;state.selectedSection=null;render();}));
 if(!state.manifest||!state.overlay){result.append(el('p','sw-note','Loading the authoritative historical navigation…'));return;}
 try{
 if(state.tab==='verse'){
 const snap=state.manifest.chapter_snapshots?.[BOOK];if(!snap)throw Error('The current historical manifest does not include '+BOOK);
 const indexPath=`api/v3/snapshots/${snap}/index/${BOOK}/${ref.chapter}.json`;
 const idx=await read(indexPath);if(token!==state.token)return;
 if(idx.canonical_chapter!==`${BOOK}.${ref.chapter}`||idx.snapshot_id!==snap)throw Error('Source chapter identity mismatch');
 const pointers=idx.verse_routes?.[String(ref.verse)]?.[state.author]||[];
 const authorRow=idx.authors.find(a=>a.author_id===state.author);
 if(!pointers.length){result.append(el('p','sw-note',authorRow?.source_unavailable?'This author’s original work is not available for this testament or chapter.':'No original commentary entry is explicitly indexed to this verse for this author. Nearby entries are not substituted.'));return;}
 if(!authorRow?.path)throw Error('Missing original author chapter pointer');
 const sourcePath=authorRow.path.replace(/^\//,'');const src=await read(sourcePath);if(token!==state.token)return;
 if(src.author_id!==state.author||src.canonical_chapter!==`${BOOK}.${ref.chapter}`||src.snapshot_id!==snap)throw Error('Original author chapter metadata mismatch');
 const usable=pointers.map(i=>src.entries[i]).filter(e=>e&&e.reader_visible!==false);
 if(!usable.length){result.append(el('p','sw-note','The original source entries are not reader-visible.'));return;}
 for(const e of usable){if(!String(e.passage_start||'').startsWith(`${BOOK}.`))throw Error('Source entry passage mismatch');
  displayEntry(`${nameFor(state.author)} · ${e.passage_start}`+(e.passage_end!==e.passage_start?`–${e.passage_end}`:''),e.reader_content_plain||e.content_plain||Array.isArray(e.content_parts)&&e.content_parts.join('\n\n')||'',`Source: ${src.source?.system||'original edition'} · ${e.entry_id}`,sourcePath);
 }
 }else{
 const sections=sectionsFor(state.tab,ref).filter(s=>s.author_id===state.author);
 if(!sections.length){result.append(el('p','sw-note','No source-verified '+(state.tab==='book'?'book preface or introduction':state.tab==='chapter'?'chapter introduction':'passage overview')+' is available for this author at this location.'));return;}
 for(const s of sections){const detail=`${infoText(s)} · ${s.role.replace(/_/g,' ')}`;list.append(createButton(detail,state.selectedSection===s.section_id,()=>{state.selectedSection=s.section_id;render();}));}
 if(!state.selectedSection||!sections.some(s=>s.section_id===state.selectedSection)){result.append(el('p','sw-note',`${sections.length} original source section${sections.length===1?'':'s'} available. Select a title above to read it.`));return;}
 const s=sections.find(x=>x.section_id===state.selectedSection);const sourcePath=s.source?.chapter_file?.replace(/^\//,'');if(!sourcePath)throw Error('Non-verse section is missing source path');
 const chapter=await read(sourcePath);if(token!==state.token)return;
 const original=chapter.navigation_sections?.find(x=>x.section_id===s.section_id);
 if(!original)throw Error('Authoritative P source pointer does not resolve');
 if(s.source?.fragment_sha256&&original.source?.fragment_sha256!==s.source.fragment_sha256)throw Error('P fragment integrity mismatch');
 displayEntry(`${nameFor(s.author_id)} · ${infoText(s)}`,original.content_plain,`P navigation only · ${s.scope} · ${s.role} · ${s.section_id}`,sourcePath);
 }
 }catch(e){if(token!==state.token)return;const error=el('p','sw-error','Could not display remote historical source: '+e.message);result.append(error);result.append(el('p','sw-note','The translation remains readable. Use the original source link below to inspect the independent commentary dataset.'));}
}
function sync(){const ref=currentRef();if(!ref||state.ref?.id===ref.id)return;state.ref=ref;state.selectedSection=null;render();}
async function boot(){try{const manifest=await read('api/v3/navigation-coverage/v1/manifest.json');if(!manifest.books?.includes(BOOK)||!manifest.chapter_snapshots?.[BOOK])throw Error('No canonical book mapping in historical manifest');const overlay=await read(`api/v3/navigation-coverage/v1/books/${BOOK}.json`);if(overlay.book_id!==BOOK||overlay.snapshot_id!==manifest.chapter_snapshots[BOOK])throw Error('Non-verse overlay identity mismatch');state.manifest=manifest;state.overlay=overlay;render();}catch(e){result.replaceChildren(el('p','sw-error','Historical commentary feed unavailable: '+e.message));}}
for(const id of ['chapter','verse','chapterSelect','verseSelect'])document.getElementById(id)?.addEventListener('change',()=>setTimeout(sync,40));
window.addEventListener('hashchange',()=>setTimeout(sync,30));
const observeIds=['scripture','selectionId','text'];for(const id of observeIds){const n=document.getElementById(id);if(n)new MutationObserver(()=>{setTimeout(sync,0);}).observe(n,{childList:true,subtree:id!=='selectionId',attributes:id==='scripture',attributeFilter:id==='scripture'?['class']:undefined});}
// Covers chapter renderers that update select.value without dispatching an event.
let last='',ticks=0;const warm=setInterval(()=>{const v=currentRef()?.id||'';if(v&&v!==last){last=v;sync();}if(++ticks>=30)clearInterval(warm);},300);
sync();boot();
})();
