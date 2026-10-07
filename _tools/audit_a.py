# -*- coding: utf-8 -*-
import re, sys, json
import urllib.request, urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"

def get(url, timeout=30, extra=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    if extra:
        for k, v in extra.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return r.status, dict(r.headers), raw
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except Exception as e:
        return None, {}, repr(e).encode()

def show(tag, url, grep=None, maxlen=400):
    st, hd, body = get(url)
    print("=" * 70)
    print(f"[{tag}] {url}")
    print(f"  status={st} bytes={len(body)} ctype={hd.get('Content-Type')}")
    txt = body.decode("utf-8", "replace")
    if grep:
        for pat in grep:
            hits = re.findall(pat, txt, re.I)
            uniq = sorted(set(h if isinstance(h, str) else str(h) for h in hits))
            print(f"  /{pat}/ -> {len(hits)} hits, uniq={uniq[:20]}")
    return st, hd, txt

TARGETS = sys.argv[1:] if len(sys.argv) > 1 else []

# 1. ihchina project + representative raw HTML -> find ajax url
for url in ["https://www.ihchina.cn/project.html", "https://www.ihchina.cn/representative.html"]:
    st, hd, txt = show("raw", url, grep=[r'url\s*:\s*["\'][^"\']+["\']',
                                          r'\$\.(?:ajax|post|get)\s*\(\s*["\'][^"\']+["\']',
                                          r'(?:action|api|ajaxUrl)\s*[:=]\s*["\'][^"\']+["\']',
                                          r'/project/[a-zA-Z_]+',
                                          r'/representative/[a-zA-Z_]+',
                                          r'\.json'])
    # dump script blocks mentioning ajax/search
    for m in re.finditer(r'<script[^>]*>(.*?)</script>', txt, re.S | re.I):
        s = m.group(1)
        if re.search(r'ajax|ajaxUrl|url\s*:|search', s, re.I) and len(s) < 6000:
            print("  --- SCRIPT BLOCK (%d chars) ---" % len(s))
            print("\n".join("    " + l.strip() for l in s.splitlines() if l.strip())[:3000])

print("\n\n########## robots.txt ##########")
show("robots", "https://www.ihchina.cn/robots.txt")
