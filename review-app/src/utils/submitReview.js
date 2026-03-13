const GFORM_ACTION_URL = 'https://docs.google.com/forms/d/e/1FAIpQLSce7goUhOdE9cVMgBgRMvlTgXgxjGrodegYcWcONpAOo1yXDQ/formResponse'
const GF = {
  item_id:  'entry.1812182732',
  file:     'entry.619280192',
  station:  'entry.1502652563',
  status:   'entry.1026213585',
  comment:  'entry.970714276',
  email:    'entry.1982549206',
}

export function submitLoginEvent(user) {
  if (!user) return
  _submitEvent('login', user)
}

export function submitLogoutEvent(user) {
  if (!user) return
  _submitEvent('logout', user)
}

function _submitEvent(eventType, user) {
  const body = new FormData()
  body.append(GF.item_id, eventType.toUpperCase())
  body.append(GF.file, navigator.userAgent || '')
  body.append(GF.station, new Date().toISOString())
  body.append(GF.status, eventType)
  body.append(GF.comment, user.name || '')
  body.append(GF.email, user.email || '')

  console.log(`Logging ${eventType}:`, user.email)
  fetch(GFORM_ACTION_URL, {
    method: 'POST',
    mode: 'no-cors',
    body,
  }).catch(() => {})
}

export function submitToGoogleForm(item, status, note, userEmail, edits) {
  if (!item) return

  // Build location: จังหวัด / เขต / หน่วย
  let loc = [
    item.province,
    item.constituency ? 'เขต ' + item.constituency : '',
    item.station_no ? 'หน่วย ' + item.station_no : '',
  ].filter(Boolean).join(' / ')

  // Fallback: parse from file path
  if (!loc && item.file) {
    const parts = item.file.split('/')
    const locParts = parts.slice(0, Math.min(parts.length - 1, 3))
    if (locParts.length >= 3) locParts[2] = 'หน่วย ' + locParts[2].split('-')[0]
    if (locParts.length >= 1) locParts[0] = locParts[0].replace('จังหวัด', '')
    if (locParts.length >= 2) locParts[1] = locParts[1].replace('เลือกตั้ง', '')
    loc = locParts.join(' / ')
  }

  // Append edits summary to comment for full audit trail
  let comment = note || ''
  if (edits && typeof edits === 'object' && Object.keys(edits).length > 0) {
    const editsSummary = Object.entries(edits).map(([k, v]) => `${k}=${v}`).join(', ')
    comment = comment ? `${comment} | edits: ${editsSummary}` : `edits: ${editsSummary}`
  }

  const body = new FormData()
  body.append(GF.item_id, item.id || item._id || '')
  body.append(GF.file, item.file || '')
  body.append(GF.station, loc)
  body.append(GF.status, status)
  body.append(GF.comment, comment)
  body.append(GF.email, userEmail || 'anonymous')

  console.log('Submitting to Google Form:', Object.fromEntries(body))

  fetch(GFORM_ACTION_URL, {
    method: 'POST',
    mode: 'no-cors',
    body,
  }).then(() => {
    console.log('Review submitted to Google Form')
  }).catch(err => {
    console.warn('Google Form submission error:', err)
  })
}
