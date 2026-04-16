/**
 * Fetch review data from the published Google Sheet (linked to Google Form).
 * This allows the admin/employer to see ALL reviewers' progress,
 * not just the local browser's localStorage.
 *
 * The Google Sheet must be shared as "Anyone with the link can view/edit".
 *
 * Google Form field order (known, hardcoded):
 *   Col 0 = Timestamp (auto by Google)
 *   Col 1 = 1. รหัสรายการ  (item_id)
 *   Col 2 = 2. ชื่อไฟล์    (file)
 *   Col 3 = 3. สถานที่      (station/location)
 *   Col 4 = 4. สถานะ       (status: confirmed/flagged/rejected/pending/login/logout)
 *   Col 5 = 5. หมายเหตุ    (comment/note)
 *   Col 6 = 6. อีเมลผู้ตรวจ (email)
 */

const SHEET_ID = '1mBkP2kS4TWB-PqijYQoJ7C2fZEi-cicZqN7jM47sGow'
const GID = '1556112815'

// Try multiple URL formats for robustness
const SHEET_URLS = [
  `https://docs.google.com/spreadsheets/d/${SHEET_ID}/gviz/tq?tqx=out:csv&gid=${GID}`,
  `https://docs.google.com/spreadsheets/d/${SHEET_ID}/export?format=csv&gid=${GID}`,
  `https://docs.google.com/spreadsheets/d/${SHEET_ID}/pub?gid=${GID}&single=true&output=csv`,
]

// Hardcoded column positions matching Google Form field order
const COL = { timestamp: 0, itemId: 1, file: 2, station: 3, status: 4, note: 5, email: 6 }

const VALID_STATUSES = new Set(['confirmed', 'flagged', 'rejected', 'pending'])
const SKIP_ITEM_IDS = new Set(['LOGIN', 'LOGOUT', 'login', 'logout', ''])

const CACHE_KEY = 'ocr_remote_reviews'
const CACHE_TTL_MS = 2 * 60 * 1000 // 2 minutes cache

/**
 * Parse a CSV line handling quoted fields with commas and newlines.
 */
function parseCSVLine(line) {
  const result = []
  let current = ''
  let inQuotes = false
  for (let i = 0; i < line.length; i++) {
    const ch = line[i]
    if (inQuotes) {
      if (ch === '"' && line[i + 1] === '"') {
        current += '"'
        i++
      } else if (ch === '"') {
        inQuotes = false
      } else {
        current += ch
      }
    } else {
      if (ch === '"') {
        inQuotes = true
      } else if (ch === ',') {
        result.push(current.trim())
        current = ''
      } else {
        current += ch
      }
    }
  }
  result.push(current.trim())
  return result
}

/**
 * Parse a gviz Date() value like "Date(2026,3,8,9,13,48)" → ISO string.
 * gviz months are 0-indexed.
 */
function parseGvizDate(str) {
  const m = str.match(/Date\((\d+),(\d+),(\d+)(?:,(\d+),(\d+),(\d+))?\)/)
  if (!m) return null
  const d = new Date(+m[1], +m[2], +m[3], +(m[4] || 0), +(m[5] || 0), +(m[6] || 0))
  return isNaN(d.getTime()) ? null : d.toISOString()
}

/**
 * Parse any timestamp format → ISO string.
 */
function parseTimestamp(raw) {
  if (!raw) return ''
  // gviz Date() format
  if (raw.startsWith('Date(')) {
    return parseGvizDate(raw) || raw
  }
  // Standard date string
  try {
    const d = new Date(raw)
    if (!isNaN(d.getTime())) return d.toISOString()
  } catch {}
  return raw
}

/**
 * Parse Google Sheet CSV into review log entries.
 * Uses hardcoded column positions (we know the exact Google Form field order).
 */
function parseSheetCSV(csvText) {
  // Strip BOM and normalize line endings
  let text = csvText.replace(/^\uFEFF/, '').replace(/\r\n/g, '\n').replace(/\r/g, '\n')

  const lines = text.split('\n').filter(l => l.trim())
  if (lines.length < 2) {
    console.warn('[fetchRemoteReviews] CSV has < 2 lines. Length:', csvText.length)
    return []
  }

  const headers = parseCSVLine(lines[0])
  console.log('[fetchRemoteReviews] Headers:', headers)
  console.log('[fetchRemoteReviews] Total rows (incl header):', lines.length)

  // Try auto-detect columns, but always fall back to hardcoded positions
  const colMap = { ...COL }
  const headersLower = headers.map(h => h.toLowerCase().trim())
  headersLower.forEach((h, i) => {
    if (/timestamp|เวลา/.test(h)) colMap.timestamp = i
    else if (/รหัส|item.?id/.test(h)) colMap.itemId = i
    else if (/สถานะ|status/.test(h)) colMap.status = i
    else if (/อีเมล|email/.test(h)) colMap.email = i
    else if (/หมายเหตุ|comment|note/.test(h)) colMap.note = i
    else if (/ไฟล์|file/.test(h)) colMap.file = i
    else if (/สถานที่|station|location/.test(h)) colMap.station = i
  })

  console.log('[fetchRemoteReviews] Column map:', colMap)

  const entries = []
  let skippedLogin = 0, skippedStatus = 0, skippedEmpty = 0
  for (let i = 1; i < lines.length; i++) {
    const cols = parseCSVLine(lines[i])
    if (cols.length < 5) { skippedEmpty++; continue }

    const rawItemId = (cols[colMap.itemId] || '').trim()
    const rawStatus = (cols[colMap.status] || '').trim()
    const rawEmail = (cols[colMap.email] || '').trim()
    const rawTimestamp = (cols[colMap.timestamp] || '').trim()
    const rawNote = (cols[colMap.note] || '').trim()

    // Normalize status: lowercase, strip whitespace
    const status = rawStatus.toLowerCase().replace(/\s+/g, '')

    // Skip login/logout events and empty rows
    if (SKIP_ITEM_IDS.has(rawItemId) || SKIP_ITEM_IDS.has(rawItemId.toUpperCase())) {
      skippedLogin++
      continue
    }
    // Skip invalid statuses
    if (!VALID_STATUSES.has(status)) {
      skippedStatus++
      // Log first few skipped for debugging
      if (skippedStatus <= 3) {
        console.log(`[fetchRemoteReviews] Skipped row ${i}: status="${rawStatus}" (normalized="${status}"), itemId="${rawItemId.substring(0, 30)}"`)
      }
      continue
    }
    if (!rawEmail) { skippedEmpty++; continue }

    const isoTimestamp = parseTimestamp(rawTimestamp)

    // Parse edits from comment field (format: "note text | edits: field1=val1, field2=val2")
    let edits = {}
    let cleanNote = rawNote
    const editsMatch = rawNote.match(/\|\s*edits:\s*(.+)$/)
    if (editsMatch) {
      cleanNote = rawNote.replace(editsMatch[0], '').trim()
      editsMatch[1].split(',').forEach(pair => {
        const eqIdx = pair.indexOf('=')
        if (eqIdx > 0) {
          const k = pair.substring(0, eqIdx).trim()
          const v = pair.substring(eqIdx + 1).trim()
          if (k) edits[k] = isNaN(Number(v)) ? v : Number(v)
        }
      })
    }

    entries.push({
      itemId: rawItemId,
      email: rawEmail,
      name: rawEmail.split('@')[0],
      status,
      note: cleanNote,
      edits,
      timestamp: isoTimestamp,
      _remote: true,
    })
  }

  console.log(`[fetchRemoteReviews] Parsed: ${entries.length} valid, skipped: ${skippedLogin} login/logout, ${skippedStatus} invalid status, ${skippedEmpty} empty/short`)

  return entries
}

/**
 * Fetch remote reviews from Google Sheet.
 * Uses caching to avoid excessive requests.
 * @param {boolean} forceRefresh - bypass cache
 * @returns {Promise<{entries: Array, error: string|null, fromCache: boolean, fetchedAt: string}>}
 */
export async function fetchRemoteReviews(forceRefresh = false) {
  // Check cache first
  if (!forceRefresh) {
    try {
      const cached = JSON.parse(sessionStorage.getItem(CACHE_KEY) || 'null')
      if (cached && (Date.now() - cached.fetchedAtMs) < CACHE_TTL_MS) {
        return { entries: cached.entries, error: null, fromCache: true, fetchedAt: cached.fetchedAt }
      }
    } catch {}
  }

  let lastError = null
  for (const url of SHEET_URLS) {
    try {
      console.log(`[fetchRemoteReviews] Trying: ${url.substring(0, 80)}...`)
      const response = await fetch(url, { cache: 'no-cache' })
      if (!response.ok) {
        lastError = `HTTP ${response.status}: ${response.statusText}`
        console.warn(`[fetchRemoteReviews] ${lastError}`)
        continue
      }
      const csvText = await response.text()

      // Check for HTML error pages
      if (!csvText || csvText.length < 10) {
        lastError = `Response too short (${csvText?.length || 0} chars)`
        continue
      }
      if (csvText.includes('<!DOCTYPE html>') || csvText.includes('<html')) {
        lastError = 'ได้รับ HTML แทน CSV — Sheet อาจยังไม่ได้ publish หรือ share'
        console.warn('[fetchRemoteReviews] Got HTML instead of CSV. First 200 chars:', csvText.substring(0, 200))
        continue
      }

      console.log(`[fetchRemoteReviews] Got CSV: ${csvText.length} chars, first 300:`, csvText.substring(0, 300))

      const entries = parseSheetCSV(csvText)
      const fetchedAt = new Date().toISOString()

      // Cache in sessionStorage
      try {
        sessionStorage.setItem(CACHE_KEY, JSON.stringify({
          entries,
          fetchedAt,
          fetchedAtMs: Date.now(),
        }))
      } catch {}

      console.log(`[fetchRemoteReviews] SUCCESS: ${entries.length} review entries from ${url.includes('gviz') ? 'gviz' : url.includes('export') ? 'export' : 'pub'}`)
      return { entries, error: null, fromCache: false, fetchedAt }
    } catch (err) {
      lastError = err.message
      console.warn(`[fetchRemoteReviews] Fetch error:`, err.message)
    }
  }

  return { entries: [], error: lastError || 'ไม่สามารถเชื่อมต่อ Google Sheet ได้', fromCache: false, fetchedAt: null }
}

/**
 * Merge remote review entries with local review log.
 * Returns combined log, deduplicated by (itemId + email + timestamp).
 * Does NOT persist to localStorage — for display purposes only.
 */
export function mergeLocalAndRemote(localLog, remoteEntries) {
  const keySet = new Set(
    localLog.map(r => `${r.itemId}|${r.email}|${r.timestamp}`)
  )

  const merged = [...localLog]
  let addedCount = 0

  remoteEntries.forEach(entry => {
    const key = `${entry.itemId}|${entry.email}|${entry.timestamp}`
    if (!keySet.has(key)) {
      merged.push(entry)
      keySet.add(key)
      addedCount++
    }
  })

  merged.sort((a, b) => (a.timestamp || '').localeCompare(b.timestamp || ''))

  return { merged, addedCount, totalRemote: remoteEntries.length, totalLocal: localLog.length }
}
