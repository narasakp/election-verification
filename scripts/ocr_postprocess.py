# -*- coding: utf-8 -*-
"""Post-processing module for OCR results.

Applies mathematical constraints and auto-correction to improve accuracy.
Can be used standalone or integrated into ocr_multimodel.py pipeline.

Constraints:
  R1: ballots_received = valid + invalid + no_vote + remaining
  R2: turnout = valid + invalid + no_vote  (i.e. turnout = received - remaining)
  R3: sum(candidate_votes) <= valid_ballots
  R4: turnout <= registered_voters
  R5: remaining = ballots_received - turnout
  R6: total_votes == sum(candidate_votes)
"""
import json
import os
import sys
import copy

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def auto_correct_ballots(item):
    """Apply ballot reconciliation constraints to auto-correct one missing/wrong value.
    
    Formula: ballots_received = valid + invalid + no_vote + remaining
    Also:    remaining = ballots_received - turnout
             turnout = valid + invalid + no_vote
    
    Returns: (corrected_item, corrections_list)
    """
    corrections = []
    item = copy.deepcopy(item)
    
    r = item.get('ballots_received')
    v = item.get('valid_ballots')
    inv = item.get('invalid_ballots')
    nv = item.get('no_vote_ballots')
    rem = item.get('remaining_ballots')
    turnout = item.get('turnout')
    voters = item.get('registered_voters')
    
    fields = {'ballots_received': r, 'valid_ballots': v, 'invalid_ballots': inv,
              'no_vote_ballots': nv, 'remaining_ballots': rem}
    
    # ─── Rule R5: remaining = ballots_received - turnout ───
    if r is not None and turnout is not None and rem is not None:
        expected_rem = r - turnout
        if expected_rem >= 0 and rem != expected_rem:
            corrections.append({
                'field': 'remaining_ballots',
                'rule': 'R5',
                'old': rem,
                'new': expected_rem,
                'reason': f'remaining = received({r}) - turnout({turnout}) = {expected_rem}'
            })
            rem = expected_rem
            item['remaining_ballots'] = expected_rem
    
    # ─── Rule R5b: if remaining is None, compute from received - turnout ───
    if rem is None and r is not None and turnout is not None:
        expected_rem = r - turnout
        if expected_rem >= 0:
            corrections.append({
                'field': 'remaining_ballots',
                'rule': 'R5_fill',
                'old': None,
                'new': expected_rem,
                'reason': f'remaining = received({r}) - turnout({turnout}) = {expected_rem}'
            })
            rem = expected_rem
            item['remaining_ballots'] = expected_rem
    
    # ─── Rule R2: turnout = valid + invalid + no_vote ───
    if v is not None and inv is not None and nv is not None:
        expected_turnout = v + inv + nv
        if turnout is not None and turnout != expected_turnout:
            # Safety: don't override if it would make remaining negative
            would_cause_neg_rem = (r is not None and r - expected_turnout < 0)
            if not would_cause_neg_rem:
                corrections.append({
                    'field': 'turnout',
                    'rule': 'R2',
                    'old': turnout,
                    'new': expected_turnout,
                    'reason': f'turnout = valid({v}) + invalid({inv}) + no_vote({nv}) = {expected_turnout}'
                })
                turnout = expected_turnout
                item['turnout'] = expected_turnout
        elif turnout is None:
            corrections.append({
                'field': 'turnout',
                'rule': 'R2_fill',
                'old': None,
                'new': expected_turnout,
                'reason': f'turnout = valid({v}) + invalid({inv}) + no_vote({nv}) = {expected_turnout}'
            })
            turnout = expected_turnout
            item['turnout'] = expected_turnout
    
    # ─── Rule R1: received = valid + invalid + no_vote + remaining ───
    ballot_fields = [v, inv, nv, rem]
    none_count = sum(1 for x in ballot_fields if x is None)
    
    if r is not None and none_count == 0:
        expected = v + inv + nv + rem
        if r != expected:
            # All 4 components present but don't sum to received
            # Try to fix the most likely wrong field
            diff = r - expected
            
            # If diff is small and remaining is the likely culprit
            new_rem = rem + diff
            if abs(diff) < 50 and new_rem >= 0:  # small difference, non-negative result
                corrections.append({
                    'field': 'remaining_ballots',
                    'rule': 'R1_fix_remaining',
                    'old': rem,
                    'new': new_rem,
                    'reason': f'Adjusting remaining by {diff:+d} to match received({r})'
                })
                item['remaining_ballots'] = new_rem
    
    elif r is not None and none_count == 1:
        # Exactly one field missing — compute it
        if v is None:
            computed = r - (inv + nv + rem)
            if computed >= 0:
                corrections.append({
                    'field': 'valid_ballots', 'rule': 'R1_solve',
                    'old': None, 'new': computed,
                    'reason': f'valid = received({r}) - invalid({inv}) - no_vote({nv}) - remaining({rem})'
                })
                item['valid_ballots'] = computed
        elif inv is None:
            computed = r - (v + nv + rem)
            if computed >= 0:
                corrections.append({
                    'field': 'invalid_ballots', 'rule': 'R1_solve',
                    'old': None, 'new': computed,
                    'reason': f'invalid = received({r}) - valid({v}) - no_vote({nv}) - remaining({rem})'
                })
                item['invalid_ballots'] = computed
        elif nv is None:
            computed = r - (v + inv + rem)
            if computed >= 0:
                corrections.append({
                    'field': 'no_vote_ballots', 'rule': 'R1_solve',
                    'old': None, 'new': computed,
                    'reason': f'no_vote = received({r}) - valid({v}) - invalid({inv}) - remaining({rem})'
                })
                item['no_vote_ballots'] = computed
        elif rem is None:
            computed = r - (v + inv + nv)
            if computed >= 0:
                corrections.append({
                    'field': 'remaining_ballots', 'rule': 'R1_solve',
                    'old': None, 'new': computed,
                    'reason': f'remaining = received({r}) - valid({v}) - invalid({inv}) - no_vote({nv})'
                })
                item['remaining_ballots'] = computed
    
    elif r is None and none_count == 0:
        # received missing, all components present
        computed = v + inv + nv + rem
        corrections.append({
            'field': 'ballots_received', 'rule': 'R1_solve',
            'old': None, 'new': computed,
            'reason': f'received = valid({v}) + invalid({inv}) + no_vote({nv}) + remaining({rem})'
        })
        item['ballots_received'] = computed
    
    # ─── Rule R4: turnout <= registered_voters ───
    turnout = item.get('turnout')
    voters = item.get('registered_voters')
    if turnout is not None and voters is not None and turnout > voters:
        # Flag but don't auto-correct — could be either field wrong
        item['_flag_turnout_exceeds_voters'] = True
    
    # ─── Rule R6: total_votes = sum(candidate_votes) ───
    # Only apply if candidate extraction looks complete (sum is reasonable)
    cands = item.get('candidates', [])
    cand_votes = [c.get('votes') for c in cands if c.get('votes') is not None]
    if cand_votes:
        computed_total = sum(cand_votes)
        current_total = item.get('total_votes')
        valid = item.get('valid_ballots')
        
        # Safety: skip R6 if sum(candidate_votes) is <50% of valid_ballots
        # This means OCR likely missed some candidates
        skip_r6 = False
        if valid and valid > 0 and computed_total < valid * 0.5:
            skip_r6 = True
            item['_flag_incomplete_candidates'] = True
        
        if not skip_r6 and current_total != computed_total:
            corrections.append({
                'field': 'total_votes', 'rule': 'R6',
                'old': current_total, 'new': computed_total,
                'reason': f'total_votes = sum(candidate_votes) = {computed_total}'
            })
            item['total_votes'] = computed_total
    
    # ─── Rule R3: sum(candidate_votes) <= valid_ballots ───
    valid = item.get('valid_ballots')
    if cand_votes and valid is not None:
        total_cv = sum(cand_votes)
        if total_cv > valid:
            item['_flag_votes_exceed_valid'] = True
    
    if corrections:
        item['_auto_corrections'] = corrections
    
    return item, corrections


def postprocess_results(results):
    """Apply auto-correction to all results."""
    corrected = []
    total_corrections = 0
    items_corrected = 0
    
    for item in results:
        if item.get('is_back_page') or not item.get('candidates'):
            corrected.append(item)
            continue
        
        corrected_item, corrections = auto_correct_ballots(item)
        corrected.append(corrected_item)
        
        if corrections:
            items_corrected += 1
            total_corrections += len(corrections)
    
    return corrected, total_corrections, items_corrected


# ─── CLI ────────────────────────────────────────────────────────────

def main():
    """Standalone: apply auto-correction to an OCR results file."""
    import argparse
    parser = argparse.ArgumentParser(description='Post-process OCR results with auto-correction')
    parser.add_argument('input', help='Input JSON file (e.g. data/ocr_multimodel_tak.json)')
    parser.add_argument('--output', help='Output file (default: overwrite input)')
    parser.add_argument('--dry-run', action='store_true', help='Show corrections without saving')
    args = parser.parse_args()
    
    # Load
    with open(args.input, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    print(f"Loaded {len(results)} items from {args.input}")
    
    # Process
    corrected, total_corrections, items_corrected = postprocess_results(results)
    
    # Report
    print(f"\n{'='*60}")
    print(f"AUTO-CORRECTION REPORT")
    print(f"{'='*60}")
    print(f"  Items processed: {len(results)}")
    print(f"  Items corrected: {items_corrected}")
    print(f"  Total corrections: {total_corrections}")
    
    for item in corrected:
        corrs = item.get('_auto_corrections', [])
        if corrs:
            station = item.get('station_no')
            page = item.get('page')
            print(f"\n  --- p{page} station={station} ---")
            for c in corrs:
                print(f"    [{c['rule']}] {c['field']}: {c['old']} → {c['new']}")
                print(f"           {c['reason']}")
        
        if item.get('_flag_turnout_exceeds_voters'):
            print(f"    ⚠️  turnout({item['turnout']}) > voters({item['registered_voters']})")
        if item.get('_flag_votes_exceed_valid'):
            cand_sum = sum(c.get('votes', 0) for c in item.get('candidates', []) if c.get('votes'))
            print(f"    ⚠️  candidate_sum({cand_sum}) > valid({item['valid_ballots']})")
    
    # Save
    if not args.dry_run:
        output_path = args.output or args.input
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(corrected, f, ensure_ascii=False, indent=2)
        print(f"\n  Saved to: {output_path}")
    else:
        print(f"\n  [DRY RUN] No files written.")


if __name__ == '__main__':
    main()
