/**
 * Fetch review data from the published Google Sheet (linked to Google Form).
 * This allows the admin/employer to see ALL reviewers' progress,
 * not just the local browser's localStorage.
 *
 * The Google Sheet must be:
 * 1. Shared as "Anyone with the link can view"
 * 2. Published to web (File → Share → Publish to web → CSV)
 */

const SHEET_ID = '1mBkP2kS4TWB-PqijYQoJ7C2fZEi-cicZqN7jM47sGow'
const GID = '1556112815'

// Try multiple URL formats for robustness
const SHEET_URLS = [
  `https://docs.google.com/spreadsheets/d/${SHEET_ID}/gviz/tq?tqx=out:csv&gid=${GID}`,
  `https://docs.google.com/spreadsheets/d/${SHEET_ID}/export?format=csv&gid=${GID}`,
  `https://docs.google.com/spreadsheets/d/${SHEET_ID}/pub?gid=${GID}&single=true&output=csv`,
]

const CACHE_KEY = 'ocr_remote_reviews'
const CACHE_TTL_MS = 2 * 60 * 1000 // 2 minutes cache

/**
 * Parse a CSV line handling quoted fields with commas.
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
        i++ // skip escaped quote
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
 * Parse Google Sheet CSV into review log entries.
 *
 * Expected Google Form columns (order may vary):
 * Timestamp | item_id | file | station/location | status | comment | email
 *
 * We detect columns by header name matching.
 */
function parseSheetCSV(csvText) {
  const lines = csvText.split('\n').filter(l => l.trim())
  if (lines.length < 2) return []

  const headers = parseCSVLine(lines[0]).map(h => h.toLowerCase().trim())

  // Auto-detect column indices by matching known patterns
  const colMap = {}
  headers.forEach((h, i) => {
    if (/timestamp|เวลา/.test(h)) colMap.timestamp = i
    else if (/item.?id|รหัส/.test(h)) colMap.itemId = i
    else if (/status|สถานะ/.test(h)) colMap.status = i
    else if (/email|อีเมล/.test(h)) colMap.email = i
    else if (/comment|หมายเหตุ|note/.test(h)) colMap.note = i
    else if (/file|ไฟล์/.test(h)) colMap.file = i
    else if (/station|สถานที่|location/.test(h)) colMap.station = i
  })

  // Fallback: if auto-detect fails, assume standard Google Form order
  // Column 0 = Timestamp (auto), then form fields in order they appear in form
  if (colMap.timestamp == null && headers.length >= 7) {
    colMap.timestamp = 0
    colMap.itemId = 1
    colMap.file = 2
    colMap.station = 3
    colMap.status = 4
    colMap.note = 5
    colMap.email = 6
  }

  if (colMap.itemId == null || colMap.status == null || colMap.email == null) {
    console.warn('[fetchRemoteReviews] Could not detect columns. Headers:', headers)
    return []
  }

  const entries = []
  for (let i = 1; i < lines.length; i++) {
    const cols = parseCSVLine(lines[i])
    if (cols.length < 3) continue

    const itemId = cols[colMap.itemId] || ''
    const status = (cols[colMap.status] || '').toLowerCase().trim()
    const email = cols[colMap.email] || ''
    const timestamp = cols[colMap.timestamp] || ''
    const note = cols[colMap.note] || ''

    // Skip non-review entries (login/logout events)
    if (!itemId || itemId === 'LOGIN' || itemId === 'LOGOUT') continue
    // Skip invalid statuses
    if (!['confirmed', 'flagged', 'rejected', 'pending'].includes(status)) continue
    if (!email) continue

    // Parse Google timestamp format: "4/16/2025 13:45:00" → ISO
    let isoTimestamp = timestamp
    try {
      const d = new Date(timestamp)
      if (!isNaN(d.getTime())) {
        isoTimestamp = d.toISOString()
      }
    } catch {}

    // Parse edits from comment field (format: "note text | edits: field1=val1, field2=val2")
    let edits = {}
    let cleanNote = note
    const editsMatch = note.match(/\|\s*edits:\s*(.+)$/)
    if (editsMatch) {
      cleanNote = note.replace(editsMatch[0], '').trim()
      editsMatch[1].split(',').forEach(pair => {
        const [k, v] = pair.split('=').map(s => s.trim())
        if (k && v !== undefined) {
          edits[k] = isNaN(Number(v)) ? v : Number(v)
        }
      })
    }

    entries.push({
      itemId,
      email,
      name: email.split('@')[0],
      status,
      note: cleanNote,
      edits,
      timestamp: isoTimestamp,
      _remote: true,
    })
  }

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
      const response = await fetch(url, { cache: 'no-cache' })
      if (!response.ok) {
        lastError = `HTTP ${response.status}: ${response.statusText}`
        continue
      }
      const csvText = await response.text()
      if (!csvText || csvText.length < 10 || csvText.includes('<!DOCTYPE html>')) {
        lastError = 'ได้รับ HTML แทน CSV — Sheet อาจยังไม่ได้ publish หรือ share'
        continue
      }

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

      console.log(`[fetchRemoteReviews] Fetched ${entries.length} review entries from Google Sheet`)
      return { entries, error: null, fromCache: false, fetchedAt }
    } catch (err) {
      lastError = err.message
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
