import React, { useState, useMemo } from 'react'
import { GitCompareArrows, ChevronDown, ChevronRight, AlertTriangle, CheckCircle2, XCircle, ArrowUp, ArrowDown, ArrowUpDown } from 'lucide-react'
import ErrorBoundary from './ErrorBoundary'
import { validateItem, getWorstSeverity } from '../utils/validation'

function SeverityBadge({ severity }) {
  const cls = {
    error: 'bg-red-100 text-red-700',
    warning: 'bg-amber-100 text-amber-700',
    info: 'bg-blue-100 text-blue-700',
    ok: 'bg-emerald-100 text-emerald-700',
  }[severity] || 'bg-gray-100 text-gray-500'
  const label = { error: 'Error', warning: 'Warning', info: 'Info', ok: 'OK' }[severity] || severity
  return <span className={`text-[9px] px-1.5 py-0.5 rounded font-medium ${cls}`}>{label}</span>
}

function CrossReferencePanelInner({ allItems, review, anomalyFlags, anomalyMeta }) {
  const [expanded, setExpanded] = useState(false)
  const [filterSeverity, setFilterSeverity] = useState('all') // all | error | warning | info
  const [sortCol, setSortCol] = useState('severity')
  const [sortAsc, setSortAsc] = useState(false)
  const [page, setPage] = useState(0)
  const PAGE_SIZE = 20

  // Build per-constituency comparison data
  const comparisonData = useMemo(() => {
    // Group items by province_constituency
    const groups = {}
    allItems.forEach(item => {
      const key = `${item.province || '?'}_${item.constituency || '?'}`
      if (!groups[key]) {
        groups[key] = {
          key,
          province: item.province || '?',
          constituency: item.constituency || '?',
          voteType: item.vote_type || '?',
          items: [],
          ocrTurnout: 0,
          ocrValid: 0,
          ocrInvalid: 0,
          ocrTotal: 0,
          stationCount: 0,
        }
      }
      groups[key].items.push(item)
    })

    // Aggregate OCR data and compare with ECT anomaly flags
    return Object.values(groups).map(g => {
      let turnoutSum = 0, validSum = 0, invalidSum = 0, totalVotesSum = 0, stationSet = new Set()
      let errorCount = 0, warningCount = 0

      g.items.forEach(item => {
        turnoutSum += Number(item.turnout) || 0
        validSum += Number(item.valid_ballots) || 0
        invalidSum += Number(item.invalid_ballots) || 0
        totalVotesSum += Number(item.total_votes) || 0
        const stn = item.ocr_station_no || item.station_no
        if (stn) stationSet.add(stn)

        const warns = validateItem(item)
        warns.forEach(w => {
          if (w.severity === 'error') errorCount++
          else if (w.severity === 'warning') warningCount++
        })
      })

      // ECT anomaly flags for this constituency
      const ectFlags = anomalyFlags[g.key] || anomalyFlags[`${g.province}_${g.constituency}`] || null
      const flagCount = ectFlags ? (Array.isArray(ectFlags) ? ectFlags.length : Object.keys(ectFlags).length) : 0

      // Review status
      let reviewed = 0, confirmed = 0, rejected = 0
      g.items.forEach(item => {
        const st = (review[item.id] || {}).status || 'pending'
        if (st !== 'pending') reviewed++
        if (st === 'confirmed') confirmed++
        if (st === 'rejected') rejected++
      })

      // Determine overall severity
      let severity = 'ok'
      if (errorCount > 0 || rejected > 0) severity = 'error'
      else if (warningCount > 0 || flagCount > 0) severity = 'warning'
      else if (g.items.length === 0) severity = 'info'

      return {
        ...g,
        ocrTurnout: turnoutSum,
        ocrValid: validSum,
        ocrInvalid: invalidSum,
        ocrTotal: totalVotesSum,
        stationCount: stationSet.size,
        errorCount,
        warningCount,
        flagCount,
        reviewed,
        confirmed,
        rejected,
        reviewPct: g.items.length > 0 ? (reviewed / g.items.length * 100) : 0,
        severity,
      }
    })
  }, [allItems, review, anomalyFlags])

  // Filter
  const filtered = useMemo(() => {
    let data = comparisonData
    if (filterSeverity !== 'all') {
      data = data.filter(d => d.severity === filterSeverity)
    }
    return data
  }, [comparisonData, filterSeverity])

  // Sort
  const sorted = useMemo(() => {
    const arr = [...filtered]
    const sevOrder = { error: 3, warning: 2, info: 1, ok: 0 }
    arr.sort((a, b) => {
      let va, vb
      switch (sortCol) {
        case 'province': va = a.province; vb = b.province; return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va)
        case 'constituency': va = Number(a.constituency) || 0; vb = Number(b.constituency) || 0; break
        case 'stations': va = a.stationCount; vb = b.stationCount; break
        case 'errors': va = a.errorCount; vb = b.errorCount; break
        case 'flags': va = a.flagCount; vb = b.flagCount; break
        case 'reviewPct': va = a.reviewPct; vb = b.reviewPct; break
        case 'severity': va = sevOrder[a.severity] || 0; vb = sevOrder[b.severity] || 0; break
        default: return 0
      }
      return sortAsc ? va - vb : vb - va
    })
    return arr
  }, [filtered, sortCol, sortAsc])

  // Paginate
  const paged = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
  const totalPages = Math.ceil(sorted.length / PAGE_SIZE)

  // Summary counts
  const summary = useMemo(() => ({
    total: comparisonData.length,
    errors: comparisonData.filter(d => d.severity === 'error').length,
    warnings: comparisonData.filter(d => d.severity === 'warning').length,
    ok: comparisonData.filter(d => d.severity === 'ok').length,
  }), [comparisonData])

  const toggleSort = (col) => {
    if (sortCol === col) setSortAsc(v => !v)
    else { setSortCol(col); setSortAsc(col === 'province') }
  }

  const SortTh = ({ col, align = 'left', children }) => {
    const active = sortCol === col
    return (
      <th
        className={`px-2 py-1.5 text-${align} cursor-pointer select-none hover:text-gray-700 transition`}
        onClick={() => toggleSort(col)}
      >
        <span className="inline-flex items-center gap-0.5">
          {children}
          {active ? (sortAsc ? <ArrowUp size={9} /> : <ArrowDown size={9} />) : <ArrowUpDown size={8} className="opacity-30" />}
        </span>
      </th>
    )
  }

  if (allItems.length === 0) return null

  return (
    <div className="max-w-[1400px] mx-auto px-4 mt-3">
      <button
        onClick={() => setExpanded(v => !v)}
        className="flex items-center gap-2 text-sm font-semibold text-gray-700 hover:text-indigo-700 transition mb-2"
      >
        {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        <GitCompareArrows size={16} className="text-purple-500" />
        🔬 Cross-Reference: OCR vs ECT
        <span className="text-xs font-normal text-gray-400 ml-2">
          {summary.total} เขต · {summary.errors} errors · {summary.warnings} warnings
        </span>
      </button>

      {expanded && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-4">
          {/* Summary cards */}
          <div className="flex items-center gap-3">
            {[
              { label: 'ทั้งหมด', count: summary.total, cls: 'bg-gray-50 text-gray-700', filter: 'all' },
              { label: 'Error', count: summary.errors, cls: 'bg-red-50 text-red-700', filter: 'error' },
              { label: 'Warning', count: summary.warnings, cls: 'bg-amber-50 text-amber-700', filter: 'warning' },
              { label: 'OK', count: summary.ok, cls: 'bg-emerald-50 text-emerald-700', filter: 'ok' },
            ].map(s => (
              <button
                key={s.filter}
                onClick={() => { setFilterSeverity(s.filter); setPage(0) }}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                  filterSeverity === s.filter ? s.cls + ' ring-2 ring-offset-1 ring-indigo-300' : 'bg-gray-50 text-gray-500 hover:bg-gray-100'
                }`}
              >
                {s.label} ({s.count})
              </button>
            ))}
          </div>

          {anomalyMeta && (
            <div className="text-[10px] text-gray-400">
              ข้อมูล ECT: {anomalyMeta.generated || '—'} · {anomalyMeta.total_flags || 0} flags ทั้งหมด
            </div>
          )}

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-[10px] text-gray-500 uppercase border-b border-gray-200 bg-gray-50">
                  <SortTh col="severity" align="center">สถานะ</SortTh>
                  <SortTh col="province" align="left">จังหวัด</SortTh>
                  <SortTh col="constituency" align="center">เขต</SortTh>
                  <SortTh col="stations" align="center">หน่วย</SortTh>
                  <th className="px-2 py-1.5 text-right">OCR Turnout</th>
                  <th className="px-2 py-1.5 text-right">OCR Valid</th>
                  <SortTh col="errors" align="center">Errors</SortTh>
                  <SortTh col="flags" align="center">ECT Flags</SortTh>
                  <SortTh col="reviewPct" align="center">Review %</SortTh>
                </tr>
              </thead>
              <tbody>
                {paged.map((row, i) => (
                  <tr key={row.key} className="border-b border-gray-50 hover:bg-gray-50 transition">
                    <td className="px-2 py-2 text-center"><SeverityBadge severity={row.severity} /></td>
                    <td className="px-2 py-2 font-medium text-gray-700">{row.province}</td>
                    <td className="px-2 py-2 text-center">{row.constituency}</td>
                    <td className="px-2 py-2 text-center text-gray-500">{row.stationCount}</td>
                    <td className="px-2 py-2 text-right font-mono text-gray-600">{row.ocrTurnout.toLocaleString()}</td>
                    <td className="px-2 py-2 text-right font-mono text-gray-600">{row.ocrValid.toLocaleString()}</td>
                    <td className="px-2 py-2 text-center">
                      {row.errorCount > 0 ? (
                        <span className="bg-red-100 text-red-700 px-1.5 py-0.5 rounded font-mono">{row.errorCount}</span>
                      ) : (
                        <span className="text-gray-300">0</span>
                      )}
                    </td>
                    <td className="px-2 py-2 text-center">
                      {row.flagCount > 0 ? (
                        <span className="bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded font-mono">{row.flagCount}</span>
                      ) : (
                        <span className="text-gray-300">0</span>
                      )}
                    </td>
                    <td className="px-2 py-2 text-center">
                      <div className="flex items-center gap-1">
                        <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${row.reviewPct >= 100 ? 'bg-emerald-500' : row.reviewPct > 50 ? 'bg-indigo-400' : 'bg-amber-400'}`}
                            style={{ width: `${row.reviewPct}%` }}
                          />
                        </div>
                        <span className="text-[9px] text-gray-400 w-8 text-right">{row.reviewPct.toFixed(0)}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>แสดง {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, sorted.length)} จาก {sorted.length}</span>
              <div className="flex gap-1">
                <button
                  onClick={() => setPage(p => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="px-2 py-1 bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-30"
                >
                  ← ก่อนหน้า
                </button>
                <button
                  onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                  disabled={page >= totalPages - 1}
                  className="px-2 py-1 bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-30"
                >
                  ถัดไป →
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function CrossReferencePanel(props) {
  return (
    <ErrorBoundary compact>
      <CrossReferencePanelInner {...props} />
    </ErrorBoundary>
  )
}
