# -*- coding: utf-8 -*-
import re, json, time, io, base64
import urllib.request, urllib.error

OUT = io.StringIO()
def P(*a):
    s = " ".join(str(x) for x in a); print(s); OUT.write(s + "\n")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"

def get(url, timeout=60, headers=None):
    h = {"User-Agent": UA, "Accept": "*/*"}
    if headers: h.update(headers)
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except Exception as e:
        return None, {}, repr(e).encode()

print("### Is raw.githubusercontent.com reachable? ###")
for u in ["https://raw.githubusercontent.com/metabismuth/tarot-json/master/README.md",
          "https://raw.githubusercontent.com/metabismuth/tarot-json/main/README.md"]:
    st, hd, b = get(u, timeout=25)
    P(f"  {u} -> status={st} bytes={len(b)} {b[:120].decode('utf-8','replace') if st is None else ''}")

GH = {"Accept": "application/vnd.github+json"}
def gh_file(repo, path):
    st, hd, b = get(f"https://api.github.com/repos/{repo}/contents/{path}", headers=GH)
    if st != 200:
        P(f"  !! {repo}/{path} -> {st} {b.decode('utf-8','replace')[:150]}")
        return None
    j = json.loads(b.decode())
    if isinstance(j, list):
        return j
    if j.get("encoding") == "base64":
        return base64.b64decode(j["content"])
    return j

print("\n### metabismuth/tarot-json : tarot.json ###")
b = gh_file("metabismuth/tarot-json", "tarot.json")
if b:
    j = json.loads(b.decode("utf-8", "replace"))
    P(f"  bytes={len(b)} top-type={type(j).__name__}")
    if isinstance(j, dict):
        P(f"  keys={list(j.keys())}")
        for k, v in list(j.items())[:3]:
            P(f"   -- {k}: {json.dumps(v, ensure_ascii=False)[:800]}")
    elif isinstance(j, list):
        P(f"  len={len(j)}")
        P("  first:", json.dumps(j[0], ensure_ascii=False)[:1000])
        allkeys = set()
        for it in j[:200]:
            if isinstance(it, dict): allkeys |= set(it.keys())
        P("  union of keys:", sorted(allkeys))
    # correspondence keywords?
    s = json.dumps(j, ensure_ascii=False).lower()
    for kw in ["element", "astrolog", "hebrew", "zodiac", "planet", "correspond", "golden dawn", "sephira"]:
        P(f"  contains '{kw}': {kw in s}")

print("\n### Tarotoo-com/tarotoo-tarot-dataset : data/cards.json ###")
b = gh_file("Tarotoo-com/tarotoo-tarot-dataset", "data/cards.json")
if b:
    j = json.loads(b.decode("utf-8", "replace"))
    P(f"  bytes={len(b)} type={type(j).__name__}")
    if isinstance(j, dict):
        P(f"  keys={list(j.keys())}")
        for k in list(j.keys())[:2]:
            P(f"   -- {k}: {json.dumps(j[k], ensure_ascii=False)[:900]}")
    elif isinstance(j, list):
        P(f"  len={len(j)}")
        P("  first:", json.dumps(j[0], ensure_ascii=False)[:900])
        allkeys = set()
        for it in j:
            if isinstance(it, dict): allkeys |= set(it.keys())
        P("  union of keys:", sorted(allkeys))
    s = json.dumps(j, ensure_ascii=False).lower()
    for kw in ["element", "astrolog", "hebrew", "zodiac", "planet"]:
        P(f"  contains '{kw}': {kw in s}")

print("\n### burdiuz/mythology_demo_data : genealogical_tree.json (Greek) ###")
b = gh_file("burdiuz/mythology_demo_data", "genealogical_tree.json")
if b:
    j = json.loads(b.decode("utf-8", "replace"))
    P(f"  bytes={len(b)} type={type(j).__name__}")
    if isinstance(j, dict):
        P(f"  keys={list(j.keys())[:20]}")
        P("  SAMPLE:", json.dumps(j, ensure_ascii=False)[:1200])
        n = len(re.findall(r'"name"', json.dumps(j, ensure_ascii=False)))
        P(f"  approx node count: {n}")

print("\n### ZSLPZDZH/shanhaijing-bestiaire : beasts_data.json ###")
b = gh_file("ZSLPZDZH/shanhaijing-bestiaire", "beasts_data.json")
if b:
    j = json.loads(b.decode("utf-8", "replace"))
    P(f"  bytes={len(b)} type={type(j).__name__}")
    if isinstance(j, dict):
        P(f"  keys={list(j.keys())[:20]}")
        for k in list(j.keys())[:2]:
            v = j[k]
            P(f"   -- {k}: {type(v).__name__} {len(v) if hasattr(v,'__len__') else ''}")
            P(f"      sample: {json.dumps(v[0] if isinstance(v,list) and v else v, ensure_ascii=False)[:800]}")
    elif isinstance(j, list):
        P(f"  len={len(j)}")
        P("  first:", json.dumps(j[0], ensure_ascii=False)[:900])
        allkeys = set()
        for it in j:
            if isinstance(it, dict): allkeys |= set(it.keys())
        P("  union of keys:", sorted(allkeys))

print("\n### yasenstar/shanhaijing : look for data files ###")
for d in ["01_ShanJing", "db-dumps", "puml_model"]:
    r = gh_file("yasenstar/shanhaijing", d)
    if isinstance(r, list):
        P(f"  {d}/: {[(i['name'], i.get('size')) for i in r][:15]}")
    time.sleep(0.7)

with open(r"E:\develop\myprogram\keshihua\_tools\results_final2.txt", "w", encoding="utf-8") as f:
    f.write(OUT.getvalue())
print("\n[saved]")
