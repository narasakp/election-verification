/**
 * Review Log — tracks all review actions across users.
 *
 * localStorage 'ocr_review_log' = [
 *   { itemId, email, name, status, note, edits, timestamp, checksum }
 * ]
 *
 * Features:
 * - Per-item summary: reviewer count, total reviews
 * - Majority vote (consensus) with edit merging
 * - Outlier detection (reviewers disagreeing with majority)
 * - Rate limiting (min interval between reviews)
 * - Anomaly scoring per user
 * - Integrity checksums
 */

const LOG_KEY = 'ocr_review_log'
const RATE_KEY = 'ocr_review_rate'
const MIN_REVIEW_INTERVAL_MS = 3000  // 3 seconds minimum between reviews
const RAPID_REVIEW_THRESHOLD = 5     // 5 rapid reviews in a row → flag user
const EDIT_MIN = 0
const EDIT_MAX = 99999

// --------------- checksum ---------------

function simpleHash(str) {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    const ch = str.charCodeAt(i)
    hash = ((hash << 5) - hash) + ch
    hash |= 0
  }
  return hash.toString(36)
}

function computeChecksum(entry) {
  const payload = `${entry.itemId}|${entry.email}|${entry.status}|${entry.timestamp}`
  return simpleHash(payload)
}

const MAX_LOG_BYTES = 4 * 1024 * 1024  // 4MB soft limit (localStorage max ~5MB)
const TRIM_KEEP_RATIO = 0.75           // keep 75% of entries when trimming

// --------------- low-level ---------------

export function getReviewLog() {
  try {
    return JSON.parse(localStorage.getItem(LOG_KEY) || '[]')
  } catch {
    return []
  }
}

export function saveReviewLog(log) {
  const json = JSON.stringify(log)
  // If approaching localStorage limit, trim oldest entries
  if (json.length > MAX_LOG_BYTES) {
    const keepCount = Math.floor(log.length * TRIM_KEEP_RATIO)
    const trimmed = log.slice(log.length - keepCount)
    console.warn(`[reviewLog] Trimmed ${log.length - keepCount} oldest entries (${log.length}→${trimmed.length}) to stay within storage limit`)
    localStorage.setItem(LOG_KEY, JSON.stringify(trimmed))
    return
  }
  localStorage.setItem(LOG_KEY, json)
}

/**
 * Append a review entry and return updated log.
 * Now also tracks edits and includes integrity checksum.
 * @param {{ itemId: string, email: string, name: string, status: string, note?: string, edits?: object }} entry
 * @returns {Array} updated log
 */
export function appendReviewLog(entry) {
  const log = getReviewLog()
  const ts = new Date().toISOString()
  const record = {
    ...entry,
    edits: entry.edits || {},
    timestamp: ts,
  }
  record.checksum = computeChecksum(record)
  log.push(record)
  saveReviewLog(log)
  // D1: Return what's actually persisted (saveReviewLog may have trimmed)
  return getReviewLog()
}

// --------------- rate limiting (F2) ---------------

/**
 * Check if the user is reviewing too fast.
 * Returns { allowed: boolean, waitMs: number, rapidCount: number, flagged: boolean }
 */
export function checkRateLimit(email) {
  const now = Date.now()
  let rateData = {}
  try { rateData = JSON.parse(localStorage.getItem(RATE_KEY) || '{}') } catch {}

  const userData = rateData[email] || { lastReviewAt: 0, rapidCount: 0 }
  const elapsed = now - userData.lastReviewAt
  const tooFast = elapsed < MIN_REVIEW_INTERVAL_MS && userData.lastReviewAt > 0

  if (tooFast) {
    userData.rapidCount = (userData.rapidCount || 0) + 1
  } else {
    userData.rapidCount = 0
  }

  const flagged = userData.rapidCount >= RAPID_REVIEW_THRESHOLD

  // Persist rapidCount so flag detection accumulates across blocked attempts
  rateData[email] = userData
  localStorage.setItem(RATE_KEY, JSON.stringify(rateData))

  return {
    allowed: !tooFast,
    waitMs: tooFast ? MIN_REVIEW_INTERVAL_MS - elapsed : 0,
    rapidCount: userData.rapidCount,
    flagged,
  }
}

/**
 * Record that a review was made (update lastReviewAt).
 * C5: rapidCount is already handled by checkRateLimit; this only stamps the time.
 */
export function recordReviewTiming(email) {
  const now = Date.now()
  let rateData = {}
  try { rateData = JSON.parse(localStorage.getItem(RATE_KEY) || '{}') } catch {}

  const userData = rateData[email] || { lastReviewAt: 0, rapidCount: 0 }
  userData.lastReviewAt = now
  // Reset rapidCount on successful (allowed) review
  userData.rapidCount = 0

  rateData[email] = userData
  localStorage.setItem(RATE_KEY, JSON.stringify(rateData))
}

// --------------- edit bounds checking (F3) ---------------

const NUMERIC_FIELDS = new Set([
  'registered_voters', 'turnout', 'ballots_received', 'valid_ballots',
  'invalid_ballots', 'no_vote_ballots', 'remaining_ballots', 'total_votes',
  'constituency',
])

/**
 * Validate an edit value. Returns { valid: boolean, reason?: string }
 */
export function validateEditValue(field, value) {
  if (value === '' || value === null || value === undefined) return { valid: true }

  if (NUMERIC_FIELDS.has(field) || field.startsWith('cand_')) {
    const num = Number(value)
    if (isNaN(num)) return { valid: false, reason: `"${field}" ต้องเป็นตัวเลข` }
    if (num < EDIT_MIN) return { valid: false, reason: `"${field}" ห้ามเป็นค่าลบ` }
    if (num > EDIT_MAX) return { valid: false, reason: `"${field}" เกินค่าสูงสุด (${EDIT_MAX})` }
    if (!Number.isInteger(num)) return { valid: false, reason: `"${field}" ต้องเป็นจำนวนเต็ม` }
  }

  return { valid: true }
}

// --------------- anomaly scoring (F4) ---------------

/**
 * Compute anomaly score for a user based on review log patterns.
 * Score 0-100. Higher = more suspicious.
 *
 * Factors:
 * - High reject ratio (> 50% rejected)
 * - Many rapid reviews
 * - Large edit deviations from OCR values
 * - Reviewing without any edits on items with warnings
 * - All same status (no variety → possibly bot-like)
 */
export function computeAnomalyScore(log, email) {
  const userReviews = log.filter(r => r.email === email && r.status !== 'pending')
  if (userReviews.length < 3) return { score: 0, factors: [], level: 'ok', reviewCount: userReviews.length }

  const factors = []
  let score = 0

  // C3: Use latest review per item for ratio calculations (not all historical)
  const latestPerItem = {}
  userReviews.forEach(r => {
    if (!latestPerItem[r.itemId] || r.timestamp > latestPerItem[r.itemId].timestamp) {
      latestPerItem[r.itemId] = r
    }
  })
  const currentReviews = Object.values(latestPerItem)

  // 1. Reject ratio (based on current state per item, not all historical)
  const rejectCount = currentReviews.filter(r => r.status === 'rejected').length
  const rejectRatio = currentReviews.length > 0 ? rejectCount / currentReviews.length : 0
  if (rejectRatio > 0.5 && currentReviews.length >= 5) {
    const pts = Math.min(30, Math.round(rejectRatio * 40))
    score += pts
    factors.push({ type: 'high_reject_ratio', value: rejectRatio, points: pts, desc: `${Math.round(rejectRatio * 100)}% ถูกกด "ใช้ไม่ได้"` })
  }

  // 2. Rapid review detection (reviews within 3s of each other — uses all reviews for timing)
  const sorted = [...userReviews].sort((a, b) => a.timestamp.localeCompare(b.timestamp))
  let rapidCount = 0
  for (let i = 1; i < sorted.length; i++) {
    const diff = new Date(sorted[i].timestamp) - new Date(sorted[i - 1].timestamp)
    if (diff < MIN_REVIEW_INTERVAL_MS) rapidCount++
  }
  const rapidRatio = sorted.length > 1 ? rapidCount / (sorted.length - 1) : 0
  if (rapidRatio > 0.3) {
    const pts = Math.min(25, Math.round(rapidRatio * 35))
    score += pts
    factors.push({ type: 'rapid_reviews', value: rapidCount, points: pts, desc: `${rapidCount} ครั้งตรวจเร็วเกิน (<3วิ)` })
  }

  // 3. Large edit deviations
  let bigEditCount = 0
  userReviews.forEach(r => {
    if (r.edits && typeof r.edits === 'object') {
      Object.values(r.edits).forEach(v => {
        const num = Number(v)
        if (!isNaN(num) && num > 10000) bigEditCount++
      })
    }
  })
  if (bigEditCount > 2) {
    const pts = Math.min(20, bigEditCount * 5)
    score += pts
    factors.push({ type: 'large_edits', value: bigEditCount, points: pts, desc: `${bigEditCount} ค่าแก้ไขสูงผิดปกติ` })
  }

  // 4. All same status (bot-like) — uses latest per item to avoid false positives from status changes
  const uniqueStatuses = new Set(currentReviews.map(r => r.status))
  if (uniqueStatuses.size === 1 && currentReviews.length >= 10) {
    score += 15
    factors.push({ type: 'uniform_status', value: [...uniqueStatuses][0], points: 15, desc: `ทุกหน้ากดสถานะเดียวกัน (${currentReviews.length} รายการ)` })
  }

  // 5. Review speed (average time between reviews)
  if (sorted.length >= 5) {
    const totalTime = new Date(sorted[sorted.length - 1].timestamp) - new Date(sorted[0].timestamp)
    const avgMs = totalTime / (sorted.length - 1)
    if (avgMs < 5000) { // avg < 5s
      score += 10
      factors.push({ type: 'very_fast_avg', value: Math.round(avgMs / 1000), points: 10, desc: `เฉลี่ย ${Math.round(avgMs / 1000)} วิ/หน้า` })
    }
  }

  score = Math.min(100, score)
  const level = score >= 60 ? 'danger' : score >= 30 ? 'warning' : 'ok'

  return { score, factors, level, reviewCount: userReviews.length }
}

/**
 * Get anomaly scores for all users in the log.
 * Returns { [email]: { score, factors, level, reviewCount } }
 */
export function getAllAnomalyScores(log) {
  const emails = new Set(log.map(r => r.email).filter(Boolean))
  const scores = {}
  emails.forEach(email => {
    scores[email] = computeAnomalyScore(log, email)
  })
  return scores
}

// --------------- aggregation ---------------

/**
 * Build per-item summary from log.
 * Returns { reviewerCount, totalReviews, statusCounts, majorityStatus, outliers, hasConflict,
 *           consensusEdits, editConflicts }
 */
export function getItemSummary(log, itemId) {
  const allItemReviews = log.filter(r => r.itemId === itemId && r.status)
  if (allItemReviews.length === 0) return null

  // C1: Build latest-per-user from ALL reviews (including pending/reset)
  // so a reset properly withdraws the user's vote
  const latestByUserAll = {}
  allItemReviews.forEach(r => {
    if (!latestByUserAll[r.email] || r.timestamp > latestByUserAll[r.email].timestamp) {
      latestByUserAll[r.email] = r
    }
  })

  // Only keep users whose latest vote is NOT pending (active voters)
  const latestByUser = {}
  Object.entries(latestByUserAll).forEach(([email, r]) => {
    if (r.status !== 'pending') {
      latestByUser[email] = r
    }
  })

  // If no active voters remain, return minimal summary
  if (Object.keys(latestByUser).length === 0) return null

  const totalReviews = allItemReviews.filter(r => r.status !== 'pending').length

  // C2: statusCounts from latest-per-user only (reflects current state, not history)
  const statusCounts = {}
  Object.values(latestByUser).forEach(r => {
    statusCounts[r.status] = (statusCounts[r.status] || 0) + 1
  })

  const sorted = Object.entries(statusCounts).sort((a, b) => b[1] - a[1])
  const topCount = sorted[0]?.[1] || 0
  const tiedStatuses = sorted.filter(([_, c]) => c === topCount)
  // True majority: winner must be unique; otherwise mark as disputed
  const totalVoters = Object.keys(latestByUser).length
  const isTie = tiedStatuses.length > 1
  const majorityStatus = isTie ? null : (sorted[0]?.[0] || null)
  const consensusRatio = totalVoters > 0 ? topCount / totalVoters : 0

  // Outliers: users whose latest vote differs from majority (only meaningful if no tie)
  const outliers = majorityStatus
    ? Object.entries(latestByUser)
        .filter(([_, r]) => r.status !== majorityStatus)
        .map(([email, r]) => ({ email, name: r.name, status: r.status }))
    : []

  // Merge edits — majority vote per field
  const editsByField = {} // field → { [value]: count }
  Object.values(latestByUser).forEach(r => {
    if (r.edits && typeof r.edits === 'object') {
      Object.entries(r.edits).forEach(([field, value]) => {
        if (!editsByField[field]) editsByField[field] = {}
        const key = String(value)
        editsByField[field][key] = (editsByField[field][key] || 0) + 1
      })
    }
  })

  const consensusEdits = {}
  const editConflicts = {}
  Object.entries(editsByField).forEach(([field, valueCounts]) => {
    const entries = Object.entries(valueCounts).sort((a, b) => b[1] - a[1])
    const topEditCount = entries[0][1]
    const tiedEditValues = entries.filter(([_, c]) => c === topEditCount)
    // C4: Only set consensus edit if there's a clear winner (no tie)
    if (tiedEditValues.length === 1) {
      consensusEdits[field] = entries[0][0]
    }
    if (entries.length > 1 || tiedEditValues.length > 1) {
      editConflicts[field] = entries.map(([v, c]) => ({ value: v, count: c }))
    }
  })

  return {
    reviewerCount: totalVoters,
    totalReviews,
    statusCounts,
    majorityStatus,
    isTie,
    tiedStatuses: isTie ? tiedStatuses.map(([s]) => s) : [],
    consensusRatio,
    outliers,
    hasConflict: Object.keys(statusCounts).length > 1,
    consensusEdits,
    editConflicts,
  }
}

/**
 * Build summaries for all items in log.
 * Returns { [itemId]: summary }
 */
export function getAllSummaries(log) {
  const summaries = {}
  const itemIds = new Set(log.map(r => r.itemId))
  itemIds.forEach(id => {
    const s = getItemSummary(log, id)
    if (s) summaries[id] = s
  })
  return summaries
}

/**
 * Verify integrity of log entries. Returns array of corrupted entry indices.
 */
export function verifyLogIntegrity(log) {
  const corrupted = []
  log.forEach((entry, i) => {
    if (entry.checksum && entry.checksum !== computeChecksum(entry)) {
      corrupted.push(i)
    }
  })
  return corrupted
}

/**
 * Merge an external review log into the current one (for importing from other browsers).
 * Deduplicates by (itemId + email + timestamp).
 */
export function mergeReviewLogs(externalLog) {
  const current = getReviewLog()
  const existingKeys = new Set(
    current.map(r => `${r.itemId}|${r.email}|${r.timestamp}`)
  )
  let added = 0
  externalLog.forEach(entry => {
    const key = `${entry.itemId}|${entry.email}|${entry.timestamp}`
    if (!existingKeys.has(key)) {
      current.push(entry)
      existingKeys.add(key)
      added++
    }
  })
  if (added > 0) {
    current.sort((a, b) => a.timestamp.localeCompare(b.timestamp))
    saveReviewLog(current)
  }
  return { merged: current, added }
}

/**
 * Get per-user review storage key.
 */
export function getUserReviewKey(email) {
  return `ocr_review_${email || 'anon'}`
}
