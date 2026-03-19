#!/usr/bin/env python3
import os
import re
import json
from urllib.parse import urljoin, urlparse

import requests

BASE = "https://www.ect.go.th"
PAGE = "https://www.ect.go.th/th/election-2026"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")


def fetch(url: str) -> requests.Response:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    r = requests.get(url, headers=headers, timeout=60, allow_redirects=True)
    return r


def extract_links(html: str, base_url: str):
    # crude but effective: href/src links
    raw = re.findall(r"(?:href|src)=[\"']([^\"']+)[\"']", html, flags=re.IGNORECASE)
    links = []
    for u in raw:
        u = u.strip()
        if u.startswith("javascript:") or u.startswith("#") or u.startswith("mailto:"):
            continue
        abs_url = urljoin(base_url, u)
        links.append(abs_url)
    # dedupe
    seen = set()
    out = []
    for u in links:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def is_doc(url: str) -> bool:
    p = urlparse(url)
    path = p.path.lower()
    return any(path.endswith(ext) for ext in [".pdf", ".jpg", ".jpeg", ".png", ".zip"]) or "file_download" in path or "/web-upload/" in path


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    print(f"Fetching: {PAGE}")
    r = fetch(PAGE)
    print("Status:", r.status_code)
    print("Final URL:", r.url)
    ct = r.headers.get("Content-Type", "")
    print("Content-Type:", ct)

    out_html = os.path.join(DATA_DIR, "ect_election_2026_page.html")
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(r.text)
    print("Saved HTML:", out_html)

    links = extract_links(r.text, r.url)
    doc_links = [u for u in links if is_doc(u)]

    # Also scan plain text for http(s) occurrences (sometimes embedded)
    extra = re.findall(r"https?://[^\s\"'<>]+", r.text)
    for u in extra:
        if is_doc(u) and u not in doc_links:
            doc_links.append(u)

    # Group by host + path prefix
    groups = {}
    for u in doc_links:
        p = urlparse(u)
        host = p.netloc
        prefix = "/".join(p.path.strip("/").split("/")[:4])
        key = f"{host}/{prefix}"
        groups.setdefault(key, 0)
        groups[key] += 1

    out_json = os.path.join(DATA_DIR, "ect_election_2026_links.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "page": PAGE,
            "status": r.status_code,
            "final_url": r.url,
            "content_type": ct,
            "doc_links": sorted(doc_links),
            "groups": dict(sorted(groups.items(), key=lambda x: x[1], reverse=True)),
        }, f, ensure_ascii=False, indent=2)
    print("Saved links JSON:", out_json)

    print("\nTop groups:")
    for k, v in list(sorted(groups.items(), key=lambda x: x[1], reverse=True))[:15]:
        print(f"  {v:4d}  {k}")

    print(f"\nTotal doc-like links: {len(doc_links)}")
    print("Sample:")
    for u in sorted(doc_links)[:20]:
        print(" ", u)


if __name__ == "__main__":
    main()
