# -*- coding: utf-8 -*-
"""
Prepare review data for the React review app.
Combines OCR results JSON with debug images and text files.

Usage:
  python scripts/prepare_review_data.py
"""
import json
import os
import re
import shutil
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
try:
    from ocr_cloud_vision import parse_ss518_text
except ImportError:
    parse_ss518_text = None
PROJECT_ROOT = os.path.join(SCRIPT_DIR, '..')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

# Canonical slug → Thai province name mapping
SLUG_TO_PROVINCE = {
    "bangkok": "กรุงเทพมหานคร",
    "krabi": "กระบี่",
    "kanchanaburi": "กาญจนบุรี",
    "kalasin": "กาฬสินธุ์",
    "kamphaengphet": "กำแพงเพชร",
    "khonkaen": "ขอนแก่น",
    "chanthaburi": "จันทบุรี",
    "chachoengsao": "ฉะเชิงเทรา",
    "chonburi": "ชลบุรี",
    "chainat": "ชัยนาท",
    "chaiyaphum": "ชัยภูมิ",
    "chumphon": "ชุมพร",
    "chiangrai": "เชียงราย",
    "chiangmai": "เชียงใหม่",
    "trang": "ตรัง",
    "trat": "ตราด",
    "tak": "ตาก",
    "nakhonnayok": "นครนายก",
    "nakhonpathom": "นครปฐม",
    "nakhonphanom": "นครพนม",
    "nakhonratchasima": "นครราชสีมา",
    "nakhonsithammarat": "นครศรีธรรมราช",
    "nakhonsawan": "นครสวรรค์",
    "nonthaburi": "นนทบุรี",
    "narathiwat": "นราธิวาส",
    "nan": "น่าน",
    "buengkan": "บึงกาฬ",
    "buriram": "บุรีรัมย์",
    "pathumthani": "ปทุมธานี",
    "prachuapkhirikhan": "ประจวบคีรีขันธ์",
    "prachinburi": "ปราจีนบุรี",
    "pattani": "ปัตตานี",
    "ayutthaya": "พระนครศรีอยุธยา",
    "phayao": "พะเยา",
    "phangnga": "พังงา",
    "phatthalung": "พัทลุง",
    "phichit": "พิจิตร",
    "phitsanulok": "พิษณุโลก",
    "phetchaburi": "เพชรบุรี",
    "phetchabun": "เพชรบูรณ์",
    "phrae": "แพร่",
    "maehongson": "แม่ฮ่องสอน",
    "mukdahan": "มุกดาหาร",
    "mahasarakham": "มหาสารคาม",
    "yasothon": "ยโสธร",
    "yala": "ยะลา",
    "roiet": "ร้อยเอ็ด",
    "ranong": "ระนอง",
    "rayong": "ระยอง",
    "ratchaburi": "ราชบุรี",
    "lopburi": "ลพบุรี",
    "lampang": "ลำปาง",
    "lamphun": "ลำพูน",
    "loei": "เลย",
    "sisaket": "ศรีสะเกษ",
    "sakonnakhon": "สกลนคร",
    "songkhla": "สงขลา",
    "satun": "สตูล",
    "samutprakan": "สมุทรปราการ",
    "samutsongkhram": "สมุทรสงคราม",
    "samutsakhon": "สมุทรสาคร",
    "sakaeo": "สระแก้ว",
    "saraburi": "สระบุรี",
    "singburi": "สิงห์บุรี",
    "sukhothai": "สุโขทัย",
    "suphanburi": "สุพรรณบุรี",
    "suratthani": "สุราษฎร์ธานี",
    "surin": "สุรินทร์",
    "nongkhai": "หนองคาย",
    "nongbualamphu": "หนองบัวลำภู",
    "angthong": "อ่างทอง",
    "amnatcharoen": "อำนาจเจริญ",
    "udonthani": "อุดรธานี",
    "uttaradit": "อุตรดิตถ์",
    "uthaithani": "อุทัยธานี",
    "ubonratchathani": "อุบลราชธานี",
    "phuket": "ภูเก็ต",
}

def _slug_from_id(item_id):
    """Extract province slug from item ID like 'chaiyaphum_0042'."""
    parts = item_id.rsplit('_', 1)
    if len(parts) == 2 and parts[1].isdigit():
        raw_slug = parts[0]
        # Handle variant slugs like 'tak_backup_pre_improve'
        for known in SLUG_TO_PROVINCE:
            if raw_slug == known or raw_slug.startswith(known + '_'):
                return known
    return None

def _normalize_province(item):
    """Return canonical Thai province name from item ID slug."""
    slug = _slug_from_id(item.get('id', ''))
    if slug and slug in SLUG_TO_PROVINCE:
        return SLUG_TO_PROVINCE[slug]
    # Fallback: trust OCR province if it matches a known name
    ocr_prov = item.get('province') or item.get('ocr_province') or ''
    known_names = set(SLUG_TO_PROVINCE.values())
    if ocr_prov in known_names:
        return ocr_prov
    return ocr_prov or 'ไม่ทราบ'

def _extract_constituency_from_file(filepath):
    """Extract constituency number from filepath like 'เขตเลือกตั้งที่ 3/...'."""
    m = re.search(r'เขตเลือกตั้งที่\s*(\d+)', filepath or '')
    if m:
        return int(m.group(1))
    return None

def _classify_vote_type(item):
    """Classify vote type: แบ่งเขต, บัญชีรายชื่อ, ประชามติ, นอกเขต.
    
    Priority: filename > candidate count (for combined files) > OCR classification.
    """
    # 1) Classify from filename FIRST (most reliable)
    fname = item.get('file') or ''
    fname_lower = fname.lower()
    if any(k in fname for k in ['ประชามติ', 'มติ']):
        return 'ประชามติ'
    if any(k in fname_lower for k in ['อ.ส. 4', 'อ.ส.4', 'อส 4', '4-7', '4/7', '4ทับ7']):
        return 'ประชามติ'

    # 2) Detect combined files (both keywords in path, e.g. "ต.XXX-แบ่งเขต/บัญชีรายชื่อ.pdf")
    #    Also detect 'บช' (without parens/period) in folder names like 'นอกเขต บช/'
    has_bk = 'แบ่งเขต' in fname
    has_bn = any(k in fname for k in ['บัญชีรายชื่อ', 'บัญชี'])
    # Check for standalone 'บช' in path segments (folder or filename)
    import re as _re
    if not has_bn:
        has_bn = bool(_re.search(r'(?:^|[/\\\s(])บช(?:[/\\\s).]|$)', fname))
    if has_bk and has_bn:
        # Combined file: use candidate count to distinguish
        # แบ่งเขต typically has ≤10 candidates, บัญชีรายชื่อ has 11+
        n_cands = len(item.get('candidates') or [])
        if n_cands > 10:
            return 'บัญชีรายชื่อ'
        # Trust existing vote_type from postprocess.py if available
        existing = item.get('vote_type') or ''
        if existing in ('แบ่งเขต', 'บัญชีรายชื่อ'):
            return existing
        # Default: check parent folder
        norm_path = fname.replace('\\', '/')
        parent = '/'.join(norm_path.split('/')[:-1])
        if 'แบ่งเขต' in parent:
            return 'แบ่งเขต'
        return 'บัญชีรายชื่อ'

    # 3) Single keyword in path
    if has_bn:
        return 'บัญชีรายชื่อ'
    if has_bk:
        return 'แบ่งเขต'

    # 3b) นอกเขต — reclassify as proper vote type based on candidate count
    #    Out-of-area forms without explicit party list marker are constituency forms
    if 'นอกเขต' in fname or 'นอกราช' in fname:
        n_cands = len(item.get('candidates') or [])
        if n_cands > 10:
            return 'บัญชีรายชื่อ'
        return 'แบ่งเขต'

    # 4) Fall back to OCR classification / existing vote_type
    vt = item.get('vote_type') or item.get('ocr_vote_type') or ''
    if vt in ('แบ่งเขต', 'บัญชีรายชื่อ', 'ประชามติ', 'นอกเขต'):
        return vt
    # 5) Partial OCR match
    if 'บัญชี' in vt or 'บช' in vt:
        return 'บัญชีรายชื่อ'
    if 'เขต' in vt and 'นอก' not in vt:
        return 'แบ่งเขต'
    return vt or 'ไม่ระบุ'

def _consolidate_multipage_records(items):
    """Merge multi-page records for the same station into single records.

    Party list forms (บัญชีรายชื่อ) often span 2+ pages per station due to
    40+ party candidates. This merges consecutive pages (gap ≤ 2) from the
    same file and station into one consolidated record.
    Also applies to แบ่งเขต where duplicates exist.

    Two strategies:
    1) Records WITH station_no → group by (file, station_no, vote_type)
    2) Records WITHOUT station_no → group consecutive pages by (file, vote_type)
    """
    from collections import defaultdict

    # --- Pass 1: records with station_no ---
    groups = defaultdict(list)
    no_stn_items = []

    for item in items:
        stn = item.get('ocr_station_no') or item.get('station_no')
        if stn:
            key = (item.get('file', ''), str(stn), item.get('vote_type', ''))
            groups[key].append(item)
        else:
            no_stn_items.append(item)

    result = []
    merged_count = 0

    for key, recs in groups.items():
        if len(recs) == 1:
            result.append(recs[0])
            continue
        merged_count += _merge_consecutive_pages(recs, result)

    # --- Pass 2: records without station_no (use page proximity) ---
    no_stn_groups = defaultdict(list)
    for item in no_stn_items:
        key = (item.get('file', ''), item.get('vote_type', ''))
        no_stn_groups[key].append(item)

    no_stn_merged = 0
    for key, recs in no_stn_groups.items():
        if len(recs) == 1:
            result.append(recs[0])
            continue
        no_stn_merged += _merge_consecutive_pages(recs, result)

    merged_count += no_stn_merged
    print(f"  📑 Consolidated {merged_count} multi-page records (incl. {no_stn_merged} without station_no)")
    return result


def _merge_consecutive_pages(recs, result_list):
    """Sort records by page, merge consecutive pages (gap ≤ 2, max 4 per group).
    Appends results to result_list. Returns number of records saved by merging."""
    recs.sort(key=lambda r: r.get('page', 0) or 0)

    sub_groups = []
    current_sub = [recs[0]]
    for i in range(1, len(recs)):
        prev_page = current_sub[-1].get('page', 0) or 0
        curr_page = recs[i].get('page', 0) or 0
        if curr_page - prev_page <= 2 and len(current_sub) < 4:
            current_sub.append(recs[i])
        else:
            sub_groups.append(current_sub)
            current_sub = [recs[i]]
    sub_groups.append(current_sub)

    saved = 0
    for sub in sub_groups:
        if len(sub) == 1:
            result_list.append(sub[0])
        else:
            result_list.append(_merge_page_group(sub))
            saved += len(sub) - 1
    return saved


def _merge_page_group(recs):
    """Merge a group of consecutive page records into one."""
    base = dict(recs[0])  # shallow copy of first record as base

    # Collect all pages and images
    all_pages = [r.get('page') for r in recs if r.get('page') is not None]
    all_images = [r.get('image_url') for r in recs if r.get('image_url')]

    base['page'] = all_pages[0] if all_pages else None
    base['_merged_pages'] = all_pages
    if len(all_images) > 1:
        base['_extra_images'] = all_images[1:]

    # Combine candidate lists (each page has different candidates)
    all_candidates = []
    seen_numbers = set()
    for r in recs:
        for c in (r.get('candidates') or []):
            cno = c.get('number') or c.get('candidate_no')
            if cno and cno not in seen_numbers:
                seen_numbers.add(cno)
                all_candidates.append(c)
            elif not cno:
                all_candidates.append(c)
    base['candidates'] = all_candidates

    # Ballot data: use first non-None value from any page
    ballot_fields = [
        'registered_voters', 'turnout', 'ballots_received',
        'valid_ballots', 'invalid_ballots', 'no_vote_ballots',
        'remaining_ballots', 'total_votes'
    ]
    for field in ballot_fields:
        if base.get(field) is None:
            for r in recs[1:]:
                if r.get(field) is not None:
                    base[field] = r[field]
                    break

    # Update ID to indicate merged
    base['_consolidated'] = True
    base['_consolidated_count'] = len(recs)

    return base


def _infer_station_no_from_filename(items):
    """Infer station_no from filename patterns for records that lack it.

    Common patterns: หน่วยที่ X, หน่วย X, หน่วยที่X
    """
    import re
    inferred = 0
    for item in items:
        if item.get('ocr_station_no') or item.get('station_no'):
            continue
        fname = item.get('file', '')
        # Try multiple patterns: หน่วยที่ X, หน่วย X, ชุดที่ X
        m = re.search(r'หน่วย(?:ที่)?\s*(\d+)', fname)
        if not m:
            m = re.search(r'ชุดที่\s*(\d+)', fname)
            if m:
                # Use 'ชุด' prefix to avoid collisions with regular station numbers
                stn = f"ชุด{m.group(1)}"
                item['ocr_station_no'] = stn
                item['_station_no_inferred'] = True
                inferred += 1
                continue
        if m:
            stn = m.group(1)
            item['ocr_station_no'] = stn
            item['_station_no_inferred'] = True
            inferred += 1
    if inferred:
        print(f"  🔍 Inferred station_no from filename for {inferred} records")
    return items


def _balance_vote_types(items):
    """Balance แบ่งเขต and บัญชีรายชื่อ record counts per station.

    For each unique station (province, constituency, station_no), ensures
    both vote types have the same number of records by trimming only the
    excess from the larger type (keeping the best-quality records).

    Records without station_no are kept as-is.
    """
    from collections import defaultdict

    ballot_fields = [
        'registered_voters', 'turnout', 'ballots_received',
        'valid_ballots', 'invalid_ballots', 'no_vote_ballots',
        'remaining_ballots', 'total_votes'
    ]

    def score(r):
        n_cands = len(r.get('candidates') or [])
        n_ballot = sum(1 for f in ballot_fields if r.get(f) is not None)
        is_consolidated = 1 if r.get('_consolidated') else 0
        return (n_cands, n_ballot, is_consolidated)

    # Group by (province, constituency, station_no)
    stations = defaultdict(lambda: defaultdict(list))
    ungroupable = []

    for item in items:
        stn = item.get('ocr_station_no') or item.get('station_no')
        cons = item.get('constituency')
        prov = item.get('province', '')
        vt = item.get('vote_type', '')
        if stn and cons and vt in ('แบ่งเขต', 'บัญชีรายชื่อ'):
            key = (prov, str(cons), str(stn))
            stations[key][vt].append(item)
        else:
            ungroupable.append(item)

    result = list(ungroupable)
    trimmed = 0

    for key, vt_groups in stations.items():
        bk = vt_groups.get('แบ่งเขต', [])
        bn = vt_groups.get('บัญชีรายชื่อ', [])

        if not bk or not bn:
            # Only one vote type → keep all
            result.extend(bk)
            result.extend(bn)
            continue

        # Both types exist → trim larger to match smaller
        target = min(len(bk), len(bn))

        # Sort by quality descending, keep top `target`
        bk.sort(key=score, reverse=True)
        bn.sort(key=score, reverse=True)

        trimmed += len(bk) - target + len(bn) - target
        result.extend(bk[:target])
        result.extend(bn[:target])

    # Per-province summary
    by_prov = defaultdict(lambda: [0, 0])
    for item in result:
        prov = item.get('province', '?')
        if item.get('vote_type') == 'แบ่งเขต':
            by_prov[prov][0] += 1
        elif item.get('vote_type') == 'บัญชีรายชื่อ':
            by_prov[prov][1] += 1

    for prov, (bk, bn) in by_prov.items():
        ratio = bn / bk if bk > 0 else 999
        print(f"    {prov}: แบ่งเขต={bk}, บัญชีฯ={bn} (ratio {ratio:.2f}x)")

    print(f"  ⚖️  Balanced: trimmed {trimmed} excess records")
    return result


ECT_REF_PATH = os.path.join(DATA_DIR, 'ect_candidates_reference.json')

def _load_ect_reference():
    """Load ECT candidate reference data. Returns dict { province: { zone_str: [candidates] } }."""
    if not os.path.exists(ECT_REF_PATH):
        print(f"[WARN] ECT reference not found: {ECT_REF_PATH}")
        return {}
    with open(ECT_REF_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def _enrich_with_ect(item, ect_ref):
    """Enrich item with ECT reference data, normalize names/parties, and rebuild candidate list.

    Strategy (ECT = ground truth):
    1. Build lookup {candidate_no: {name, party}} from ECT
    2. For each OCR candidate matched by number → override name & party with ECT
    3. Remove ghost candidates (number not in ECT AND no real votes)
    4. Fill missing ECT candidates (votes=None) so every page has the full list
    5. Sort by candidate number for consistency
    """
    if item.get('vote_type') != 'แบ่งเขต':
        return

    prov = item.get('province', '')
    cons = str(item.get('constituency', ''))

    if prov not in ect_ref or cons not in ect_ref[prov]:
        return

    ect_cands = ect_ref[prov][cons]
    ect_by_no = {c['no']: c for c in ect_cands}
    ect_count = len(ect_cands)

    item['ect_candidates'] = ect_cands
    item['ect_candidate_count'] = ect_count

    ocr_cands = item.get('candidates') or []
    if not ocr_cands:
        # No OCR candidates at all — nothing to normalize
        return

    # --- Phase 1: Match OCR → ECT by number, override name+party ---
    matched_nos = set()
    kept = []
    removed = []

    for c in ocr_cands:
        num = c.get('number')
        if num in ect_by_no:
            # Override name + party with ECT ground truth
            ect = ect_by_no[num]
            c['name'] = ect['name']
            c['party'] = ect['party']
            c['_ect_matched'] = True
            matched_nos.add(num)
            kept.append(c)
        else:
            # Not in ECT — ghost candidate?
            name = c.get('name') or ''
            votes = c.get('votes')
            is_ghost = (not name.strip()) or (votes is None) or (votes == 0)
            if is_ghost:
                removed.append(c)
            else:
                # Has real votes but unknown number — keep but flag
                c['_ect_matched'] = False
                kept.append(c)

    if removed:
        item['_candidates_auto_fixed'] = True
        item['_candidates_removed'] = len(removed)

    # --- Phase 2: Fill missing ECT candidates not found in OCR ---
    for no, ect in sorted(ect_by_no.items()):
        if no not in matched_nos:
            kept.append({
                'number': no,
                'name': ect['name'],
                'party': ect['party'],
                'votes': None,
                '_ect_matched': True,
                '_ect_filled': True,   # not in OCR, filled from ECT
            })

    # --- Phase 3: Sort by candidate number ---
    def sort_key(c):
        n = c.get('number')
        return (n if isinstance(n, int) else 9999, str(c.get('name', '')))
    kept.sort(key=sort_key)

    item['candidates'] = kept

    # Check final count vs ECT
    final_count = len(kept)
    if final_count != ect_count:
        item['_candidate_mismatch'] = True
        item['_candidate_mismatch_detail'] = f"OCR={final_count} vs ECT={ect_count}"

DEBUG_DIR = os.path.join(DATA_DIR, 'ocr_debug_vision')
REVIEW_APP_DIR = os.path.join(PROJECT_ROOT, 'review-app')
PUBLIC_DATA_DIR = os.path.join(REVIEW_APP_DIR, 'public', 'data')
PUBLIC_IMG_DIR = os.path.join(REVIEW_APP_DIR, 'public', 'images')


def sanitize_filename(name):
    """Make filename safe for URLs."""
    return re.sub(r'[^\w.-]', '_', name)


def main():
    # Load ECT candidate reference
    ect_ref = _load_ect_reference()
    if ect_ref:
        total_ect = sum(len(cands) for prov in ect_ref.values() for cands in prov.values())
        print(f"[ECT] Reference loaded: {total_ect} candidates across {sum(len(z) for z in ect_ref.values())} constituencies")

    # Scan for ALL OCR result files: ocr_multimodel_*.json AND ocr_vision_*.json
    import glob
    _SKIP_SUFFIXES = ('_backup', '_pre_', '_run1', '_test', '_backup_')
    def _is_main_file(path):
        """Exclude backup/test files like _backup.json, _pre_z7reocr.json, etc."""
        base = os.path.basename(path).replace('.json', '')
        prefix = base.split('ocr_multimodel_')[-1] if 'ocr_multimodel_' in base else base.split('ocr_vision_')[-1]
        # Main file: slug is a simple province name (no underscores after province)
        # Backup: has extra suffixes like chaiyaphum_backup, tak_run1_gemini_only
        # Heuristic: if slug contains '_' and any skip word, exclude it
        for skip in _SKIP_SUFFIXES:
            if skip in prefix:
                return False
        return True

    multimodel_files = sorted(f for f in glob.glob(os.path.join(DATA_DIR, 'ocr_multimodel_*.json')) if _is_main_file(f))
    vision_files = sorted(f for f in glob.glob(os.path.join(DATA_DIR, 'ocr_vision_*.json')) if _is_main_file(f))

    # Normalize file path for dedup: strip province prefix, normalize slashes
    _PROVINCE_PREFIXES = re.compile(r'^จังหวัด[^/\\]+[/\\]')
    def _norm_file(path):
        p = (path or '').replace('\\', '/')
        p = _PROVINCE_PREFIXES.sub('', p)
        return p

    # Load multimodel first, then supplement with vision-only pages
    results = []
    seen_file_page = set()  # track (normalized_file, page) to avoid duplicates

    for jf in multimodel_files:
        slug = os.path.basename(jf).replace('ocr_multimodel_', '').replace('.json', '')
        with open(jf, 'r', encoding='utf-8') as f:
            items = json.load(f)
        for item in items:
            item['_source_slug'] = slug
            item['_source_type'] = 'multimodel'
            seen_file_page.add((_norm_file(item.get('file', '')), item.get('page')))
        results.extend(items)
        print(f"  📄 {os.path.basename(jf)}: {len(items)} items (multimodel)")

    # Add vision records that don't overlap with multimodel (by normalized file+page)
    for jf in vision_files:
        slug = os.path.basename(jf).replace('ocr_vision_', '').replace('.json', '')
        with open(jf, 'r', encoding='utf-8') as f:
            items = json.load(f)
        new_items = []
        for item in items:
            key = (_norm_file(item.get('file', '')), item.get('page'))
            if key not in seen_file_page:
                item['_source_slug'] = slug
                item['_source_type'] = 'vision'
                new_items.append(item)
                seen_file_page.add(key)
        results.extend(new_items)
        if new_items:
            print(f"  📄 {os.path.basename(jf)}: +{len(new_items)} vision-only items (of {len(items)} total)")

    if not results:
        print(f"[ERROR] No ocr_multimodel_*.json or ocr_vision_*.json files found in {DATA_DIR}")
        sys.exit(1)

    n_provinces = len(set(os.path.basename(f).replace('ocr_multimodel_','').replace('ocr_vision_','').replace('.json','') for f in multimodel_files + vision_files))
    print(f"📄 Loaded {len(results)} OCR results from {n_provinces} province(s)")

    os.makedirs(PUBLIC_DATA_DIR, exist_ok=True)
    os.makedirs(PUBLIC_IMG_DIR, exist_ok=True)

    review_items = []
    images_copied = 0

    for i, r in enumerate(results):
        slug = r.get('_source_slug', 'unknown')
        item_id = f"{slug}_{i:04d}"

        # Find matching debug files
        file_base = r.get('file', '')
        page = r.get('page', 1)
        # Reconstruct debug filename
        pdf_basename = os.path.basename(file_base)
        safe_base = re.sub(r'[^\w.-]', '_', pdf_basename)

        # Look for image (local debug PNG)
        img_name = f"{safe_base}_p{page}.png"
        img_src = os.path.join(DEBUG_DIR, img_name)
        image_url = None
        if os.path.exists(img_src):
            safe_img = sanitize_filename(img_name)
            dst = os.path.join(PUBLIC_IMG_DIR, safe_img)
            if not os.path.exists(dst):
                shutil.copy2(img_src, dst)
            image_url = f"./images/{safe_img}"
            images_copied += 1

        # Drive PDF preview URL (for Drive-mode OCR results)
        pdf_url = None
        drive_file_id = r.get('drive_file_id')
        if drive_file_id:
            pdf_url = f"https://drive.google.com/file/d/{drive_file_id}/preview"

        # Look for OCR text (debug file first, then from OCR result JSON)
        txt_name = f"{safe_base}_p{page}_vision.txt"
        txt_src = os.path.join(DEBUG_DIR, txt_name)
        ocr_text = None
        if os.path.exists(txt_src):
            with open(txt_src, 'r', encoding='utf-8') as f:
                ocr_text = f.read()
        elif r.get('ocr_text'):
            ocr_text = r['ocr_text']

        # Re-parse OCR text to get confidence data (only for vision source)
        parsed = {}
        is_multimodel = r.get('_source_type') == 'multimodel'
        if ocr_text and parse_ss518_text and not is_multimodel:
            parsed = parse_ss518_text(ocr_text)

        # Build review item
        # For multimodel (Gemini): use structured JSON directly
        # For vision: use re-parsed data with confidence
        if is_multimodel:
            item = {
                "id": item_id,
                "file": r.get('file', ''),
                "page": page,
                "total_pages": r.get('total_pages'),
                "province": r.get('province'),
                "constituency": r.get('constituency'),
                "district": r.get('district'),
                "sub_district": r.get('sub_district'),
                "station_range": r.get('station_range'),
                "vote_type": r.get('vote_type'),
                "ocr_vote_type": r.get('vote_type'),
                "ocr_province": r.get('province'),
                "ocr_constituency": r.get('constituency'),
                "ocr_station_no": r.get('station_no'),
                "ocr_sub_district": r.get('sub_district'),
                "ocr_district": r.get('district'),
                "registered_voters": r.get('registered_voters'),
                "turnout": r.get('turnout'),
                "ballots_received": r.get('ballots_received'),
                "valid_ballots": r.get('valid_ballots'),
                "invalid_ballots": r.get('invalid_ballots'),
                "no_vote_ballots": r.get('no_vote_ballots'),
                "remaining_ballots": r.get('remaining_ballots'),
                "total_votes": r.get('total_votes'),
                "candidates": r.get('candidates', []),
                "confidence": {},
                "image_url": image_url,
                "pdf_url": pdf_url,
                "drive_view_url": r.get('drive_view_url'),
                "ocr_text": ocr_text,
                "is_back_page": r.get('is_back_page', False),
                "model": r.get('model'),
                "model_variant": r.get('model_variant'),
                "_source_type": "multimodel",
            }
        else:
            item = {
                "id": item_id,
                "file": r.get('file', ''),
                "page": page,
                "total_pages": r.get('total_pages'),
                "province": r.get('province') or r.get('ocr_province'),
                "constituency": r.get('constituency') or r.get('ocr_constituency'),
                "district": r.get('district') or r.get('ocr_district'),
                "sub_district": r.get('sub_district') or r.get('ocr_sub_district'),
                "station_range": r.get('station_range'),
                "vote_type": r.get('vote_type') or r.get('ocr_vote_type'),
                "ocr_vote_type": parsed.get('ocr_vote_type') or r.get('ocr_vote_type'),
                "ocr_province": parsed.get('ocr_province') or r.get('ocr_province'),
                "ocr_constituency": parsed.get('ocr_constituency') or r.get('ocr_constituency'),
                "ocr_station_no": parsed.get('ocr_station_no') or r.get('ocr_station_no'),
                "ocr_sub_district": parsed.get('ocr_sub_district') or r.get('ocr_sub_district'),
                "ocr_district": parsed.get('ocr_district') or r.get('ocr_district'),
                "registered_voters": parsed.get('registered_voters') or r.get('registered_voters'),
                "turnout": parsed.get('turnout') or r.get('turnout'),
                "ballots_received": parsed.get('ballots_received') or r.get('ballots_received'),
                "valid_ballots": parsed.get('valid_ballots') or r.get('valid_ballots'),
                "invalid_ballots": parsed.get('invalid_ballots') or r.get('invalid_ballots'),
                "no_vote_ballots": parsed.get('no_vote_ballots') or r.get('no_vote_ballots'),
                "remaining_ballots": parsed.get('remaining_ballots') or r.get('remaining_ballots'),
                "total_votes": parsed.get('total_votes') or r.get('total_votes'),
                "candidates": parsed.get('candidates') or r.get('candidates', []),
                "confidence": parsed.get('_confidence', {}),
                "image_url": image_url,
                "pdf_url": pdf_url,
                "drive_view_url": r.get('drive_view_url'),
                "ocr_text": ocr_text,
                "is_back_page": r.get('is_back_page', False),
                "_source_type": r.get('_source_type', 'vision'),
            }
        # Normalize province name from slug (override OCR garbage)
        item['province'] = _normalize_province(item)
        # Classify vote type from filename/OCR
        item['vote_type'] = _classify_vote_type(item)
        # Extract constituency from filepath (more reliable than OCR)
        file_cons = _extract_constituency_from_file(item.get('file'))
        if file_cons is not None:
            item['constituency'] = file_cons
        # Enrich with ECT reference + auto-fix candidates
        if ect_ref:
            _enrich_with_ect(item, ect_ref)
        review_items.append(item)

    # Filter out back pages with no data
    content_items = [item for item in review_items if not item.get('is_back_page')]
    print(f"📋 Content pages: {len(content_items)} (filtered {len(review_items) - len(content_items)} back pages)")

    # Infer station_no from filename for records that lack it
    content_items = _infer_station_no_from_filename(content_items)

    # Consolidate multi-page records (e.g. 2-page party list forms) into single records
    content_items = _consolidate_multipage_records(content_items)
    print(f"📋 After consolidation: {len(content_items)} records")

    # Balance vote types: trim excess records per station so แบ่งเขต ≈ บัญชีรายชื่อ
    content_items = _balance_vote_types(content_items)
    print(f"📋 After balancing: {len(content_items)} records")

    # Also create a version with ALL items for reference
    out_all = os.path.join(PUBLIC_DATA_DIR, 'review_data.json')
    with open(out_all, 'w', encoding='utf-8') as f:
        json.dump(content_items, f, ensure_ascii=False, indent=2)
    print(f"💾 Saved {len(content_items)} items to {out_all}")
    print(f"🖼️  Images copied: {images_copied}")

    # Stats
    low_conf = sum(1 for item in content_items
                   if item.get('confidence') and
                   any(v and v.startswith('low') for v in item['confidence'].values()))
    no_data = sum(1 for item in content_items
                  if all(item.get(f) is None for f in
                         ['registered_voters', 'turnout', 'ballots_received',
                          'valid_ballots', 'invalid_ballots', 'remaining_ballots']))
    with_cands = sum(1 for item in content_items if item.get('candidates'))

    # ECT enrichment stats
    ect_enriched = sum(1 for item in content_items if item.get('ect_candidates'))
    auto_fixed = sum(1 for item in content_items if item.get('_candidates_auto_fixed'))
    mismatched = sum(1 for item in content_items if item.get('_candidate_mismatch'))

    print(f"\n[STATS]:")
    print(f"  Low confidence: {low_conf}")
    print(f"  No ballot data: {no_data}")
    print(f"  With candidates: {with_cands}")
    if ect_ref:
        print(f"  ECT enriched: {ect_enriched}")
        print(f"  Auto-fixed candidates: {auto_fixed}")
        print(f"  Candidate mismatches remaining: {mismatched}")
    print(f"\n[DONE] Run 'cd review-app && npm install && npm run dev' to start the review app.")


if __name__ == '__main__':
    main()
