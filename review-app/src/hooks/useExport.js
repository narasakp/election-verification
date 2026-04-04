import { useCallback } from 'react'
import { getReviewLog, getAllSummaries, getAllAnomalyScores, verifyLogIntegrity } from '../utils/reviewLog'

const csvEsc = (v) => {
  const s = String(v == null ? '' : v)
  return s.includes(',') || s.includes('"') || s.includes('\n') ? '"' + s.replace(/"/g, '""') + '"' : s
}

function downloadBlob(blob, filename) {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
}

function dateSuffix() {
  return new Date().toISOString().slice(0, 10)
}

export default function useExport({ allItems, review, sharedEdits, filteredItems, reviewLog, user }) {

  const handleExportJSON = useCallback(() => {
    const summaries = getAllSummaries(reviewLog)
    const merged = allItems.map(item => {
      const rev = review[item.id]
      const constKey = `${item.province || ''}__${item.constituency || ''}`
      const shared = sharedEdits[constKey] || {}
      const summary = summaries[item.id]
      const base = !rev
        ? { ...item, ...shared, _review_status: 'pending' }
        : { ...item, ...shared, ...(rev.edits || {}), _review_status: rev.status, _review_note: rev.note }
      if (summary) {
        base._consensus_status = summary.majorityStatus || (summary.isTie ? 'disputed' : null)
        base._consensus_ratio = summary.consensusRatio
        base._is_tie = summary.isTie
        if (summary.isTie) base._tied_statuses = summary.tiedStatuses
        base._reviewer_count = summary.reviewerCount
        base._total_reviews = summary.totalReviews
        base._has_conflict = summary.hasConflict
        if (Object.keys(summary.consensusEdits).length > 0) base._consensus_edits = summary.consensusEdits
        if (Object.keys(summary.editConflicts).length > 0) base._edit_conflicts = summary.editConflicts
        if (summary.outliers.length > 0) base._outliers = summary.outliers
      }
      return base
    })
    downloadBlob(
      new Blob([JSON.stringify(merged, null, 2)], { type: 'application/json' }),
      `ocr_reviewed_${dateSuffix()}.json`
    )
  }, [allItems, review, sharedEdits, reviewLog])

  const handleExportAuditLog = useCallback(() => {
    const log = getReviewLog()
    const anomalyScores = getAllAnomalyScores(log)
    const corrupted = verifyLogIntegrity(log)
    const exportData = {
      exportedAt: new Date().toISOString(),
      exportedBy: user?.email || 'anonymous',
      logEntries: log.length,
      corruptedEntries: corrupted,
      anomalyScores,
      log,
    }
    downloadBlob(
      new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' }),
      `audit_log_${dateSuffix()}.json`
    )
  }, [user])

  const buildCSVRows = useCallback((items) => {
    const headers = ['file','page','province','constituency','station_no','sub_district','district','vote_type',
      'registered_voters','turnout','ballots_received','valid_ballots','invalid_ballots','no_vote_ballots','remaining_ballots','total_votes',
      'candidates_count','candidate_votes_sum','review_status','review_note']
    const rows = [headers.join(',')]
    items.forEach(d => {
      const rev = review[d.id] || {}
      const constKey = `${d.province || ''}__${d.constituency || ''}`
      const shared = sharedEdits[constKey] || {}
      const edits = rev.edits || {}
      const merged = { ...d, ...shared, ...edits }
      const cands = d.candidates || []
      const candSum = cands.reduce((s, c) => s + (Number(c.votes) || 0), 0)
      rows.push([
        csvEsc(merged.file), merged.page, csvEsc(merged.province), merged.constituency, merged.ocr_station_no,
        csvEsc(merged.sub_district), csvEsc(merged.district), csvEsc(merged.vote_type),
        merged.registered_voters, merged.turnout, merged.ballots_received, merged.valid_ballots,
        merged.invalid_ballots, merged.no_vote_ballots, merged.remaining_ballots, merged.total_votes,
        cands.length, candSum, rev.status || 'pending', csvEsc(rev.note || '')
      ].join(','))
    })
    return rows
  }, [review, sharedEdits])

  const handleExportCSV = useCallback(() => {
    const rows = buildCSVRows(allItems)
    downloadBlob(
      new Blob(['\uFEFF' + rows.join('\n')], { type: 'text/csv;charset=utf-8' }),
      `election_data_${dateSuffix()}.csv`
    )
  }, [allItems, buildCSVRows])

  const handleExportFilteredJSON = useCallback(() => {
    const summaries = getAllSummaries(reviewLog)
    const merged = filteredItems.map(item => {
      const rev = review[item.id]
      const constKey = `${item.province || ''}__${item.constituency || ''}`
      const shared = sharedEdits[constKey] || {}
      const summary = summaries[item.id]
      const base = !rev
        ? { ...item, ...shared, _review_status: 'pending' }
        : { ...item, ...shared, ...(rev.edits || {}), _review_status: rev.status, _review_note: rev.note }
      if (summary) {
        base._consensus_status = summary.majorityStatus || (summary.isTie ? 'disputed' : null)
        base._reviewer_count = summary.reviewerCount
      }
      return base
    })
    downloadBlob(
      new Blob([JSON.stringify(merged, null, 2)], { type: 'application/json' }),
      `ocr_filtered_${filteredItems.length}_${dateSuffix()}.json`
    )
  }, [filteredItems, review, sharedEdits, reviewLog])

  const handleExportFilteredCSV = useCallback(() => {
    const rows = buildCSVRows(filteredItems)
    downloadBlob(
      new Blob(['\uFEFF' + rows.join('\n')], { type: 'text/csv;charset=utf-8' }),
      `election_filtered_${filteredItems.length}_${dateSuffix()}.csv`
    )
  }, [filteredItems, buildCSVRows])

  const handleExportFullCSV = useCallback(() => {
    const constItems = allItems.filter(d => d.vote_type === 'แบ่งเขต')
    let maxCands = 0
    constItems.forEach(d => { const c = (d.candidates || []).length; if (c > maxCands) maxCands = c })
    const headers = ['file','page','province','constituency','station_no','sub_district','district','vote_type',
      'registered_voters','turnout','ballots_received','valid_ballots','invalid_ballots','no_vote_ballots','remaining_ballots','total_votes']
    for (let i = 1; i <= maxCands; i++) { headers.push(`cand${i}_no`, `cand${i}_name`, `cand${i}_party`, `cand${i}_votes`) }
    const rows = [headers.join(',')]
    constItems.forEach(d => {
      const row = [
        csvEsc(d.file), d.page, csvEsc(d.province), d.constituency, d.ocr_station_no,
        csvEsc(d.sub_district), csvEsc(d.district), csvEsc(d.vote_type),
        d.registered_voters, d.turnout, d.ballots_received, d.valid_ballots,
        d.invalid_ballots, d.no_vote_ballots, d.remaining_ballots, d.total_votes
      ]
      const cands = d.candidates || []
      for (let i = 0; i < maxCands; i++) {
        const c = cands[i]
        row.push(c ? c.number : '', c ? csvEsc(c.name) : '', c ? csvEsc(c.party) : '', c ? c.votes : '')
      }
      rows.push(row.join(','))
    })
    downloadBlob(
      new Blob(['\uFEFF' + rows.join('\n')], { type: 'text/csv;charset=utf-8' }),
      `election_constituency_${dateSuffix()}.csv`
    )
  }, [allItems])

  return {
    handleExportJSON,
    handleExportCSV,
    handleExportFullCSV,
    handleExportFilteredJSON,
    handleExportFilteredCSV,
    handleExportAuditLog,
  }
}
