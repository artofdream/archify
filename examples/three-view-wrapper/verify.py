#!/usr/bin/env python3
"""Optional browser smoke test for out/three-view.html (Chrome + Playwright, no other deps).

  pip install playwright   # uses the system Chrome: set CHROME=/path/to/chrome if not /usr/bin/google-chrome
  python3 build.py && python3 verify.py

Checks only this wrapper (tabs, hash routing, step player, chapters, Route button, gap table, theme).
Results and screenshots go to out/ (git-ignored). Chrome only; other browsers are untested.
"""
import json, os, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
F = HERE / "out" / "three-view.html"
SHOTS = HERE / "out" / "shots"; SHOTS.mkdir(exist_ok=True)
res = []
def chk(name, ok, info=""):
    res.append((name, bool(ok), info)); print(("PASS" if ok else "FAIL"), name, info)

def route_hash(pg):
    return pg.evaluate('()=>document.querySelector(".panel:not([hidden]) iframe").contentWindow.location.hash')

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get("CHROME", "/usr/bin/google-chrome"), args=["--no-sandbox"])
    for w in (1280, 800):
        for v in ("current", "target", "gaps"):
            pg = b.new_page(viewport={"width": w, "height": 900}); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            pg.goto(f"file://{F}#{v}"); pg.wait_for_timeout(1500)
            chk(f"{w} #{v} tab selected", pg.eval_on_selector(f"#tab-{v}", "e=>e.getAttribute('aria-selected')") == "true")
            ov = pg.evaluate("()=>{const W=document.documentElement.clientWidth;return document.documentElement.scrollWidth<=W+1}")
            chk(f"{w} #{v} no horizontal scroll", ov)
            chk(f"{w} #{v} no JS errors", not errs, str(errs)[:200])
            n = [f.evaluate('()=>document.querySelectorAll("[data-node-id]").length') for f in pg.frames if f != pg.main_frame]
            chk(f"{w} #{v} embedded Archify page has nodes", any(x > 0 for x in n), str(n))
            pg.screenshot(path=str(SHOTS / f"{v}-{w}.png")); pg.close()
    pg = b.new_page(viewport={"width": 1280, "height": 1000}); pg.goto(f"file://{F}"); pg.wait_for_timeout(1200)
    T = lambda: pg.inner_text("#ptitle")
    chk("default tab current", pg.eval_on_selector("#tab-current", "e=>e.getAttribute('aria-selected')") == "true")
    pg.click("#next"); chk("Next -> step 2", T().startswith("Step 2/5"), T())
    pg.click("#prev"); chk("Prev -> step 1", T().startswith("Step 1/5"), T())
    pg.keyboard.press("ArrowRight"); pg.keyboard.press("ArrowRight"); chk("ArrowRight x2 -> step 3", T().startswith("Step 3/5"), T())
    pg.click("#restart"); chk("Restart -> 1", T().startswith("Step 1/5"))
    pg.evaluate("document.activeElement.blur()"); pg.keyboard.press("Space"); chk("Space starts play", pg.inner_text("#play").strip().startswith("❚❚"))
    pg.keyboard.press("Space"); chk("Space pauses", pg.inner_text("#play").strip().startswith("▶"))
    pg.click("#play"); pg.wait_for_timeout(4200); chk("Play advances after 3.5 s", T().startswith("Step 2/5"), T()); pg.click("#play")
    for v, steps in (("current", (1, 4)), ("target", (4, 5)), ("gaps", (5,))):
        for n in steps:
            pg.goto(f"file://{F}?step={n}#{v}"); pg.wait_for_timeout(1500)
            chk(f"?step={n}#{v} title", T().startswith(f"Step {n}/5"), T())
            on = pg.evaluate("""()=>{const d=document.querySelector('.panel:not([hidden]) iframe').contentDocument;return [...d.querySelectorAll('[data-node-id]')].filter(g=>g.style.opacity==='1').map(g=>g.dataset.nodeId)}""")
            chk(f"?step={n}#{v} highlight applied", len(on) >= 2, str(on))
    pg.goto(f"file://{F}#target"); pg.wait_for_timeout(1200)
    ids = pg.eval_on_selector_all("#chapters button", "b=>b.map(x=>x.dataset.chapter)")
    chk("4 chapter buttons", ids == ["request", "auth", "store", "index"], str(ids))
    for c, step in (("request", 1), ("auth", 3), ("store", 4), ("index", 5)):
        pg.click(f"#chapters button[data-chapter={c}]"); chk(f"chapter {c} -> step {step}", T().startswith(f"Step {step}/"), T())
        chk(f"chapter {c} pressed", pg.eval_on_selector(f"#chapters button[data-chapter={c}]", "b=>b.getAttribute('aria-pressed')") == "true")
    pg.click("#route"); pg.wait_for_timeout(1200)
    chk("Route button sets #route=api~search in the embedded viewer", route_hash(pg) == "#route=api~search", route_hash(pg))
    pg.screenshot(path=str(SHOTS / "target-route.png"))
    pg.click("#clear"); pg.wait_for_timeout(500)
    chk("Clear removes highlight", pg.evaluate("()=>{const d=document.querySelector('.panel:not([hidden]) iframe').contentDocument;return [...d.querySelectorAll('[data-node-id]')].every(g=>g.style.opacity==='')}"))
    chk("Clear removes route hash", route_hash(pg) == "", route_hash(pg))
    for v in ("gaps", "current", "target"):
        pg.click(f"#tab-{v}"); pg.wait_for_timeout(300); chk(f"click tab {v} -> hash", pg.evaluate("()=>location.hash") == f"#{v}")
    chk("gap table rows", pg.eval_on_selector_all("table tbody tr", "r=>r.length") == 8)
    pg.click("#theme"); chk("theme toggle", pg.evaluate("()=>document.body.classList.contains('dark')"))
    pg.close(); b.close()
bad = [r for r in res if not r[1]]
print(len(res), "checks,", len(bad), "failed")
(HERE / "out" / "verify-results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
sys.exit(1 if bad else 0)
