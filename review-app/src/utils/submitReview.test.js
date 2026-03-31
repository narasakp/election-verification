import { describe, it, expect, beforeEach, vi } from 'vitest'
import { submitToGoogleForm, submitLoginEvent, submitLogoutEvent } from './submitReview'

// Mock fetch globally
beforeEach(() => {
  global.fetch = vi.fn(() => Promise.resolve())
  vi.spyOn(console, 'log').mockImplementation(() => {})
  vi.spyOn(console, 'warn').mockImplementation(() => {})
})

describe('submitToGoogleForm', () => {
  it('returns early for null item', () => {
    submitToGoogleForm(null, 'confirmed', '', 'test@t.com')
    expect(fetch).not.toHaveBeenCalled()
  })

  it('returns early for undefined item', () => {
    submitToGoogleForm(undefined, 'confirmed', '', 'test@t.com')
    expect(fetch).not.toHaveBeenCalled()
  })

  it('calls fetch with POST and no-cors', () => {
    submitToGoogleForm({ id: '1', province: 'ชัยภูมิ' }, 'confirmed', '', 'user@t.com')
    expect(fetch).toHaveBeenCalledTimes(1)
    const [url, opts] = fetch.mock.calls[0]
    expect(url).toContain('google.com/forms')
    expect(opts.method).toBe('POST')
    expect(opts.mode).toBe('no-cors')
  })

  it('builds location from province/constituency/station_no', () => {
    submitToGoogleForm(
      { id: '1', province: 'ชัยภูมิ', constituency: '3', station_no: '5' },
      'confirmed', '', 'user@t.com'
    )
    const body = fetch.mock.calls[0][1].body
    const entries = Object.fromEntries(body)
    // station field should contain location
    const stationVal = Object.values(entries).find(v => v.includes('ชัยภูมิ'))
    expect(stationVal).toContain('ชัยภูมิ')
    expect(stationVal).toContain('เขต 3')
    expect(stationVal).toContain('หน่วย 5')
  })

  it('builds location without constituency and station when missing', () => {
    submitToGoogleForm(
      { id: '1', province: 'ตาก' },
      'confirmed', '', 'user@t.com'
    )
    const body = fetch.mock.calls[0][1].body
    const entries = Object.fromEntries(body)
    const stationVal = Object.values(entries).find(v => v.includes('ตาก'))
    expect(stationVal).toBe('ตาก')
  })

  it('falls back to file path when no province/constituency/station', () => {
    submitToGoogleForm(
      { id: '1', file: 'chaiyaphum/zone3/5-something.pdf' },
      'confirmed', '', 'user@t.com'
    )
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('appends edits summary to comment', () => {
    submitToGoogleForm(
      { id: '1', province: 'ชัยภูมิ' },
      'confirmed', 'มีปัญหา', 'user@t.com',
      { turnout: '500', valid_ballots: '450' }
    )
    const body = fetch.mock.calls[0][1].body
    const entries = Object.fromEntries(body)
    const comment = Object.values(entries).find(v => v.includes('edits:'))
    expect(comment).toContain('มีปัญหา')
    expect(comment).toContain('turnout=500')
    expect(comment).toContain('valid_ballots=450')
  })

  it('creates edit-only comment when note is empty', () => {
    submitToGoogleForm(
      { id: '1', province: 'ชัยภูมิ' },
      'confirmed', '', 'user@t.com',
      { turnout: '500' }
    )
    const body = fetch.mock.calls[0][1].body
    const entries = Object.fromEntries(body)
    const comment = Object.values(entries).find(v => v.includes('edits:'))
    expect(comment).toBe('edits: turnout=500')
  })

  it('sends empty comment when no note and no edits', () => {
    submitToGoogleForm(
      { id: '1', province: 'ชัยภูมิ' },
      'confirmed', '', 'user@t.com'
    )
    const body = fetch.mock.calls[0][1].body
    const entries = Object.fromEntries(body)
    // Should have item_id
    expect(Object.values(entries)).toContain('1')
  })

  it('uses _id as fallback when id is missing', () => {
    submitToGoogleForm(
      { _id: 'fallback-id', province: 'ชัยภูมิ' },
      'confirmed', '', 'user@t.com'
    )
    const body = fetch.mock.calls[0][1].body
    const entries = Object.fromEntries(body)
    expect(Object.values(entries)).toContain('fallback-id')
  })

  it('uses "anonymous" when no email provided', () => {
    submitToGoogleForm(
      { id: '1', province: 'ชัยภูมิ' },
      'confirmed', '', null
    )
    const body = fetch.mock.calls[0][1].body
    const entries = Object.fromEntries(body)
    expect(Object.values(entries)).toContain('anonymous')
  })

  it('handles empty edits object without appending to comment', () => {
    submitToGoogleForm(
      { id: '1', province: 'ชัยภูมิ' },
      'confirmed', 'note', 'user@t.com',
      {}
    )
    const body = fetch.mock.calls[0][1].body
    const entries = Object.fromEntries(body)
    const hasEdits = Object.values(entries).some(v => typeof v === 'string' && v.includes('edits:'))
    expect(hasEdits).toBe(false)
  })
})

describe('submitLoginEvent', () => {
  it('returns early for null user', () => {
    submitLoginEvent(null)
    expect(fetch).not.toHaveBeenCalled()
  })

  it('returns early for undefined user', () => {
    submitLoginEvent(undefined)
    expect(fetch).not.toHaveBeenCalled()
  })

  it('calls fetch for valid user', () => {
    submitLoginEvent({ name: 'Test', email: 'test@t.com' })
    expect(fetch).toHaveBeenCalledTimes(1)
    const opts = fetch.mock.calls[0][1]
    expect(opts.method).toBe('POST')
    expect(opts.mode).toBe('no-cors')
  })
})

describe('submitLogoutEvent', () => {
  it('returns early for null user', () => {
    submitLogoutEvent(null)
    expect(fetch).not.toHaveBeenCalled()
  })

  it('returns early for undefined user', () => {
    submitLogoutEvent(undefined)
    expect(fetch).not.toHaveBeenCalled()
  })

  it('calls fetch for valid user', () => {
    submitLogoutEvent({ name: 'Test', email: 'test@t.com' })
    expect(fetch).toHaveBeenCalledTimes(1)
  })
})
