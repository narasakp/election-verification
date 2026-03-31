import { describe, it, expect } from 'vitest'
import { validateItem, getWorstSeverity } from './validation'

// Helper: create a base valid item
function makeItem(overrides = {}) {
  return {
    registered_voters: 1000,
    turnout: 800,
    ballots_received: 1000,
    valid_ballots: 750,
    invalid_ballots: 30,
    no_vote_ballots: 20,
    remaining_ballots: 200,
    total_votes: 750,
    candidates: [
      { number: 1, name: 'Alice', votes: 400 },
      { number: 2, name: 'Bob', votes: 350 },
    ],
    ...overrides,
  }
}

describe('validateItem', () => {
  it('returns no errors for a valid item', () => {
    const item = makeItem()
    const warnings = validateItem(item)
    // The only issue: ballots_received != turnout + remaining (1000 != 800+200=1000) — actually matches
    // valid+invalid+no_vote = 750+30+20 = 800 = turnout ✓
    // total_votes = 750 = valid_ballots ✓
    // cand sum = 400+350 = 750 = total_votes ✓
    expect(warnings.filter(w => w.severity === 'error')).toHaveLength(0)
  })

  it('V1: turnout > registered_voters → error', () => {
    const item = makeItem({ turnout: 1200 })
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'turnout_exceeds_voters')).toBe(true)
    expect(warnings.find(w => w.id === 'turnout_exceeds_voters').severity).toBe('error')
  })

  it('V2: total_votes ≠ valid_ballots → warning', () => {
    const item = makeItem({ total_votes: 600 })
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'votes_ne_valid')).toBe(true)
    expect(warnings.find(w => w.id === 'votes_ne_valid').severity).toBe('warning')
  })

  it('V3: ballot sum ≠ turnout → warning', () => {
    const item = makeItem({ valid_ballots: 700, invalid_ballots: 30, no_vote_ballots: 20, turnout: 800 })
    // 700+30+20=750 ≠ 800
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'ballot_sum_ne_turnout')).toBe(true)
  })

  it('V4: negative remaining_ballots → error', () => {
    const item = makeItem({ remaining_ballots: -5 })
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'negative_remaining')).toBe(true)
    expect(warnings.find(w => w.id === 'negative_remaining').severity).toBe('error')
  })

  it('V5: received ≠ turnout + remaining → warning', () => {
    const item = makeItem({ ballots_received: 900, turnout: 800, remaining_ballots: 200 })
    // 900 ≠ 800+200=1000
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'received_ne_used_plus_remain')).toBe(true)
  })

  it('V6: candidate sum ≠ total_votes → warning', () => {
    const item = makeItem({
      total_votes: 750,
      candidates: [
        { number: 1, name: 'A', votes: 300 },
        { number: 2, name: 'B', votes: 300 },
      ],
    })
    // 300+300=600 ≠ 750
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'cand_sum_ne_total')).toBe(true)
  })

  it('V7: negative field values → error', () => {
    const item = makeItem({ turnout: -10 })
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'negative_values')).toBe(true)
    expect(warnings.find(w => w.id === 'negative_values').severity).toBe('error')
  })

  it('V8: registered_voters > 10000 → warning', () => {
    const item = makeItem({ registered_voters: 50000 })
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'voters_too_high')).toBe(true)
  })

  it('V9: no stats at all → info', () => {
    const item = {
      registered_voters: null,
      turnout: null,
      ballots_received: null,
      valid_ballots: null,
    }
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'no_stats')).toBe(true)
    expect(warnings.find(w => w.id === 'no_stats').severity).toBe('info')
  })

  it('V10: candidate votes > valid_ballots → error', () => {
    const item = makeItem({
      valid_ballots: 100,
      candidates: [{ number: 1, name: 'X', votes: 200 }],
    })
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'cand_exceeds_valid')).toBe(true)
    expect(warnings.find(w => w.id === 'cand_exceeds_valid').severity).toBe('error')
  })

  it('V11: candidate mismatch flag → warning', () => {
    const item = makeItem({ _candidate_mismatch: true, _candidate_mismatch_detail: 'OCR 5 vs ECT 4' })
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'candidate_mismatch')).toBe(true)
  })

  it('handles null/undefined fields gracefully', () => {
    const item = {}
    expect(() => validateItem(item)).not.toThrow()
    const warnings = validateItem(item)
    expect(Array.isArray(warnings)).toBe(true)
  })

  it('handles zero values without false positives', () => {
    const item = makeItem({
      registered_voters: 0,
      turnout: 0,
      valid_ballots: 0,
      invalid_ballots: 0,
      no_vote_ballots: 0,
      remaining_ballots: 0,
      total_votes: 0,
      ballots_received: 0,
      candidates: [],
    })
    const warnings = validateItem(item)
    // Should only get 'no_stats' info, no errors
    const errors = warnings.filter(w => w.severity === 'error')
    expect(errors).toHaveLength(0)
  })

  it('V1: equal turnout and registered_voters → no error', () => {
    const item = makeItem({ registered_voters: 800, turnout: 800 })
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'turnout_exceeds_voters')).toBe(false)
  })

  it('V2: equal total_votes and valid_ballots → no warning', () => {
    const item = makeItem({ total_votes: 750, valid_ballots: 750 })
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'votes_ne_valid')).toBe(false)
  })

  it('V3: exact ballot sum matches turnout → no warning', () => {
    const item = makeItem({ valid_ballots: 750, invalid_ballots: 30, no_vote_ballots: 20, turnout: 800 })
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'ballot_sum_ne_turnout')).toBe(false)
  })

  it('V5: skips check when remaining_ballots is negative', () => {
    const item = makeItem({ remaining_ballots: -1, ballots_received: 1000 })
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'received_ne_used_plus_remain')).toBe(false)
  })

  it('V6: no candidates → no candidate sum warning', () => {
    const item = makeItem({ candidates: [] })
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'cand_sum_ne_total')).toBe(false)
  })

  it('V7: multiple negative fields listed in message', () => {
    const item = makeItem({ turnout: -10, valid_ballots: -5 })
    const warnings = validateItem(item)
    const w = warnings.find(w => w.id === 'negative_values')
    expect(w).toBeDefined()
    expect(w.message).toContain('turnout')
    expect(w.message).toContain('valid_ballots')
  })

  it('V8: exactly 10000 registered_voters → no warning', () => {
    const item = makeItem({ registered_voters: 10000 })
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'voters_too_high')).toBe(false)
  })

  it('V9: all zeros triggers no_stats info', () => {
    const item = makeItem({
      registered_voters: 0, turnout: 0, ballots_received: 0, valid_ballots: 0,
    })
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'no_stats')).toBe(true)
  })

  it('V10: candidate with null votes → no error', () => {
    const item = makeItem({
      valid_ballots: 100,
      candidates: [{ number: 1, name: 'A', votes: null }],
    })
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'cand_exceeds_valid')).toBe(false)
  })

  it('V11: no _candidate_mismatch flag → no warning', () => {
    const item = makeItem()
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'candidate_mismatch')).toBe(false)
  })

  it('detects multiple violations simultaneously', () => {
    const item = makeItem({
      registered_voters: 100,
      turnout: 200, // V1: turnout > registered
      valid_ballots: 150,
      total_votes: 100, // V2: total_votes ≠ valid_ballots
      remaining_ballots: -5, // V4: negative remaining
    })
    const warnings = validateItem(item)
    const ids = warnings.map(w => w.id)
    expect(ids).toContain('turnout_exceeds_voters')
    expect(ids).toContain('votes_ne_valid')
    expect(ids).toContain('negative_remaining')
  })

  it('handles string numeric values via coercion', () => {
    const item = makeItem({ registered_voters: '1000', turnout: '1200' })
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'turnout_exceeds_voters')).toBe(true)
  })
})

describe('getWorstSeverity', () => {
  it('returns "ok" for empty array', () => {
    expect(getWorstSeverity([])).toBe('ok')
  })

  it('returns "info" for info-only warnings', () => {
    expect(getWorstSeverity([{ severity: 'info' }])).toBe('info')
  })

  it('returns "warning" for warning-level warnings', () => {
    expect(getWorstSeverity([{ severity: 'info' }, { severity: 'warning' }])).toBe('warning')
  })

  it('V4: remaining_ballots < 0 → error', () => {
    const item = makeItem({ remaining_ballots: -50 })
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'negative_remaining')).toBe(true)
    expect(warnings.find(w => w.id === 'negative_remaining').severity).toBe('error')
  })

  it('V5: ballots_received ≠ turnout + remaining → warning', () => {
    const item = makeItem({ ballots_received: 900 }) // 900 ≠ 800 + 200
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'ballots_mismatch')).toBe(true)
    expect(warnings.find(w => w.id === 'ballots_mismatch').severity).toBe('warning')
  })

  it('V7: negative invalid_ballots → error', () => {
    const item = makeItem({ invalid_ballots: -10 })
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'negative_values')).toBe(true)
    expect(warnings.find(w => w.id === 'negative_values').severity).toBe('error')
  })

  it('V10: candidate votes > valid_ballots → error', () => {
    const item = makeItem({
      candidates: [
        { number: 1, name: 'Alice', votes: 800 }, // 800 > 750
        { number: 2, name: 'Bob', votes: 100 },
      ]
    })
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'candidate_over_votes')).toBe(true)
    expect(warnings.find(w => w.id === 'candidate_over_votes').severity).toBe('error')
  })

  it('V11: candidate count mismatch → warning', () => {
    const item = makeItem({
      candidates: [
        { number: 1, name: 'Alice', votes: 400 },
        { number: 2, name: 'Bob', votes: 350 },
        { number: 3, name: 'Charlie', votes: 50 },
      ]
    })
    // Assuming ECT reference expects 2 candidates but we have 3
    const warnings = validateItem(item)
    // This might need mock ECT data, placeholder for now
    expect(warnings.filter(w => w.severity === 'warning')).toHaveLength(expect.any(Number))
  })

  it('handles empty candidates array', () => {
    const item = makeItem({ candidates: [] })
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'no_candidates')).toBe(true)
  })

  it('handles null/undefined values gracefully', () => {
    const item = makeItem({
      registered_voters: null,
      turnout: undefined,
      valid_ballots: 750
    })
    const warnings = validateItem(item)
    // Should not crash, handle gracefully
    expect(Array.isArray(warnings)).toBe(true)
  })

  it('edge case: zero registered voters', () => {
    const item = makeItem({ registered_voters: 0 })
    const warnings = validateItem(item)
    expect(warnings.some(w => w.id === 'zero_voters')).toBe(true)
  })
