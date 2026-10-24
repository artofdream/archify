#!/usr/bin/env python3
"""Build one self-contained page that wraps three Archify renders (Current / Target / Gaps).

EXAMPLE, NOT A CORE FEATURE. Archify renders one diagram per file; this script only
validates + delivers three architecture IRs with the Archify CLI and then embeds the three
delivered HTML pages in a small hand-written wrapper page (tabs + step player + gap table).
Python 3 standard library only. Nothing here changes Archify itself.

Usage:  python3 build.py            (from anywhere)
Env:    ARCHIFY=<path to archify/bin/archify.mjs>   default: <repo>/archify/bin/archify.mjs
        ARCHIFY_UPDATE_CHECK_DISABLED=1 is set for the CLI calls by this script.
Output: out/<view>.architecture.html (+ delivery receipts) and out/three-view.html (all git-ignored).
"""
import html, json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARCHIFY = os.environ.get("ARCHIFY") or str(HERE.parents[1] / "archify" / "bin" / "archify.mjs")
OUT = HERE / "out"
VIEWS = [("current", "1 · Current", "What exists today (sample data)"),
         ("target", "2 · Target", "What we want to build (sample data)"),
         ("gaps", "3 · Gaps", "Target minus current: DONE / PARTIAL / MISSING (sample data)")]
STATUS_COLOR = {"DONE": "#1b9e63", "PARTIAL": "#d98a00", "MISSING": "#d6335a"}


def archify(*args):
    env = dict(os.environ, ARCHIFY_UPDATE_CHECK_DISABLED="1")
    return subprocess.run(["node", ARCHIFY, *args], env=env, capture_output=True, text=True)


def render_view(view):
    ir = HERE / "sample" / f"{view}.architecture.json"
    res = archify("validate", "architecture", str(ir), "--json")
    report = json.loads(res.stdout or "{}")
    diags = report.get("diagnostics", [])
    if res.returncode != 0 or not report.get("ok"):
        sys.exit(f"validate failed for {view}:\n" + "\n".join(d.get("message", "") for d in diags))
    if diags:
        print(f"[{view}] validate warnings: {len(diags)}")
    out = OUT / f"{view}.architecture.html"
    res = archify("deliver", "architecture", str(ir), str(out), "--json")
    if res.returncode != 0:
        sys.exit(f"deliver failed for {view}:\n{res.stdout}\n{res.stderr}")
    print(f"[{view}] validate ok, deliver ok -> {out.relative_to(HERE)}")
    return out.read_text(encoding="utf-8")


# Runs inside each embedded Archify page: receives {type:'tvw-story', nodes, edges, color} and dims the rest.
INJECT = """<script>(function(){function clear(){document.querySelectorAll('[data-node-id]').forEach(function(g){g.style.opacity='';g.style.filter='';var r=g.querySelector('rect:not(.c-mask)');if(r){r.style.removeProperty('stroke');r.style.removeProperty('stroke-width')}});document.querySelectorAll('[data-edge-from]').forEach(function(p){p.style.opacity='';if(p.tagName==='path'){p.style.removeProperty('stroke');p.style.removeProperty('stroke-width')}})}
function apply(m){clear();if(!m.nodes)return;var c=m.color||'#e11d74';document.querySelectorAll('[data-node-id]').forEach(function(g){var on=m.nodes.indexOf(g.getAttribute('data-node-id'))>=0;g.style.opacity=on?'1':'0.22';if(on){g.style.filter='drop-shadow(0 0 5px '+c+')';var r=g.querySelector('rect:not(.c-mask)');if(r){r.style.setProperty('stroke',c,'important');r.style.setProperty('stroke-width','3.5','important')}}});document.querySelectorAll('[data-edge-from]').forEach(function(p){var on=(m.edges||[]).some(function(e){return p.getAttribute('data-edge-from')===e[0]&&p.getAttribute('data-edge-to')===e[1]});p.style.opacity=on?'1':'0.12';if(on&&p.tagName==='path'){p.style.setProperty('stroke',c,'important');p.style.setProperty('stroke-width','2.6','important')}})}
window.addEventListener('message',function(e){var m=e.data;if(m&&m.type==='tvw-story')apply(m)})})();</script>"""

CSS = """
:root{--bg:#f6f7fb;--fg:#1c2233;--mut:#5b6478;--card:#fff;--acc:#0b7aa8;--bd:#d5dae6}
body.dark{--bg:#0f1420;--fg:#e6e9ef;--mut:#9aa3b8;--card:#182033;--acc:#4cc9f0;--bd:#2a3550}
body{margin:0;font:15px/1.5 system-ui,sans-serif;background:var(--bg);color:var(--fg)}
header,main{max-width:1240px;margin:auto;padding:12px 16px}
h1{font-size:1.3rem;margin:.2em 0}
.banner{border:2px dashed var(--acc);border-radius:8px;padding:6px 12px;margin:6px 0;color:var(--fg)}
.hon{display:inline-block;border:1px solid var(--acc);color:var(--acc);border-radius:99px;padding:1px 10px;font-size:.8rem;margin:2px 4px 2px 0}
[role=tablist]{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}
button{font:inherit;background:var(--card);color:var(--fg);border:1px solid var(--bd);border-radius:8px;padding:6px 14px;cursor:pointer}
button[aria-selected=true],button[aria-pressed=true]{border-color:var(--acc);box-shadow:0 0 0 2px var(--acc) inset;font-weight:600}
iframe{width:100%;height:78vh;min-height:620px;border:1px solid var(--bd);border-radius:10px;background:#fff}
.note{color:var(--mut);margin:4px 0} .wrap{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:.85rem;background:var(--card)} th,td{border:1px solid var(--bd);padding:5px 8px;text-align:left;vertical-align:top}
#player{background:var(--card);border:1px solid var(--bd);border-radius:10px;margin:10px 0;padding:8px 12px}
.pbar{display:flex;flex-wrap:wrap;gap:6px;align-items:center} #pcount{margin-left:auto;color:var(--mut)}
#chapters{display:grid;grid-template-columns:repeat(auto-fit,minmax(9.5rem,1fr));gap:6px;margin-top:8px}
#chapters button{width:100%;height:100%;text-align:left;padding:5px 10px;font-size:.85rem;line-height:1.25} #chapters small{display:block;color:var(--mut);font-weight:400}
#pchap{margin-top:6px;font-size:.85rem;color:var(--mut)} #pchap button{padding:2px 10px;font-size:.8rem;margin-left:6px}
#ptitle{font-weight:700;margin-top:6px} #phops{color:var(--mut);font-size:.82rem} #ptext{margin:4px 0}
.chip{color:#fff;border-radius:99px;padding:1px 8px;font-size:.75rem;font-weight:600}
"""

JS = r"""
const vs=['current','target','gaps'];const STORY=__STORY__;const CHAP=__CHAPTERS__;let cur=0,timer=null,active='current';
function show(v){if(!vs.includes(v))v='current';vs.forEach(x=>{document.getElementById('p-'+x).hidden=x!==v;document.getElementById('tab-'+x).setAttribute('aria-selected',x===v)});active=v;history.replaceState(null,'','#'+v);render()}
vs.forEach(v=>document.getElementById('tab-'+v).onclick=()=>show(v));
document.getElementById('theme').onclick=()=>document.body.classList.toggle('dark');
function post(m){const f=document.querySelector('#p-'+active+' iframe');if(f&&f.contentWindow)f.contentWindow.postMessage(m,'*')}
function chapOf(){return CHAP[active].findIndex(c=>c.steps.indexOf(cur+1)>=0)}
function setRoute(r){const f=document.querySelector('#p-'+active+' iframe');try{f.contentWindow.location.hash=r?'#route='+r:''}catch(e){}}
function renderChap(){const ci=chapOf(),box=document.getElementById('chapters');box.innerHTML='';
CHAP[active].forEach((c,i)=>{const b=document.createElement('button');b.type='button';b.setAttribute('aria-pressed',i===ci);b.dataset.chapter=c.id;b.textContent=(i+1)+' · '+c.label;const sm=document.createElement('small');sm.textContent='step'+(c.steps.length>1?'s '+c.steps[0]+'–'+c.steps[c.steps.length-1]:' '+c.steps[0]);b.appendChild(sm);b.onclick=()=>{stop();go(c.steps[0]-1)};box.appendChild(b)});
const c=CHAP[active][ci],p=document.getElementById('pchap');p.textContent='';if(c){p.append('Chapter '+(ci+1)+'/'+CHAP[active].length+' — '+c.label+': '+c.note+' ');const r=document.createElement('button');r.type='button';r.id='route';r.textContent='Show this route in Archify';r.onclick=()=>setRoute(c.route);p.appendChild(r)}}
function render(){renderChap();const s=STORY[active][cur];const t=document.getElementById('ptitle');t.textContent='Step '+(cur+1)+'/'+STORY[active].length+' — '+s.title+' ';const chip=document.createElement('span');chip.className='chip';chip.style.background=s.color;chip.textContent=s.status;t.appendChild(chip);
document.getElementById('phops').textContent='Hop: '+s.hops;document.getElementById('ptext').textContent=s.caption;document.getElementById('pcount').textContent=active+' view';
post({type:'tvw-story',nodes:s.nodes,edges:s.edges,color:s.color})}
function go(n){cur=Math.max(0,Math.min(STORY[active].length-1,n));render()}
function stop(){if(timer){clearInterval(timer);timer=null}document.getElementById('play').textContent='▶ Play'}
function playpause(){if(timer){stop();return}if(cur>=STORY[active].length-1)cur=0;render();document.getElementById('play').textContent='❚❚ Pause';timer=setInterval(()=>{if(cur>=STORY[active].length-1){stop();return}go(cur+1)},3500)}
document.getElementById('prev').onclick=()=>{stop();go(cur-1)};document.getElementById('next').onclick=()=>{stop();go(cur+1)};
document.getElementById('play').onclick=playpause;document.getElementById('restart').onclick=()=>{stop();go(0)};
document.getElementById('clear').onclick=()=>{stop();post({type:'tvw-story'});setRoute('')};
document.addEventListener('keydown',e=>{if(e.key==='ArrowRight'){stop();go(cur+1)}else if(e.key==='ArrowLeft'){stop();go(cur-1)}else if(e.key===' '&&e.target.tagName!=='BUTTON'){e.preventDefault();playpause()}});
document.querySelectorAll('iframe').forEach(f=>f.addEventListener('load',render));
cur=Math.max(0,(+(new URLSearchParams(location.search).get('step')||1))-1);show(location.hash.slice(1));
"""


def main():
    OUT.mkdir(exist_ok=True)
    pages = {v: render_view(v) for v, _, _ in VIEWS}
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    chapters = json.loads((HERE / "chapters.json").read_text(encoding="utf-8"))
    gap_rows = json.loads((HERE / "gap-table.json").read_text(encoding="utf-8"))
    tabs = "".join(f'<button role="tab" data-v="{v}" id="tab-{v}">{n}</button>' for v, n, _ in VIEWS)
    panels = "".join(
        f'<section class="panel" id="p-{v}" role="tabpanel" hidden><p class="note">{html.escape(d)}</p>'
        f'<iframe title="{html.escape(n)}" loading="eager" srcdoc="{html.escape(pages[v].replace("</body>", INJECT + "</body>", 1), quote=True)}"></iframe></section>'
        for v, n, d in VIEWS)
    rows = "".join(
        f"<tr><td><b>{html.escape(r['element'])}</b></td><td>{html.escape(r['today'])}</td><td>{html.escape(r['target'])}</td>"
        f"<td><span class=chip style='background:{STATUS_COLOR[r['gap']]}'>{r['gap']}</span></td></tr>" for r in gap_rows)
    js = JS.replace("__STORY__", json.dumps(story)).replace("__CHAPTERS__", json.dumps(chapters))
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Example: three-view wrapper around Archify (sample data)</title><style>{CSS}</style></head><body>
<header><h1>Notes service (invented sample): Current · Target · Gaps</h1>
<div class="banner"><b>Example, not a core Archify feature.</b> Three separate Archify renders embedded in a hand-written wrapper page. The system shown is invented for illustration.</div>
<span class="hon">Sample data</span><span class="hon">Wrapper is custom HTML</span><span class="hon">Diagrams are Archify</span>
<div role="tablist" aria-label="View">{tabs}<button id="theme">Dark / light</button></div></header>
<main><div id="player" aria-live="polite">
<div class="pbar"><b>Request path: play story</b>
<button id="prev">◀ Prev</button><button id="play">▶ Play</button><button id="next">Next ▶</button><button id="restart">⟲ Restart</button><button id="clear">Clear</button>
<span id="pcount"></span></div>
<div id="chapters" role="group" aria-label="Chapters (rendered by this page, not by Archify)"></div>
<div id="pchap"></div>
<div id="pcap"><div id="ptitle"></div><div id="phops"></div><p id="ptext"></p></div>
<details class="note"><summary>Keys and notes</summary><p class="note">Keys: ← → step, Space play/pause. The highlight follows the active tab. The player and the chapter buttons are custom HTML in this page; Archify has no playback of its own. “Show this route in Archify” sets the deep link <code>#route=a~b</code> in the embedded viewer (Archify's own Route view).</p></details>
</div>
{panels}
<h2>Gap table (same data as the Gaps view)</h2>
<div class="wrap"><table><thead><tr><th>Element</th><th>Today</th><th>Target</th><th>Gap</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="note">Each view is a full Archify page (embedded, offline). The tab switcher is custom HTML because Archify renders one diagram per file.</p></main>
<script>{js}</script></body></html>"""
    (OUT / "three-view.html").write_text(page, encoding="utf-8")
    print(f"wrote {(OUT / 'three-view.html').relative_to(HERE)} ({len(page):,} bytes)")


if __name__ == "__main__":
    main()
