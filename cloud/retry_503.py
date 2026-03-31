# -*- coding: utf-8 -*-
"""Retry ONLY 503 errors from dispatch_missing error logs."""
import json, os, sys, time, re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, '..')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

def load_env():
    env = {}
    p = os.path.join(PROJECT_ROOT, '.env')
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env

def get_503_tasks(province):
    """Extract 503 error tasks from error log."""
    err_path = os.path.join(DATA_DIR, f'dispatch_missing_errors_{province}.json')
    if not os.path.exists(err_path):
        print(f"No error log for {province}"); return []
    errors = json.load(open(err_path, 'r', encoding='utf-8'))
    
    # Load drive index for file_id lookup
    idx_path = os.path.join(DATA_DIR, f'drive_index_{province}.json')
    drive_idx = json.load(open(idx_path, 'r', encoding='utf-8')) if os.path.exists(idx_path) else []
    name_to_fid = {}
    for d in drive_idx:
        label = f"{d.get('path','')}/{d.get('name','')}" if d.get('path') else d.get('name','')
        name_to_fid[label] = d.get('file_id','')
        name_to_fid[d.get('name','')] = d.get('file_id','')
    
    tasks = []
    for e in errors:
        msg = e.get('error', '')
        if '503' not in msg and 'Service Unavailable' not in msg:
            continue
        fname = e.get('file', '')
        page = e.get('page', 0)
        fid = name_to_fid.get(fname, '')
        if not fid:
            for key in name_to_fid:
                if key in fname or fname in key:
                    fid = name_to_fid[key]; break
        if not fid:
            m = re.search(r'file_id["\s:]+([A-Za-z0-9_-]{20,})', msg)
            if m: fid = m.group(1)
        if fid:
            tasks.append({'file_id': fid, 'file_label': fname, 'page_num': page - 1})
    return tasks

def send_task(url, fid, label, province, api_key, page_num):
    payload = {"file_id": fid, "file_label": label, "province": province,
               "google_api_key": api_key, "max_pages": 1, "page_num": page_num}
    try:
        r = requests.post(url, json=payload, timeout=600)
        if r.status_code != 200:
            return {"error": f"HTTP {r.status_code}: {r.text[:150]}", "file_id": fid, "file_label": label}
        return r.json()
    except Exception as e:
        return {"error": str(e), "file_id": fid, "file_label": label}

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--province", required=True)
    parser.add_argument("--function-url", required=True)
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    tasks = get_503_tasks(args.province)
    print(f"[{args.province}] Found {len(tasks)} pages with 503 errors to retry")
    
    if args.dry_run:
        for t in tasks[:20]:
            print(f"  p{t['page_num']+1} — {t['file_label'][-60:]}")
        return

    if not tasks:
        print("Nothing to retry!"); return

    env = load_env()
    api_key = env.get('GOOGLE_CLOUD_API_KEY', '')
    print(f"[Workers] {args.workers}")
    print(f"[URL] {args.function_url}\n")

    ok = err = 0
    error_log = []
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(send_task, args.function_url, t['file_id'], t['file_label'],
                            args.province, api_key, t['page_num']): t for t in tasks}
        for f in as_completed(futs):
            t = futs[f]
            res = f.result()
            p = t['page_num'] + 1
            short = t['file_label'][-50:]
            if 'error' in res:
                err += 1
                error_log.append({"file": t['file_label'], "page": p, "error": res['error'][:200]})
                print(f"  X [{ok+err}/{len(tasks)}] p{p} {short} — {res['error'][:60]}")
            else:
                ok += 1
                print(f"  OK [{ok+err}/{len(tasks)}] p{p} {short}")

    elapsed = time.time() - t0
    print(f"\nDONE in {elapsed:.0f}s — OK: {ok}, Errors: {err}")
    
    if error_log:
        path = os.path.join(DATA_DIR, f'retry_503_errors_{args.province}.json')
        json.dump(error_log, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print(f"Error log: {path}")

if __name__ == '__main__':
    main()
