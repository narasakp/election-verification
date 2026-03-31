import { describe, it, expect } from 'vitest'
import { computeItemAnomalyScore, getSeverityLabel, getSeverityColor, getScoreColor } from './anomalyScore'

describe('computeItemAnomalyScore', () => {
  it('returns score 0 for null/undefined item', () => {
    expect(computeItemAnomalyScore(null).score).toBe(0)
    expect(computeItemAnomalyScore(undefined).score).toBe(0)
  })

  it('returns score 0 for a clean item with no issues', () => {
    const item = {
      registered_voters: 1000,
      turnout: 700,
      ballots_received: 1000,
      valid_ballots: 680,
      invalid_ballots: 15,
      no_vote_ballots: 5,
      remaining_ballots: 300,
      total_votes: 680,
      candidates: [
        { number: 1, name: 'A', votes: 400 },
        { number: 2, name: 'B', votes: 280 },
      ],
    }
    const result = computeItemAnomalyScore(item)
    expect(result.score).toBe(0)
    expect(result.reasons).toHaveLength(0)
  })

  // C1: Turnout > registered voters
  it('detects turnout exceeding registered voters (critical)', () => {
    const item = { registered_voters: 500, turnout: 600 }
    const result = computeItemAnomalyScore(item)
    expect(result.score).toBeGreaterThanOrEqual(30)
    expect(result.reasons.some(r => r.severity === 'critical' && r.label.includes('เกินจำนวน'))).toBe(true)
  })

  // C2: Candidate votes > valid ballots
  it('detects candidate votes exceeding valid ballots (critical)', () => {
    const item = {
      valid_ballots: 100,
      total_votes: 100,
      candidates: [{ number: 1, name: 'X', votes: 150 }],
    }
    const result = computeItemAnomalyScore(item)
    expect(result.reasons.some(r => r.severity === 'critical' && r.label.includes('เกินบัตรดี'))).toBe(true)
  })

  // C3: Single candidate dominance >95%
  it('detects single candidate dominance >95% (critical)', () => {
    const item = {
      total_votes: 1000,
      candidates: [
        { number: 1, name: 'Winner', votes: 960 },
        { number: 2, name: 'Loser', votes: 40 },
      ],
    }
    const result = computeItemAnomalyScore(item)
    expect(result.reasons.some(r => r.severity === 'critical' && r.label.includes('เกือบทั้งหมด'))).toBe(true)
  })

  it('does NOT flag candidate dominance at 90%', () => {
    const item = {
      total_votes: 1000,
      candidates: [
        { number: 1, name: 'A', votes: 900 },
        { number: 2, name: 'B', votes: 100 },
      ],
    }
    const result = computeItemAnomalyScore(item)
    expect(result.reasons.some(r => r.label.includes('เกือบทั้งหมด'))).toBe(false)
  })

  // H1: High turnout >95%
  it('detects unusually high turnout >95% (high)', () => {
    const item = { registered_voters: 1000, turnout: 970 }
    const result = computeItemAnomalyScore(item)
    expect(result.reasons.some(r => r.severity === 'high' && r.label.includes('Turnout สูง'))).toBe(true)
  })

  // H2: Negative remaining
  it('detects negative remaining ballots (high)', () => {
    const item = { remaining_ballots: -5 }
    const result = computeItemAnomalyScore(item)
    expect(result.reasons.some(r => r.severity === 'high' && r.label.includes('ติดลบ'))).toBe(true)
  })

  // H3: ECT flags (array)
  it('detects ECT anomaly flags from array', () => {
    const item = { province: 'test', constituency: '1' }
    const flags = ['turnout_mismatch', 'vote_count_error']
    const result = computeItemAnomalyScore(item, flags)
    expect(result.reasons.some(r => r.severity === 'high' && r.label.includes('ECT'))).toBe(true)
  })

  // H3: ECT flags (object)
  it('detects ECT anomaly flags from object', () => {
    const item = {}
    const flags = { high_turnout: true, vote_mismatch: true, clean: false }
    const result = computeItemAnomalyScore(item, flags)
    expect(result.reasons.some(r => r.label.includes('ECT'))).toBe(true)
  })

  // H4: High invalid ballots
  it('detects high invalid ballot rate >10%', () => {
    const item = { turnout: 1000, invalid_ballots: 150 }
    const result = computeItemAnomalyScore(item)
    expect(result.reasons.some(r => r.severity === 'high' && r.label.includes('บัตรเสีย'))).toBe(true)
  })

  // M1: Votes ≠ valid ballots
  it('detects votes not equal to valid ballots (medium)', () => {
    const item = { total_votes: 500, valid_ballots: 480 }
    const result = computeItemAnomalyScore(item)
    expect(result.reasons.some(r => r.severity === 'medium' && r.label.includes('รวมคะแนน'))).toBe(true)
  })

  // M3: Candidate mismatch
  it('detects candidate mismatch flag', () => {
    const item = { _candidate_mismatch: true, _candidate_mismatch_detail: 'OCR 11 vs ECT 10' }
    const result = computeItemAnomalyScore(item)
    expect(result.reasons.some(r => r.label.includes('ผู้สมัครไม่ตรง'))).toBe(true)
  })

  // L1: Low OCR confidence
  it('detects low OCR confidence fields', () => {
    const item = {
      confidence: {
        registered_voters: 'low_digit_only',
        turnout: 'low_disagree',
        valid_ballots: 'high',
      },
    }
    const result = computeItemAnomalyScore(item)
    expect(result.reasons.some(r => r.severity === 'low' && r.label.includes('OCR'))).toBe(true)
    // Should be 2 low fields × 3 = 6 points
    const ocrReason = result.reasons.find(r => r.label.includes('OCR'))
    expect(ocrReason.points).toBe(6)
  })

  // L2: No data at all
  it('detects no data item', () => {
    const item = { file: 'test.pdf', page: 1 }
    const result = computeItemAnomalyScore(item)
    expect(result.reasons.some(r => r.label.includes('ไม่พบข้อมูลสถิติ'))).toBe(true)
  })

  // Score cap at 100
  it('caps score at 100', () => {
    const item = {
      registered_voters: 500,
      turnout: 600, // C1: +30
      valid_ballots: 100,
      invalid_ballots: 200, // H4: +15
      remaining_ballots: -5, // H2: +15
      total_votes: 200,
      candidates: [
        { number: 1, name: 'A', votes: 999 }, // C2: +30
        { number: 2, name: 'B', votes: 1 },
      ],
      _candidate_mismatch: true, // M3: +10
    }
    const result = computeItemAnomalyScore(item)
    expect(result.score).toBeLessThanOrEqual(100)
  })

  // Sort order: critical > high > medium > low
  it('sorts reasons by severity (critical first)', () => {
    const item = {
      registered_voters: 500,
      turnout: 600, // critical
      remaining_ballots: -5, // high
      total_votes: 200,
      valid_ballots: 180, // medium (votes ≠ valid)
      confidence: { turnout: 'low_digit_only' }, // low
    }
    const result = computeItemAnomalyScore(item)
    expect(result.reasons.length).toBeGreaterThanOrEqual(3)
    // First reason should be critical
    expect(result.reasons[0].severity).toBe('critical')
    // Last reason should be low or medium
    const lastSev = result.reasons[result.reasons.length - 1].severity
    expect(['low', 'medium']).toContain(lastSev)
  })

  // Multiple issues combined
  it('combines multiple issues into one score', () => {
    const item = {
      registered_voters: 1000,
      turnout: 970, // H1: high turnout
      valid_ballots: 960,
      invalid_ballots: 5,
      no_vote_ballots: 5,
      total_votes: 950, // M1: votes ≠ valid
      remaining_ballots: 30,
      ballots_received: 1000,
      candidates: [
        { number: 1, name: 'A', votes: 920 },
        { number: 2, name: 'B', votes: 30 },
      ],
    }
    const result = computeItemAnomalyScore(item)
    expect(result.reasons.length).toBeGreaterThanOrEqual(2)
    expect(result.score).toBeGreaterThan(20)
  })
})

describe('getSeverityLabel', () => {
  it('returns Thai labels', () => {
    expect(getSeverityLabel('critical')).toBe('วิกฤต')
    expect(getSeverityLabel('high')).toBe('สูง')
    expect(getSeverityLabel('medium')).toBe('ปานกลาง')
    expect(getSeverityLabel('low')).toBe('ต่ำ')
    expect(getSeverityLabel('unknown')).toBe('unknown')
  })
})

describe('getSeverityColor', () => {
  it('returns color objects for each severity', () => {
    for (const sev of ['critical', 'high', 'medium', 'low']) {
      const c = getSeverityColor(sev)
      expect(c).toHaveProperty('bg')
      expect(c).toHaveProperty('text')
      expect(c).toHaveProperty('badge')
      expect(c).toHaveProperty('border')
    }
  })
})

describe('getScoreColor', () => {
  it('returns red for score >= 50', () => {
    expect(getScoreColor(50)).toContain('red')
    expect(getScoreColor(100)).toContain('red')
  })
  it('returns orange for score 30-49', () => {
    expect(getScoreColor(30)).toContain('orange')
  })
  it('returns yellow for score 15-29', () => {
    expect(getScoreColor(15)).toContain('yellow')
  })
  it('returns blue for score 1-14', () => {
    expect(getScoreColor(5)).toContain('blue')
  })
  it('returns green for score 0', () => {
    expect(getScoreColor(0)).toContain('green')
  })
})
