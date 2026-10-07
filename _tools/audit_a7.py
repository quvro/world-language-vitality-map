# -*- coding: utf-8 -*-
import re, json, time, io
import urllib.request, urllib.error

OUT = io.StringIO()
def P(*a):
    s = " ".join(str(x) for x in a); print(s); OUT.write(s + "\n")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"

def get(url, timeout=120, headers=None):
    h = {"User-Agent": UA}
    if headers: h.update(headers)
    req = urllib.request.Request(url, headers=h)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read(), time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(), time.time() - t0
    except Exception as e:
        return None, {}, repr(e).encode(), time.time() - t0

H = {"X-Requested-With": "XMLHttpRequest", "Referer": "https://www.ihchina.cn/project.html"}

def probe(label, url, show_fields=False, save=None):
    st, hd, b, dt = get(url, headers=H)
    t = b.decode("utf-8", "replace")
    info = f"status={st} bytes={len(b)} {dt:.1f}s X-Cache={hd.get('X-Cache')} Age={hd.get('Age')}"
    try:
        j = json.loads(t)
        rows = j.get("list") or []
        info += f" | total={j.get('total')} p={j.get('p')} nrows={len(rows)}"
        if rows:
            r0 = rows[0]
            info += f" first_num={r0.get('num')!r} first_title={r0.get('title')!r} last_title={rows[-1].get('title')!r}"
        P(f"[{label}] {url}\n    {info}")
        if show_fields and rows:
            P("    FIELDS:", list(rows[0].keys()))
            P("    SAMPLE:", json.dumps(rows[0], ensure_ascii=False)[:600])
        if save:
            with open(save, "w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False, indent=1)
            P(f"    saved {save} ({len(rows)} rows)")
            cov = {}
            for r in rows:
                for k, v in r.items():
                    if v not in ("", None, "N;", "None", "</br>()"):
                        cov[k] = cov.get(k, 0) + 1
            P(f"    NON-EMPTY COVERAGE of {len(rows)}:")
            for k, c in sorted(cov.items(), key=lambda x: -x[1]):
                P(f"      {k}: {c}")
        return j, rows
    except Exception as e:
        P(f"[{label}] {url}\n    {info} | NON-JSON {t[:150]!r}")
        return None, []

print("=" * 70)
print("DECISIVE TEST: full 3610-record pull via cache-busting trailing slash")
print("=" * 70)
probe("slash limit=100000", "https://www.ihchina.cn/getProject.html/?province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=100000&p=1",
      show_fields=True, save=r"E:\develop\myprogram\keshihua\_tools\project_full.json")

print()
probe("slash limit=5000", "https://www.ihchina.cn/getProject.html/?province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=5000&p=1")
probe("slash limit=10 p1", "https://www.ihchina.cn/getProject.html/?province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=10&p=1")
probe("slash limit=10 p2", "https://www.ihchina.cn/getProject.html/?province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=10&p=2")

print("\n### The 4234-record dataset (lowercase / no-extension endpoint) ###")
probe("lowercase no-html full", "https://www.ihchina.cn/getProject?limit=100000&p=1",
      show_fields=True, save=r"E:\develop\myprogram\keshihua\_tools\project_4234.json")

print("\n### category filters on slash endpoint (do they work now?) ###")
for extra in ["&cate=%E6%B0%91%E9%97%B4%E6%96%87%E5%AD%A6", "&province=110000", "&rx_time=2006",
              "&keywords=%E6%98%86%E6%9B%B2"]:
    probe("filter " + extra[:22], "https://www.ihchina.cn/getProject.html/?province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=100000&p=1" + extra)

with open(r"E:\develop\myprogram\keshihua\_tools\results_a7.txt", "w", encoding="utf-8") as f:
    f.write(OUT.getvalue())
