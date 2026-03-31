/**
 * Anomaly scoring for election OCR items.
 * Computes a composite score (0–100) + list of reasons,
 * combining data integrity checks, statistical outliers,
 * OCR quality, and cross-reference flags.
 *
 * Higher score = more suspicious / needs urgent review.
 */

const n = (v) => (v == null ? null : Number(v))

/**
 * @param {object} item - Review data item
 * @param {object|null} ectFlags - ECT anomaly flags for this constituency (from anomalyFlags[province_constituency])
 * @returns {{ score: number, reasons: Array<{label: string, detail: string, severity: 'critical'|'high'|'medium'|'low', points: number}> }}
 */
export function computeItemAnomalyScore(item, ectFlags = null) {
  const reasons = []

  if (!item) return { score: 0, reasons }

  const reg = n(item.registered_voters)
  const turn = n(item.turnout)
  const vb = n(item.valid_ballots)
  const ib = n(item.invalid_ballots)
  const nv = n(item.no_vote_ballots)
  const br = n(item.ballots_received)
  const rem = n(item.remaining_ballots)
  const tv = n(item.total_votes)
  const cands = item.candidates || []

  // ─── CRITICAL: potential fraud indicators ───

  // C1: Turnout > Registered voters
  if (reg != null && turn != null && turn > reg && reg > 0) {
    const pct = ((turn / reg - 1) * 100).toFixed(1)
    reasons.push({
      label: 'มาใช้สิทธิ์เกินจำนวนผู้มีสิทธิ์',
      detail: `มาแสดงตน ${turn.toLocaleString()} > ผู้มีสิทธิ์ ${reg.toLocaleString()} (เกิน ${pct}%)`,
      severity: 'critical',
      points: 30,
    })
  }

  // C2: Candidate votes > valid ballots
  if (vb != null && vb > 0 && cands.length > 0) {
    const overVotes = cands.filter(c => n(c.votes) > vb)
    if (overVotes.length > 0) {
      reasons.push({
        label: 'ผู้สมัครได้คะแนนเกินบัตรดี',
        detail: overVotes.map(c => `${c.name || '#' + c.number}: ${n(c.votes).toLocaleString()} > ${vb.toLocaleString()}`).join(', '),
        severity: 'critical',
        points: 30,
      })
    }
  }

  // C3: Single candidate dominance (>95% of votes)
  if (cands.length >= 2 && tv != null && tv > 0) {
    const maxVotes = Math.max(...cands.map(c => n(c.votes) || 0))
    const pct = maxVotes / tv
    if (pct > 0.95) {
      const winner = cands.find(c => n(c.votes) === maxVotes)
      reasons.push({
        label: 'ผู้สมัครคนเดียวได้คะแนนเกือบทั้งหมด',
        detail: `${winner?.name || '?'} ได้ ${(pct * 100).toFixed(1)}% (${maxVotes.toLocaleString()}/${tv.toLocaleString()})`,
        severity: 'critical',
        points: 25,
      })
    }
  }

  // ─── HIGH: suspicious patterns ───

  // H1: Unusually high turnout (>95%)
  if (reg != null && turn != null && reg > 0 && turn <= reg) {
    const turnPct = turn / reg
    if (turnPct > 0.95) {
      reasons.push({
        label: 'Turnout สูงผิดปกติ',
        detail: `${(turnPct * 100).toFixed(1)}% (${turn.toLocaleString()}/${reg.toLocaleString()}) — ปกติ 60–80%`,
        severity: 'high',
        points: 20,
      })
    }
  }

  // H2: Negative remaining ballots
  if (rem != null && rem < 0) {
    reasons.push({
      label: 'บัตรเหลือติดลบ',
      detail: `remaining_ballots = ${rem}`,
      severity: 'high',
      points: 15,
    })
  }

  // H3: ECT cross-reference anomaly flags
  if (ectFlags && Array.isArray(ectFlags) && ectFlags.length > 0) {
    reasons.push({
      label: 'ECT cross-reference พบความผิดปกติ',
      detail: ectFlags.map(f => typeof f === 'string' ? f : f.message || f.flag || JSON.stringify(f)).join('; '),
      severity: 'high',
      points: 15,
    })
  } else if (ectFlags && typeof ectFlags === 'object' && !Array.isArray(ectFlags)) {
    // ectFlags might be an object with flag keys
    const flagKeys = Object.keys(ectFlags).filter(k => ectFlags[k])
    if (flagKeys.length > 0) {
      reasons.push({
        label: 'ECT cross-reference พบความผิดปกติ',
        detail: flagKeys.join(', '),
        severity: 'high',
        points: 15,
      })
    }
  }

  // H4: Invalid ballots unusually high (>10% of turnout)
  if (ib != null && turn != null && turn > 0) {
    const ibPct = ib / turn
    if (ibPct > 0.10) {
      reasons.push({
        label: 'บัตรเสียสูงผิดปกติ',
        detail: `${(ibPct * 100).toFixed(1)}% (${ib.toLocaleString()}/${turn.toLocaleString()}) — ปกติ < 3%`,
        severity: 'high',
        points: 15,
      })
    }
  }

  // ─── MEDIUM: data inconsistencies ───

  // M1: Votes ≠ valid ballots
  if (tv != null && vb != null && tv !== vb && vb > 0) {
    reasons.push({
      label: 'รวมคะแนน ≠ บัตรดี',
      detail: `${tv.toLocaleString()} ≠ ${vb.toLocaleString()}`,
      severity: 'medium',
      points: 10,
    })
  }

  // M2: Ballot sum ≠ turnout
  if (vb != null && ib != null && nv != null && turn != null && turn > 0) {
    const sum = vb + ib + nv
    if (sum !== turn) {
      reasons.push({
        label: 'บัตรดี+เสีย+ไม่เลือก ≠ มาแสดงตน',
        detail: `${sum.toLocaleString()} ≠ ${turn.toLocaleString()}`,
        severity: 'medium',
        points: 10,
      })
    }
  }

  // M3: Candidate count mismatch with ECT
  if (item._candidate_mismatch) {
    reasons.push({
      label: 'จำนวนผู้สมัครไม่ตรง ECT',
      detail: item._candidate_mismatch_detail || `OCR: ${cands.length} คน`,
      severity: 'medium',
      points: 10,
    })
  }

  // M4: Candidate votes sum ≠ total_votes
  if (cands.length > 0 && tv != null && tv > 0) {
    const candSum = cands.reduce((s, c) => s + (n(c.votes) || 0), 0)
    if (candSum !== tv) {
      reasons.push({
        label: 'ผลรวมคะแนนผู้สมัคร ≠ รวมคะแนน',
        detail: `ผู้สมัครรวม ${candSum.toLocaleString()} ≠ total ${tv.toLocaleString()}`,
        severity: 'medium',
        points: 8,
      })
    }
  }

  // M5: Registered voters unreasonably high
  if (reg != null && reg > 10000) {
    reasons.push({
      label: 'ผู้มีสิทธิ์สูงผิดปกติ',
      detail: `${reg.toLocaleString()} คน — ปกติ < 1,500 ต่อหน่วย`,
      severity: 'medium',
      points: 5,
    })
  }

  // M6: Negative values in key fields
  const negFields = ['registered_voters', 'turnout', 'ballots_received', 'valid_ballots', 'invalid_ballots', 'no_vote_ballots', 'total_votes']
    .filter(f => n(item[f]) != null && n(item[f]) < 0)
  if (negFields.length > 0) {
    reasons.push({
      label: 'ค่าติดลบในฟิลด์สำคัญ',
      detail: negFields.join(', '),
      severity: 'medium',
      points: 10,
    })
  }

  // ─── LOW: OCR quality issues ───

  // L1: Low OCR confidence
  if (item.confidence && typeof item.confidence === 'object') {
    const lowFields = Object.entries(item.confidence)
      .filter(([, v]) => v && typeof v === 'string' && v.startsWith('low'))
    if (lowFields.length > 0) {
      reasons.push({
        label: `OCR ความมั่นใจต่ำ (${lowFields.length} ฟิลด์)`,
        detail: lowFields.map(([k]) => k).join(', '),
        severity: 'low',
        points: 3 * lowFields.length,
      })
    }
  }

  // L2: No data at all
  const dataFields = ['registered_voters', 'turnout', 'ballots_received', 'valid_ballots']
  if (dataFields.every(f => item[f] == null || item[f] === 0)) {
    reasons.push({
      label: 'ไม่พบข้อมูลสถิติ',
      detail: 'ไม่มีค่าใดเลย — อาจเป็นหน้าลายเซ็น',
      severity: 'low',
      points: 3,
    })
  }

  // L3: Ballots received ≠ turnout + remaining
  if (br != null && turn != null && rem != null && rem >= 0 && br > 0) {
    if (br !== turn + rem) {
      reasons.push({
        label: 'บัตรที่ได้รับ ≠ ใช้สิทธิ์+เหลือ',
        detail: `${br.toLocaleString()} ≠ ${turn.toLocaleString()} + ${rem.toLocaleString()}`,
        severity: 'low',
        points: 5,
      })
    }
  }

  // Compute total score (capped at 100)
  const score = Math.min(100, reasons.reduce((s, r) => s + r.points, 0))

  // Sort reasons by severity (critical > high > medium > low)
  const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 }
  reasons.sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity])

  return { score, reasons }
}

/**
 * Get severity label in Thai
 */
export function getSeverityLabel(severity) {
  switch (severity) {
    case 'critical': return 'วิกฤต'
    case 'high': return 'สูง'
    case 'medium': return 'ปานกลาง'
    case 'low': return 'ต่ำ'
    default: return severity
  }
}

/**
 * Get severity color classes
 */
export function getSeverityColor(severity) {
  switch (severity) {
    case 'critical': return { bg: 'bg-red-100', text: 'text-red-800', badge: 'bg-red-500', border: 'border-red-300' }
    case 'high': return { bg: 'bg-orange-100', text: 'text-orange-800', badge: 'bg-orange-500', border: 'border-orange-300' }
    case 'medium': return { bg: 'bg-yellow-100', text: 'text-yellow-800', badge: 'bg-yellow-500', border: 'border-yellow-300' }
    case 'low': return { bg: 'bg-blue-100', text: 'text-blue-800', badge: 'bg-blue-500', border: 'border-blue-300' }
    default: return { bg: 'bg-gray-100', text: 'text-gray-800', badge: 'bg-gray-500', border: 'border-gray-300' }
  }
}

/**
 * Get score color for the overall anomaly score badge
 */
export function getScoreColor(score) {
  if (score >= 50) return 'bg-red-600 text-white'
  if (score >= 30) return 'bg-orange-500 text-white'
  if (score >= 15) return 'bg-yellow-500 text-white'
  if (score > 0) return 'bg-blue-500 text-white'
  return 'bg-green-500 text-white'
}
