import { describe, it, expect, beforeEach, vi } from 'vitest'
import { validateEditValue, getItemSummary, getUserReviewKey, verifyLogIntegrity } from './reviewLog'

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
})
