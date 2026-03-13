/**
 * Data validation rules for election OCR records.
 * Each rule returns { id, severity, message } or null.
 * severity: 'error' | 'warning' | 'info'
 */

const n = (v) => (v == null ? null : Number(v))

const rules = [
  // V1: มาแสดงตน > ผู้มีสิทธิ
  (d) => {
    const reg = n(d.registered_voters), turn = n(d.turnout)
    if (reg != null && turn != null && turn > reg && reg > 0)
      return { id: 'turnout_exceeds_voters', severity: 'error', message: `มาแสดงตน (${turn}) > ผู้มีสิทธิ (${reg})` }
    return null
  },

  // V2: คะแนนรวม ≠ บัตรดี
  (d) => {
    const tv = n(d.total_votes), vb = n(d.valid_ballots)
    if (tv != null && vb != null && tv !== vb && vb > 0)
      return { id: 'votes_ne_valid', severity: 'warning', message: `รวมคะแนน (${tv}) ≠ บัตรดี (${vb})` }
    return null
  },

  // V3: บัตรดี + บัตรเสีย + ไม่เลือกใคร ≠ มาแสดงตน
  (d) => {
    const vb = n(d.valid_ballots), ib = n(d.invalid_ballots), nv = n(d.no_vote_ballots), turn = n(d.turnout)
    if (vb != null && ib != null && nv != null && turn != null) {
      const sum = vb + ib + nv
      if (sum !== turn && turn > 0)
        return { id: 'ballot_sum_ne_turnout', severity: 'warning', message: `บัตรดี+เสีย+ไม่เลือก (${sum}) ≠ มาแสดงตน (${turn})` }
    }
    return null
  },

  // V4: บัตรเหลือติดลบ
  (d) => {
    const rem = n(d.remaining_ballots)
    if (rem != null && rem < 0)
      return { id: 'negative_remaining', severity: 'error', message: `บัตรเหลือติดลบ (${rem})` }
    return null
  },

  // V5: บัตรที่ได้รับ ≠ มาแสดงตน + บัตรเหลือ
  (d) => {
    const br = n(d.ballots_received), turn = n(d.turnout), rem = n(d.remaining_ballots)
    if (br != null && turn != null && rem != null && rem >= 0) {
      const expected = turn + rem
      if (br !== expected && br > 0)
        return { id: 'received_ne_used_plus_remain', severity: 'warning', message: `บัตรที่ได้รับ (${br}) ≠ มาแสดงตน+เหลือ (${expected})` }
    }
    return null
  },

  // V6: ผลรวมคะแนนผู้สมัคร ≠ รวมคะแนน
  (d) => {
    const cands = d.candidates || []
    if (cands.length === 0) return null
    const candSum = cands.reduce((s, c) => s + (n(c.votes) || 0), 0)
    const tv = n(d.total_votes)
    if (tv != null && candSum !== tv && tv > 0)
      return { id: 'cand_sum_ne_total', severity: 'warning', message: `ผลรวมผู้สมัคร (${candSum}) ≠ รวมคะแนน (${tv})` }
    return null
  },

  // V7: ค่าติดลบ (ยกเว้น remaining)
  (d) => {
    const fields = ['registered_voters', 'turnout', 'ballots_received', 'valid_ballots', 'invalid_ballots', 'no_vote_ballots', 'total_votes']
    const neg = fields.filter(f => n(d[f]) != null && n(d[f]) < 0)
    if (neg.length > 0)
      return { id: 'negative_values', severity: 'error', message: `ค่าติดลบ: ${neg.join(', ')}` }
    return null
  },

  // V8: ผู้มีสิทธิ > 10,000 (ผิดปกติสำหรับหน่วยเลือกตั้ง)
  (d) => {
    const reg = n(d.registered_voters)
    if (reg != null && reg > 10000)
      return { id: 'voters_too_high', severity: 'warning', message: `ผู้มีสิทธิสูงผิดปกติ (${reg.toLocaleString()}) — ปกติ < 1,500` }
    return null
  },

  // V9: ไม่มีข้อมูลสถิติเลย
  (d) => {
    const fields = ['registered_voters', 'turnout', 'ballots_received', 'valid_ballots']
    const allNull = fields.every(f => d[f] == null || d[f] === 0)
    if (allNull)
      return { id: 'no_stats', severity: 'info', message: 'ไม่พบข้อมูลสถิติการลงคะแนน' }
    return null
  },

  // V10: ผู้สมัครมีคะแนน > บัตรดี
  (d) => {
    const cands = d.candidates || []
    const vb = n(d.valid_ballots)
    if (vb == null || vb === 0 || cands.length === 0) return null
    const bad = cands.filter(c => n(c.votes) > vb)
    if (bad.length > 0)
      return { id: 'cand_exceeds_valid', severity: 'error', message: `ผู้สมัครมีคะแนน > บัตรดี: ${bad.map(c => `${c.name || '#' + c.number} (${c.votes})`).join(', ')}` }
    return null
  },

  // V11: จำนวนผู้สมัครไม่ตรงกับ ECT
  (d) => {
    if (d._candidate_mismatch)
      return { id: 'candidate_mismatch', severity: 'warning', message: `จำนวนผู้สมัครไม่ตรง ECT: ${d._candidate_mismatch_detail || ''}` }
    return null
  },
]

export function validateItem(item) {
  return rules.map(r => r(item)).filter(Boolean)
}

export function getWorstSeverity(warnings) {
  if (warnings.some(w => w.severity === 'error')) return 'error'
  if (warnings.some(w => w.severity === 'warning')) return 'warning'
  if (warnings.some(w => w.severity === 'info')) return 'info'
  return 'ok'
}
