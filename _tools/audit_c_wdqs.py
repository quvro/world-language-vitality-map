# -*- coding: utf-8 -*-
import urllib.request, urllib.error, json, ssl

UA = "KeshihuaCourseProject-DataSourceAudit/1.0 (university data-viz course; contact: student@example.edu)"

Q = "SELECT (COUNT(?d) AS ?c) WHERE { ?d wdt:P31/wdt:P279* wd:Q178885. }"
URL = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(Q) if False else \
      "https://query.wikidata.org/sparql?format=json&query=SELECT%20(COUNT(%3Fd)%20AS%20%3Fc)%20WHERE%20%7B%20%3Fd%20wdt%3AP31%2Fwdt%3AP279*%20wd%3AQ178885.%20%7D"

print("QUERY:", Q)
print("URL  :", URL)
print()

for attempt in (1, 2):
    req = urllib.request.Request(URL, headers={
        "User-Agent": UA,
        "Accept": "application/sparql-results+json,application/json;q=0.9,*/*;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read()
            print(f"attempt {attempt}: HTTP {r.status} {r.reason}")
            print("  headers of interest:")
            for k in ["Content-Type", "Retry-After", "Server", "X-Served-By", "Cache-Control", "Age", "Vary"]:
                if k in r.headers:
                    print(f"    {k}: {r.headers[k]}")
            print("  body[:1200]:", body.decode("utf-8", "replace")[:1200])
            try:
                print("  PARSED:", json.loads(body.decode("utf-8", "replace")))
            except Exception as e:
                print("  parse err:", e)
    except urllib.error.HTTPError as e:
        body = e.read()
        print(f"attempt {attempt}: HTTPError HTTP {e.code} {e.reason}")
        for k in ["Content-Type", "Retry-After", "Server", "X-Served-By", "Cache-Control"]:
            if k in e.headers:
                print(f"    {k}: {e.headers[k]}")
        print("  body[:2000]:")
        print(body.decode("utf-8", "replace")[:2000])
    except Exception as e:
        print(f"attempt {attempt}: EXC {e!r}")
    print("-" * 60)

print("\n### Also: check the failure message page from the browser-ish endpoint ###")
for u in ["https://query.wikidata.org/bigdata/namespace/wdq/sparql?format=json&query=SELECT%20%3Fs%20WHERE%20%7B%3Fs%20wdt%3AP31%20wd%3AQ5%7D%20LIMIT%201",
          "https://query.wikidata.org/sparql"]:
    req = urllib.request.Request(u, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            b = r.read()
            print(f"  {u[:70]}... -> HTTP {r.status} bytes={len(b)}")
            print("   ", b.decode("utf-8", "replace")[:500].replace("\n", " "))
    except urllib.error.HTTPError as e:
        b = e.read()
        print(f"  {u[:70]}... -> HTTP {e.code} bytes={len(b)} Retry-After={e.headers.get('Retry-After')}")
        print("   ", b.decode("utf-8", "replace")[:800].replace("\n", " "))
    except Exception as e:
        print(f"  {u[:70]}... -> EXC {e!r}")
