import { describe, it, expect, beforeEach, vi } from 'vitest'
import { validateEditValue, getItemSummary, getUserReviewKey, verifyLogIntegrity, computeAnomalyScore, getAllAnomalyScores, getAllSummaries } from './reviewLog'

describe('validateEditValue', () => {
  it('accepts empty/null/undefined values', () => {
    expect(validateEditValue('turnout', '')).toEqual({ valid: true })
    expect(validateEditValue('turnout', null)).toEqual({ valid: true })
    expect(validateEditValue('turnout', undefined)).toEqual({ valid: true })
  })

  it('accepts valid numeric values for numeric fields', () => {
    expect(validateEditValue('turnout', '500').valid).toBe(true)
    expect(validateEditValue('registered_voters', '0').valid).toBe(true)
    expect(validateEditValue('valid_ballots', '99999').valid).toBe(true)
  })

  it('rejects non-numeric values for numeric fields', () => {
    const result = validateEditValue('turnout', 'abc')
    expect(result.valid).toBe(false)
    expect(result.reason).toContain('ตัวเลข')
  })

  it('rejects negative values for numeric fields', () => {
    const result = validateEditValue('turnout', '-5')
    expect(result.valid).toBe(false)
    expect(result.reason).toContain('ลบ')
  })

  it('rejects values exceeding max (99999)', () => {
    const result = validateEditValue('turnout', '100000')
    expect(result.valid).toBe(false)
    expect(result.reason).toContain('สูงสุด')
  })

  it('rejects non-integer values for numeric fields', () => {
    const result = validateEditValue('turnout', '3.5')
    expect(result.valid).toBe(false)
    expect(result.reason).toContain('จำนวนเต็ม')
  })

  it('validates candidate fields (cand_ prefix)', () => {
    expect(validateEditValue('cand_1_votes', '200').valid).toBe(true)
    expect(validateEditValue('cand_1_votes', 'abc').valid).toBe(false)
  })

  it('accepts any value for non-numeric fields', () => {
    expect(validateEditValue('sub_district', 'บางรัก').valid).toBe(true)
    expect(validateEditValue('district', '').valid).toBe(true)
  })
})

describe('getItemSummary', () => {
  it('returns null for empty log', () => {
    expect(getItemSummary([], 'item1')).toBeNull()
  })

  it('returns null when all reviews are reset (pending)', () => {
    const log = [
      { itemId: 'item1', email: 'a@test.com', status: 'confirmed', timestamp: '2025-01-01T00:00:00Z' },
      { itemId: 'item1', email: 'a@test.com', status: 'pending', timestamp: '2025-01-01T00:01:00Z' },
    ]
    expect(getItemSummary(log, 'item1')).toBeNull()
  })

  it('counts unique reviewers correctly', () => {
    const log = [
      { itemId: 'item1', email: 'a@test.com', name: 'A', status: 'confirmed', timestamp: '2025-01-01T00:00:00Z' },
      { itemId: 'item1', email: 'b@test.com', name: 'B', status: 'confirmed', timestamp: '2025-01-01T00:01:00Z' },
      { itemId: 'item1', email: 'a@test.com', name: 'A', status: 'confirmed', timestamp: '2025-01-01T00:02:00Z' },
    ]
    const s = getItemSummary(log, 'item1')
    expect(s.reviewerCount).toBe(2)
    expect(s.totalReviews).toBe(3)
  })

  it('determines majority status correctly', () => {
    const log = [
      { itemId: 'x', email: 'a@t.com', status: 'confirmed', timestamp: '2025-01-01T00:00:00Z' },
      { itemId: 'x', email: 'b@t.com', status: 'confirmed', timestamp: '2025-01-01T00:01:00Z' },
      { itemId: 'x', email: 'c@t.com', status: 'flagged', timestamp: '2025-01-01T00:02:00Z' },
    ]
    const s = getItemSummary(log, 'x')
    expect(s.majorityStatus).toBe('confirmed')
    expect(s.isTie).toBe(false)
    expect(s.outliers).toHaveLength(1)
    expect(s.outliers[0].email).toBe('c@t.com')
  })

  it('detects ties correctly', () => {
    const log = [
      { itemId: 'x', email: 'a@t.com', status: 'confirmed', timestamp: '2025-01-01T00:00:00Z' },
      { itemId: 'x', email: 'b@t.com', status: 'flagged', timestamp: '2025-01-01T00:01:00Z' },
    ]
    const s = getItemSummary(log, 'x')
    expect(s.isTie).toBe(true)
    expect(s.majorityStatus).toBeNull()
    expect(s.tiedStatuses).toContain('confirmed')
    expect(s.tiedStatuses).toContain('flagged')
  })

  it('uses latest review per user (reset withdraws vote)', () => {
    const log = [
      { itemId: 'x', email: 'a@t.com', status: 'confirmed', timestamp: '2025-01-01T00:00:00Z' },
      { itemId: 'x', email: 'b@t.com', status: 'confirmed', timestamp: '2025-01-01T00:01:00Z' },
      { itemId: 'x', email: 'a@t.com', status: 'flagged', timestamp: '2025-01-01T00:02:00Z' },
    ]
    const s = getItemSummary(log, 'x')
    // a changed to flagged, b still confirmed → tie
    expect(s.isTie).toBe(true)
  })

  it('builds consensus edits from majority', () => {
    const log = [
      { itemId: 'x', email: 'a@t.com', status: 'confirmed', timestamp: '2025-01-01T00:00:00Z', edits: { turnout: '500' } },
      { itemId: 'x', email: 'b@t.com', status: 'confirmed', timestamp: '2025-01-01T00:01:00Z', edits: { turnout: '500' } },
      { itemId: 'x', email: 'c@t.com', status: 'confirmed', timestamp: '2025-01-01T00:02:00Z', edits: { turnout: '600' } },
    ]
    const s = getItemSummary(log, 'x')
    expect(s.consensusEdits.turnout).toBe('500')
    expect(s.editConflicts.turnout).toBeDefined()
  })
})

describe('getUserReviewKey', () => {
  it('returns key with email', () => {
    expect(getUserReviewKey('test@example.com')).toBe('ocr_review_test@example.com')
  })

  it('returns anon key for falsy email', () => {
    expect(getUserReviewKey('')).toBe('ocr_review_anon')
    expect(getUserReviewKey(null)).toBe('ocr_review_anon')
    expect(getUserReviewKey(undefined)).toBe('ocr_review_anon')
  })
})

describe('computeAnomalyScore', () => {
  it('returns score 0 for fewer than 3 reviews', () => {
    const log = [
      { itemId: '1', email: 'a@t.com', status: 'confirmed', timestamp: '2025-01-01T00:00:00Z' },
      { itemId: '2', email: 'a@t.com', status: 'confirmed', timestamp: '2025-01-01T00:01:00Z' },
    ]
    const result = computeAnomalyScore(log, 'a@t.com')
    expect(result.score).toBe(0)
    expect(result.level).toBe('ok')
    expect(result.reviewCount).toBe(2)
  })

  it('returns ok level for normal review patterns', () => {
    const log = []
    for (let i = 0; i < 10; i++) {
      const ts = new Date(2025, 0, 1, 0, i * 2, 0).toISOString() // 2 min apart
      log.push({ itemId: `item${i}`, email: 'user@t.com', status: i % 3 === 0 ? 'flagged' : 'confirmed', timestamp: ts })
    }
    const result = computeAnomalyScore(log, 'user@t.com')
    expect(result.level).toBe('ok')
  })

  it('detects high reject ratio', () => {
    const log = []
    for (let i = 0; i < 10; i++) {
      const ts = new Date(2025, 0, 1, 0, i * 2, 0).toISOString()
      log.push({ itemId: `item${i}`, email: 'bad@t.com', status: i < 8 ? 'rejected' : 'confirmed', timestamp: ts })
    }
    const result = computeAnomalyScore(log, 'bad@t.com')
    expect(result.factors.some(f => f.type === 'high_reject_ratio')).toBe(true)
  })

  it('detects rapid reviews', () => {
    const log = []
    for (let i = 0; i < 10; i++) {
      // 1 second apart — all rapid
      const ts = new Date(2025, 0, 1, 0, 0, i).toISOString()
      log.push({ itemId: `item${i}`, email: 'fast@t.com', status: i % 2 === 0 ? 'confirmed' : 'flagged', timestamp: ts })
    }
    const result = computeAnomalyScore(log, 'fast@t.com')
    expect(result.factors.some(f => f.type === 'rapid_reviews')).toBe(true)
  })

  it('detects uniform status (bot-like)', () => {
    const log = []
    for (let i = 0; i < 12; i++) {
      const ts = new Date(2025, 0, 1, 0, i * 5, 0).toISOString()
      log.push({ itemId: `item${i}`, email: 'bot@t.com', status: 'confirmed', timestamp: ts })
    }
    const result = computeAnomalyScore(log, 'bot@t.com')
    expect(result.factors.some(f => f.type === 'uniform_status')).toBe(true)
  })

  it('detects large edit values', () => {
    const log = []
    for (let i = 0; i < 5; i++) {
      const ts = new Date(2025, 0, 1, 0, i * 5, 0).toISOString()
      log.push({
        itemId: `item${i}`, email: 'edit@t.com',
        status: i % 2 === 0 ? 'confirmed' : 'flagged',
        timestamp: ts,
        edits: { turnout: '99999' }
      })
    }
    const result = computeAnomalyScore(log, 'edit@t.com')
    expect(result.factors.some(f => f.type === 'large_edits')).toBe(true)
  })

  it('ignores pending reviews in user review count', () => {
    const log = [
      { itemId: '1', email: 'a@t.com', status: 'pending', timestamp: '2025-01-01T00:00:00Z' },
      { itemId: '2', email: 'a@t.com', status: 'pending', timestamp: '2025-01-01T00:01:00Z' },
    ]
    const result = computeAnomalyScore(log, 'a@t.com')
    expect(result.reviewCount).toBe(0)
    expect(result.score).toBe(0)
  })

  it('caps score at 100', () => {
    // Create a highly suspicious pattern
    const log = []
    for (let i = 0; i < 20; i++) {
      const ts = new Date(2025, 0, 1, 0, 0, i).toISOString() // 1s apart — rapid
      log.push({
        itemId: `item${i}`, email: 'sus@t.com', status: 'rejected',
        timestamp: ts, edits: { turnout: '99999' }
      })
    }
    const result = computeAnomalyScore(log, 'sus@t.com')
    expect(result.score).toBeLessThanOrEqual(100)
  })
})

describe('getAllAnomalyScores', () => {
  it('returns scores for all unique emails', () => {
    const log = [
      { itemId: '1', email: 'a@t.com', status: 'confirmed', timestamp: '2025-01-01T00:00:00Z' },
      { itemId: '2', email: 'b@t.com', status: 'confirmed', timestamp: '2025-01-01T00:01:00Z' },
      { itemId: '3', email: 'a@t.com', status: 'flagged', timestamp: '2025-01-01T00:02:00Z' },
    ]
    const scores = getAllAnomalyScores(log)
    expect(Object.keys(scores)).toContain('a@t.com')
    expect(Object.keys(scores)).toContain('b@t.com')
  })

  it('skips entries with falsy emails', () => {
    const log = [
      { itemId: '1', email: '', status: 'confirmed', timestamp: '2025-01-01T00:00:00Z' },
      { itemId: '2', email: null, status: 'confirmed', timestamp: '2025-01-01T00:01:00Z' },
    ]
    const scores = getAllAnomalyScores(log)
    expect(Object.keys(scores)).toHaveLength(0)
  })
})

describe('getAllSummaries', () => {
  it('returns summaries keyed by itemId', () => {
    const log = [
      { itemId: 'x', email: 'a@t.com', status: 'confirmed', timestamp: '2025-01-01T00:00:00Z' },
      { itemId: 'y', email: 'b@t.com', status: 'flagged', timestamp: '2025-01-01T00:01:00Z' },
    ]
    const summaries = getAllSummaries(log)
    expect(summaries).toHaveProperty('x')
    expect(summaries).toHaveProperty('y')
    expect(summaries.x.majorityStatus).toBe('confirmed')
    expect(summaries.y.majorityStatus).toBe('flagged')
  })

  it('excludes items where all reviews are reset', () => {
    const log = [
      { itemId: 'z', email: 'a@t.com', status: 'confirmed', timestamp: '2025-01-01T00:00:00Z' },
      { itemId: 'z', email: 'a@t.com', status: 'pending', timestamp: '2025-01-01T00:01:00Z' },
    ]
    const summaries = getAllSummaries(log)
    expect(summaries).not.toHaveProperty('z')
  })
})

describe('verifyLogIntegrity', () => {
  it('returns empty array for entries without checksums', () => {
    const log = [{ itemId: 'x', email: 'a', status: 'confirmed', timestamp: '2025-01-01' }]
    expect(verifyLogIntegrity(log)).toHaveLength(0)
  })

  it('detects tampered entries', () => {
    const log = [{
      itemId: 'x',
      email: 'a@t.com',
      status: 'confirmed',
      timestamp: '2025-01-01T00:00:00Z',
      checksum: 'wrong_checksum',
    }]
    const corrupted = verifyLogIntegrity(log)
    expect(corrupted).toHaveLength(1)
    expect(corrupted[0]).toBe(0)
  })

  it('returns empty array for empty log', () => {
    expect(verifyLogIntegrity([])).toHaveLength(0)
  })

  it('returns multiple corrupted indices', () => {
    const log = [
      { itemId: 'a', email: 'x@t.com', status: 'confirmed', timestamp: '2025-01-01T00:00:00Z', checksum: 'bad1' },
      { itemId: 'b', email: 'y@t.com', status: 'flagged', timestamp: '2025-01-01T00:01:00Z', checksum: 'bad2' },
    ]
    const corrupted = verifyLogIntegrity(log)
    expect(corrupted).toHaveLength(2)
    expect(corrupted).toContain(0)
    expect(corrupted).toContain(1)
  })
})

describe('validateEditValue — extended', () => {
  it('accepts boundary value 0 for numeric fields', () => {
    expect(validateEditValue('turnout', '0').valid).toBe(true)
  })

  it('accepts boundary value 99999 for numeric fields', () => {
    expect(validateEditValue('valid_ballots', '99999').valid).toBe(true)
  })

  it('treats constituency as numeric field', () => {
    expect(validateEditValue('constituency', '3').valid).toBe(true)
    expect(validateEditValue('constituency', 'abc').valid).toBe(false)
  })

  it('rejects NaN string for numeric fields', () => {
    expect(validateEditValue('turnout', 'NaN').valid).toBe(false)
  })

  it('rejects Infinity for numeric fields', () => {
    expect(validateEditValue('turnout', 'Infinity').valid).toBe(false)
  })

  it('accepts string values for non-numeric fields', () => {
    expect(validateEditValue('province', 'ชัยภูมิ').valid).toBe(true)
    expect(validateEditValue('vote_type', 'constituency').valid).toBe(true)
  })
})

describe('getItemSummary — extended', () => {
  it('returns correct summary for single reviewer', () => {
    const log = [
      { itemId: 'item1', email: 'a@t.com', name: 'A', status: 'confirmed', timestamp: '2025-01-01T00:00:00Z' },
    ]
    const s = getItemSummary(log, 'item1')
    expect(s.reviewerCount).toBe(1)
    expect(s.totalReviews).toBe(1)
    expect(s.majorityStatus).toBe('confirmed')
    expect(s.hasConflict).toBe(false)
  })

  it('computes consensusRatio correctly', () => {
    const log = [
      { itemId: 'x', email: 'a@t.com', status: 'confirmed', timestamp: '2025-01-01T00:00:00Z' },
      { itemId: 'x', email: 'b@t.com', status: 'confirmed', timestamp: '2025-01-01T00:01:00Z' },
      { itemId: 'x', email: 'c@t.com', status: 'flagged', timestamp: '2025-01-01T00:02:00Z' },
    ]
    const s = getItemSummary(log, 'x')
    expect(s.consensusRatio).toBeCloseTo(2 / 3)
  })

  it('detects hasConflict when statuses differ', () => {
    const log = [
      { itemId: 'x', email: 'a@t.com', status: 'confirmed', timestamp: '2025-01-01T00:00:00Z' },
      { itemId: 'x', email: 'b@t.com', status: 'rejected', timestamp: '2025-01-01T00:01:00Z' },
    ]
    const s = getItemSummary(log, 'x')
    expect(s.hasConflict).toBe(true)
  })

  it('handles edit conflicts with tied values', () => {
    const log = [
      { itemId: 'x', email: 'a@t.com', status: 'confirmed', timestamp: '2025-01-01T00:00:00Z', edits: { turnout: '500' } },
      { itemId: 'x', email: 'b@t.com', status: 'confirmed', timestamp: '2025-01-01T00:01:00Z', edits: { turnout: '600' } },
    ]
    const s = getItemSummary(log, 'x')
    // Tied edit values → no consensus edit, but editConflicts present
    expect(s.editConflicts.turnout).toBeDefined()
    expect(s.editConflicts.turnout).toHaveLength(2)
  })

  it('ignores reviews for other items', () => {
    const log = [
      { itemId: 'x', email: 'a@t.com', status: 'confirmed', timestamp: '2025-01-01T00:00:00Z' },
      { itemId: 'y', email: 'b@t.com', status: 'flagged', timestamp: '2025-01-01T00:01:00Z' },
    ]
    const s = getItemSummary(log, 'x')
    expect(s.reviewerCount).toBe(1)
    expect(s.majorityStatus).toBe('confirmed')
  })
})

describe('computeAnomalyScore — extended', () => {
  it('returns warning level for score >= 30', () => {
    // Create a pattern that scores around 30-59
    const log = []
    for (let i = 0; i < 10; i++) {
      const ts = new Date(2025, 0, 1, 0, i * 2, 0).toISOString()
      log.push({
        itemId: `item${i}`, email: 'mid@t.com',
        status: 'rejected', // all rejected → high reject ratio
        timestamp: ts,
      })
    }
    const result = computeAnomalyScore(log, 'mid@t.com')
    // High reject (>50%) + uniform status → should hit warning or higher
    expect(result.score).toBeGreaterThanOrEqual(30)
  })

  it('returns danger level for combined suspicious patterns', () => {
    const log = []
    for (let i = 0; i < 20; i++) {
      const ts = new Date(2025, 0, 1, 0, 0, i).toISOString() // 1s apart
      log.push({
        itemId: `item${i}`, email: 'danger@t.com',
        status: 'rejected',
        timestamp: ts,
        edits: { turnout: '99999' },
      })
    }
    const result = computeAnomalyScore(log, 'danger@t.com')
    expect(result.level).toBe('danger')
    expect(result.score).toBeGreaterThanOrEqual(60)
  })

  it('detects very fast average review speed', () => {
    const log = []
    for (let i = 0; i < 10; i++) {
      // 2 seconds apart avg
      const ts = new Date(2025, 0, 1, 0, 0, i * 2).toISOString()
      log.push({
        itemId: `item${i}`, email: 'speedy@t.com',
        status: i % 3 === 0 ? 'flagged' : 'confirmed',
        timestamp: ts,
      })
    }
    const result = computeAnomalyScore(log, 'speedy@t.com')
    expect(result.factors.some(f => f.type === 'very_fast_avg')).toBe(true)
  })

  it('does not flag normal speed average', () => {
    const log = []
    for (let i = 0; i < 10; i++) {
      const ts = new Date(2025, 0, 1, 0, i * 2, 0).toISOString() // 2 min apart
      log.push({
        itemId: `item${i}`, email: 'normal@t.com',
        status: i % 3 === 0 ? 'flagged' : 'confirmed',
        timestamp: ts,
      })
    }
    const result = computeAnomalyScore(log, 'normal@t.com')
    expect(result.factors.some(f => f.type === 'very_fast_avg')).toBe(false)
  })

  it('handles user with only other users reviews in log', () => {
    const log = [
      { itemId: '1', email: 'other@t.com', status: 'confirmed', timestamp: '2025-01-01T00:00:00Z' },
    ]
    const result = computeAnomalyScore(log, 'nonexistent@t.com')
    expect(result.score).toBe(0)
    expect(result.reviewCount).toBe(0)
  })
})
