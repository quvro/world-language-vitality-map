# -*- coding: utf-8 -*-
import urllib.request, urllib.error, json, time

UA = "KeshihuaCourseProject-DataSourceAudit/1.0 (university data-viz course)"

def wdqs(sparql, tag):
    url = "https://query.wikidata.org/sparql?format=json&query=" + urllib.request.quote(sparql)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/sparql-results+json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            b = r.read()
            dt = time.time() - t0
            print(f"[{tag}] HTTP {r.status} in {dt:.1f}s bytes={len(b)} Age={r.headers.get('Age')} "
                  f"Retry-After={r.headers.get('Retry-After')} X-Served-By={r.headers.get('X-Served-By')}")
            try:
                j = json.loads(b.decode())
                bs = j.get("results", {}).get("bindings", [])
                print(f"    rows={len(bs)} sample={json.dumps(bs[:3], ensure_ascii=False)[:400]}")
            except Exception as e:
                print("    body:", b.decode("utf-8", "replace")[:400])
            return r.status
    except urllib.error.HTTPError as e:
        dt = time.time() - t0
        b = e.read()
        print(f"[{tag}] ** HTTPError {e.code} in {dt:.1f}s Retry-After={e.headers.get('Retry-After')}")
        print("    body:", b.decode("utf-8", "replace")[:1200])
        return e.code
    except Exception as e:
        print(f"[{tag}] EXC after {time.time()-t0:.1f}s: {e!r}")
        return None

print("### RATE-LIMIT TEST: 5 DISTINCT uncached queries back-to-back ###")
qs = [
    ("Q178885 label", 'SELECT ?l WHERE { wd:Q178885 rdfs:label ?l FILTER(lang(?l)="en") }'),
    ("tarot cards count", 'SELECT (COUNT(?c) AS ?n) WHERE { ?c wdt:P31 wd:Q1798771 }'),
    ("mythology count", 'SELECT (COUNT(?m) AS ?n) WHERE { ?m wdt:P31/wdt:P279* wd:Q9134 }'),
    ("deities count", 'SELECT (COUNT(?d) AS ?n) WHERE { ?d wdt:P31/wdt:P279* wd:Q178885 }'),
    ("greek myth chars", 'SELECT (COUNT(?p) AS ?n) WHERE { ?p wdt:P31 wd:Q5; wdt:P1343 wd:Q131969 }'),
]
for tag, q in qs:
    wdqs(q, tag)
    time.sleep(1)

print("\n### WDQS landing/status pages ###")
for u in ["https://query.wikidata.org/", "https://query.wikidata.org/bigdata/namespace/wdq/sparql?query=SELECT%20(COUNT(*)%20AS%20%3Fn)%20WHERE%20%7B%3Fs%20%3Fp%20%3Fo%7D%20LIMIT%201&format=json"]:
    req = urllib.request.Request(u, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            b = r.read()
            print(f"  {u[:60]} -> HTTP {r.status} bytes={len(b)}")
            txt = b.decode("utf-8", "replace")
            for kw in ["rate limit", "rate-limit", "1 request", "throttl", "outage", "maintenance", "429"]:
                if kw.lower() in txt.lower():
                    i = txt.lower().find(kw.lower())
                    print(f"     HIT '{kw}': ...{txt[max(0,i-200):i+250]}...".replace("\n", " "))
    except urllib.error.HTTPError as e:
        print(f"  {u[:60]} -> HTTP {e.code} Retry-After={e.headers.get('Retry-After')}")
        print("    ", e.read().decode("utf-8", "replace")[:600])
    except Exception as e:
        print(f"  {u[:60]} -> EXC {e!r}")
