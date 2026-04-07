import React, { useState, useMemo, useEffect } from 'react'
import { GitCompareArrows, ChevronDown, ChevronRight, ArrowUp, ArrowDown, ArrowUpDown, Database, ExternalLink } from 'lucide-react'
import ErrorBoundary from './ErrorBoundary'
import { validateItem } from '../utils/validation'

const CROSS_REF_URL = './data/cross_reference_sources.json'

const SOURCE_COLORS = {
  ocr: { bg: 'bg-indigo-50', text: 'text-indigo-700', bar: 'bg-indigo-500', border: 'border-indigo-200', label: 'ระบบ OCR ของเรา', icon: '🔬', url: 'https://github.com/narasakp/election-verification' },
  ect: { bg: 'bg-blue-50', text: 'text-blue-700', bar: 'bg-blue-500', border: 'border-blue-200', label: 'กกต. (ECT)', icon: '🏛️' },
  killernay: { bg: 'bg-emerald-50', text: 'text-emerald-700', bar: 'bg-emerald-500', border: 'border-emerald-200', label: 'Killernay', icon: '📊' },
  luengnat: { bg: 'bg-purple-50', text: 'text-purple-700', bar: 'bg-purple-500', border: 'border-purple-200', label: 'Luengnat', icon: '📈' },
}

const SEVERITY_CRITERIA = {
  error: '|max(กกต.,KN,LN) − OCR| / MAX > 25%',
  warning: '|MAX − OCR| / MAX > 10%',
  mismatch: '|MAX − OCR| / MAX > 3%',
  ok: 'OCR ใกล้เคียงแหล่งอ้างอิง (diff ≤ 3%) หรือยังไม่มีข้อมูล OCR',
}

function SeverityBadge({ severity }) {
  const cls = {
    error: 'bg-red-100 text-red-700',
    warning: 'bg-amber-100 text-amber-700',
    ok: 'bg-emerald-100 text-emerald-700',
    mismatch: 'bg-orange-100 text-orange-700',
  }[severity] || 'bg-gray-100 text-gray-500'
  const label = { error: 'Error', warning: 'Warning', ok: 'OK', mismatch: 'Mismatch' }[severity] || severity
  return <span className={`text-[9px] px-1.5 py-0.5 rounded font-medium cursor-help ${cls}`} title={SEVERITY_CRITERIA[severity] || ''}>{label}</span>
}

function DiffBar({ val, refVal, maxVal, color }) {
  if (!refVal || !maxVal) return <span className="text-gray-300 text-[10px]">—</span>
  const pct = (val / maxVal) * 100
  const refPct = (refVal / maxVal) * 100
  const diff = val - refVal
  const diffPct = refVal > 0 ? ((diff / refVal) * 100) : 0
  const absDiffPct = Math.abs(diffPct)
  const barColor = absDiffPct > 10 ? 'bg-red-400' : absDiffPct > 3 ? 'bg-amber-400' : color
  return (
    <div className="flex items-center gap-1" title={`${val.toLocaleString()} (diff: ${diff >= 0 ? '+' : ''}${diff.toLocaleString()}, ${diffPct.toFixed(1)}%)`}>
      <div className="w-16 bg-gray-100 rounded-full h-1.5 overflow-hidden">
        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      <span className="font-mono text-[10px] w-14 text-right">{val.toLocaleString()}</span>
      {diff !== 0 && (
        <span className={`text-[9px] font-mono ${absDiffPct > 10 ? 'text-red-600 font-semibold' : absDiffPct > 3 ? 'text-amber-600' : 'text-gray-400'}`}>
          {diff > 0 ? '+' : ''}{diffPct.toFixed(1)}%
        </span>
      )}
    </div>
  )
}

function SourceStatusBadge({ status }) {
  const map = {
    available: { cls: 'bg-emerald-100 text-emerald-700', label: 'พร้อม' },
    live: { cls: 'bg-indigo-100 text-indigo-700', label: 'Live' },
    pending: { cls: 'bg-gray-100 text-gray-400', label: 'รอข้อมูล' },
  }
  const s = map[status] || map.pending
  return <span className={`text-[9px] px-1.5 py-0.5 rounded font-medium ${s.cls}`}>{s.label}</span>
}

function CrossReferencePanelInner({ allItems, review, anomalyFlags, anomalyMeta }) {
  const [expanded, setExpanded] = useState(true)
  const [crossRefData, setCrossRefData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [filterSeverity, setFilterSeverity] = useState('all')
  const [filterProvince, setFilterProvince] = useState('all')
  const [sortCol, setSortCol] = useState('default')
  const [sortAsc, setSortAsc] = useState(true)
  const [page, setPage] = useState(0)
  const [selectedRow, setSelectedRow] = useState(null)
  const [viewMode, setViewMode] = useState('table') // table | cards
  const PAGE_SIZE = 20

  // Load cross-reference JSON on expand
  useEffect(() => {
    if (expanded && !crossRefData && !loading) {
      setLoading(true)
      fetch(CROSS_REF_URL)
        .then(r => r.ok ? r.json() : null)
        .then(d => { setCrossRefData(d); setLoading(false) })
        .catch(() => setLoading(false))
    }
  }, [expanded, crossRefData, loading])

  // Build OCR aggregates per constituency
  // Filter to แบ่งเขต only — other sources (ECT/Killernay/Luengnat) report constituency data,
  // so including บัญชีรายชื่อ would double-count turnout/valid/invalid.
  const ocrByConst = useMemo(() => {
    const groups = {}
    allItems.forEach(item => {
      const vt = item.vote_type || ''
      if (vt && vt !== 'แบ่งเขต') return
      const key = `${item.province || '?'}_${item.constituency || '?'}`
      if (!groups[key]) groups[key] = { items: [], turnout: 0, valid: 0, invalid: 0, stations: new Set(), files: new Set(), errors: 0, warnings: 0, reviewed: 0, total: 0 }
      const g = groups[key]
      g.items.push(item)
      g.turnout += Number(item.turnout) || 0
      g.valid += Number(item.valid_ballots) || 0
      g.invalid += Number(item.invalid_ballots) || 0
      g.total++
      // Unique station = sub_district + station_no (station_no alone repeats across sub-districts)
      const stn = item.ocr_station_no || item.station_no
      const subDist = item.ocr_sub_district || item.sub_district || ''
      if (stn) g.stations.add(`${subDist}_${stn}`)
      if (item.file) g.files.add(item.file)
      const warns = validateItem(item)
      warns.forEach(w => { if (w.severity === 'error') g.errors++; else if (w.severity === 'warning') g.warnings++ })
      const st = (review[item.id] || {}).status || 'pending'
      if (st !== 'pending') g.reviewed++
    })
    // Convert stations Set to count
    Object.values(groups).forEach(g => { g.stationCount = g.stations.size; g.fileCount = g.files.size; delete g.stations; delete g.files })
    return groups
  }, [allItems, review])

  // Merge all sources
  const comparisonData = useMemo(() => {
    if (!crossRefData) return []
    const constituencies = crossRefData.constituencies || []
    return constituencies.map(c => {
      const ocr = ocrByConst[c.key] || null
      const ect = c.ect || null
      const kn = c.killernay || null
      const ln = c.luengnat || null

      // MAX = max(ECT.valid_votes, KN.valid_votes, LN.valid_votes)
      // Diff = |MAX − OCR.turnout| / MAX × 100
      const refVals = [
        ect?.valid_votes || 0,
        kn?.valid_votes || 0,
        ln?.valid_votes || 0,
      ]
      const refMax = Math.max(...refVals)
      const ocrVal = ocr?.turnout || 0
      const maxDiff = (ocr && refMax > 0) ? Math.abs(refMax - ocrVal) / refMax * 100 : 0

      // Severity based on OCR vs reference diff
      let severity = 'ok'
      if (ocr && refMax > 0) {
        if (maxDiff > 25) severity = 'error'
        else if (maxDiff > 10) severity = 'warning'
        else if (maxDiff > 3) severity = 'mismatch'
      }
      // OCR quality is tracked separately (not mixed into severity)
      const ocrQuality = !ocr ? null : ocr.errors > 0 ? 'error' : ocr.warnings > 0 ? 'warning' : 'ok'

      // Count available sources
      const sourceCount = (ocr ? 1 : 0) + (ect ? 1 : 0) + (kn ? 1 : 0) + (ln ? 1 : 0)

      return {
        key: c.key,
        province: c.province,
        zone: c.zone,
        ocr,
        ect,
        kn,
        ln,
        severity,
        ocrQuality,
        maxDiff: Math.round(maxDiff * 10) / 10,
        refMax,
        sourceCount,
        reviewPct: ocr ? (ocr.total > 0 ? ocr.reviewed / ocr.total * 100 : 0) : 0,
        sortPriority: c.sort_priority != null ? c.sort_priority : 1000,
        driveFolder: c.drive_folder || '',
      }
    })
  }, [crossRefData, ocrByConst])

  // Available provinces (from cross-ref data)
  const allProvinces = useMemo(() => {
    if (!crossRefData) return []
    const set = new Set()
    ;(crossRefData.constituencies || []).forEach(c => { if (c.province) set.add(c.province) })
    const ocrPrio = crossRefData.ocr_provinces || []
    const rest = [...set].filter(p => !ocrPrio.includes(p)).sort()
    return [...ocrPrio, ...rest]
  }, [crossRefData])

  // Filter
  const filtered = useMemo(() => {
    let data = comparisonData
    if (filterSeverity !== 'all') data = data.filter(d => d.severity === filterSeverity)
    if (filterProvince !== 'all') data = data.filter(d => d.province === filterProvince)
    return data
  }, [comparisonData, filterSeverity, filterProvince])

  // Sort
  const sorted = useMemo(() => {
    const arr = [...filtered]
    const sevOrder = { error: 3, warning: 2, mismatch: 1, ok: 0 }
    arr.sort((a, b) => {
      let va, vb
      switch (sortCol) {
        case 'default':
          // sort_priority first (OCR provinces 0,1,2 → top), then province name, then zone
          if (a.sortPriority !== b.sortPriority) return a.sortPriority - b.sortPriority
          if (a.province !== b.province) return a.province.localeCompare(b.province)
          return (Number(a.zone) || 0) - (Number(b.zone) || 0)
        case 'province': va = a.province; vb = b.province; return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va)
        case 'zone': va = Number(a.zone) || 0; vb = Number(b.zone) || 0; break
        case 'diff': va = a.maxDiff; vb = b.maxDiff; break
        case 'ocrTurnout': va = a.ocr?.turnout || 0; vb = b.ocr?.turnout || 0; break
        case 'sources': va = a.sourceCount; vb = b.sourceCount; break
        case 'reviewPct': va = a.reviewPct; vb = b.reviewPct; break
        case 'severity': va = sevOrder[a.severity] || 0; vb = sevOrder[b.severity] || 0; break
        default: return 0
      }
      return sortAsc ? va - vb : vb - va
    })
    return arr
  }, [filtered, sortCol, sortAsc])

  const paged = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
  const totalPages = Math.ceil(sorted.length / PAGE_SIZE)

  const summary = useMemo(() => ({
    total: comparisonData.length,
    errors: comparisonData.filter(d => d.severity === 'error').length,
    warnings: comparisonData.filter(d => d.severity === 'warning').length,
    mismatches: comparisonData.filter(d => d.severity === 'mismatch').length,
    ok: comparisonData.filter(d => d.severity === 'ok').length,
  }), [comparisonData])

  const toggleSort = (col) => {
    if (sortCol === col) setSortAsc(v => !v)
    else { setSortCol(col); setSortAsc(col === 'province') }
  }

  const SortTh = ({ col, align = 'left', children }) => {
    const active = sortCol === col
    return (
      <th className={`px-2 py-1.5 text-${align} cursor-pointer select-none hover:text-gray-700 transition`} onClick={() => toggleSort(col)}>
        <span className="inline-flex items-center gap-0.5">
          {children}
          {active ? (sortAsc ? <ArrowUp size={9} /> : <ArrowDown size={9} />) : <ArrowUpDown size={8} className="opacity-30" />}
        </span>
      </th>
    )
  }

  const fmtNum = (n) => n != null ? n.toLocaleString() : '—'
  const sources = crossRefData?.sources || {}

  if (allItems.length === 0) return null

  return (
    <div>
      <button
        onClick={() => setExpanded(v => !v)}
        className="w-full flex items-center gap-2.5 py-3 text-sm font-semibold text-gray-700 hover:text-indigo-700 transition group"
      >
        <span className="w-7 h-7 rounded-lg bg-violet-50 flex items-center justify-center group-hover:bg-violet-100 transition">
          <GitCompareArrows size={15} className="text-violet-500" />
        </span>
        Cross-Reference: 4 แหล่งข้อมูล
        {expanded ? <ChevronDown size={14} className="text-gray-400" /> : <ChevronRight size={14} className="text-gray-400" />}
        <span className="text-xs font-normal text-gray-400">
          {summary.total > 0 ? `${summary.total} เขต · ${summary.errors} errors · ${summary.warnings} warnings` : 'คลิกเพื่อโหลด'}
        </span>
      </button>

      {expanded && (
        <div className="p-5 space-y-4">
          {loading && <div className="text-center text-gray-400 py-8 animate-pulse">กำลังโหลดข้อมูล cross-reference...</div>}

          {!loading && crossRefData && (
            <>
              {/* Source status cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {Object.entries(SOURCE_COLORS).map(([key, sc]) => {
                  const src = sources[key] || {}
                  const count = key === 'ocr' ? Object.keys(ocrByConst).length : (src.records || 0)
                  return (
                    <div key={key} className={`rounded-lg border ${sc.border} ${sc.bg} p-3 text-center`}>
                      <div className="flex items-center justify-center gap-1 mb-1">
                        {(() => {
                          const linkUrl = sc.url || (key !== 'ocr' && crossRefData?.sources?.[key]?.url)
                          const content = <span className="text-sm font-medium">{sc.icon} {sc.label}</span>
                          return linkUrl ? <a href={linkUrl} target="_blank" rel="noopener noreferrer" className="hover:underline">{content}</a> : content
                        })()}
                        <SourceStatusBadge status={key === 'ocr' ? 'live' : (src.status || 'pending')} />
                      </div>
                      <div className={`text-lg font-bold ${sc.text}`}>{count.toLocaleString()}</div>
                      <div className="text-[10px] text-gray-500">เขตเลือกตั้ง</div>
                    </div>
                  )
                })}
              </div>

              {crossRefData.generated && (
                <div className="text-[10px] text-gray-400">
                  ข้อมูลอัปเดต: {new Date(crossRefData.generated).toLocaleString('th-TH')}
                  {anomalyMeta && <> · ECT flags: {anomalyMeta.total_flags || 0}</>}
                </div>
              )}

              {/* Filter + view mode */}
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2 flex-wrap">
                  {/* Province filter dropdown */}
                  <select
                    value={filterProvince}
                    onChange={e => { setFilterProvince(e.target.value); setPage(0) }}
                    className="px-2 py-1 rounded-lg text-[11px] font-medium bg-gray-50 text-gray-700 border border-gray-200 focus:ring-2 focus:ring-indigo-300 focus:outline-none"
                  >
                    <option value="all">ทุกจังหวัด ({allProvinces.length})</option>
                    {allProvinces.map(p => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                  {[
                    { label: 'ทั้งหมด', count: summary.total, cls: 'bg-gray-50 text-gray-700', filter: 'all', tip: 'แสดงทุกเขต' },
                    { label: 'Error', count: summary.errors, cls: 'bg-red-50 text-red-700', filter: 'error', tip: SEVERITY_CRITERIA.error },
                    { label: 'Warning', count: summary.warnings, cls: 'bg-amber-50 text-amber-700', filter: 'warning', tip: SEVERITY_CRITERIA.warning },
                    { label: 'Mismatch', count: summary.mismatches, cls: 'bg-orange-50 text-orange-700', filter: 'mismatch', tip: SEVERITY_CRITERIA.mismatch },
                    { label: 'OK', count: summary.ok, cls: 'bg-emerald-50 text-emerald-700', filter: 'ok', tip: SEVERITY_CRITERIA.ok },
                  ].map(s => (
                    <button
                      key={s.filter}
                      onClick={() => { setFilterSeverity(s.filter); setPage(0) }}
                      title={s.tip}
                      className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition ${
                        filterSeverity === s.filter ? s.cls + ' ring-2 ring-offset-1 ring-indigo-300' : 'bg-gray-50 text-gray-500 hover:bg-gray-100'
                      }`}
                    >
                      {s.label} ({s.count})
                    </button>
                  ))}
                </div>
                <div className="flex gap-1">
                  {['table', 'cards'].map(m => (
                    <button key={m} onClick={() => setViewMode(m)}
                      className={`px-2 py-1 text-[10px] rounded ${viewMode === m ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-50 text-gray-500 hover:bg-gray-100'}`}
                    >{m === 'table' ? '📋 ตาราง' : '🃏 การ์ด'}</button>
                  ))}
                </div>
              </div>

              {/* Table view */}
              {viewMode === 'table' && (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-[10px] text-gray-500 uppercase border-b border-gray-200 bg-gray-50">
                        <SortTh col="severity" align="center">สถานะ</SortTh>
                        <SortTh col="province" align="center">จังหวัด</SortTh>
                        <SortTh col="zone" align="center">เขต</SortTh>
                        <th className="px-2 py-1.5 text-center"><a href="https://github.com/narasakp/election-verification" target="_blank" rel="noopener noreferrer" className="hover:underline">🔬 OCR</a></th>
                        <th className="px-2 py-1.5 text-center"><a href={crossRefData?.sources?.ect?.url} target="_blank" rel="noopener noreferrer" className="hover:underline">🏛️ กกต.</a></th>
                        <th className="px-2 py-1.5 text-center"><a href={crossRefData?.sources?.killernay?.url} target="_blank" rel="noopener noreferrer" className="hover:underline">📊 KILLERNAY</a></th>
                        <th className="px-2 py-1.5 text-center"><a href={crossRefData?.sources?.luengnat?.url} target="_blank" rel="noopener noreferrer" className="hover:underline">📈 LUENGNAT</a></th>
                        <SortTh col="diff" align="center">Max Diff</SortTh>
                        <SortTh col="reviewPct" align="center">Review</SortTh>
                      </tr>
                    </thead>
                    <tbody>
                      {paged.map((row) => {
                        const maxTurnout = Math.max(row.ocr?.turnout || 0, row.ect?.turnout || 0, row.kn?.valid_votes || 0, row.ln?.valid_votes || 0, 1)
                        return (
                          <tr key={row.key}
                            className={`border-b border-gray-50 hover:bg-gray-50 transition cursor-pointer ${selectedRow === row.key ? 'bg-indigo-50' : ''}`}
                            onClick={() => setSelectedRow(selectedRow === row.key ? null : row.key)}
                          >
                            <td className="px-2 py-2 text-center"><SeverityBadge severity={row.severity} /></td>
                            <td className="px-2 py-2 text-center font-medium text-gray-700">{row.province}</td>
                            <td className="px-2 py-2 text-center">{row.zone}</td>
                            <td className="px-2 py-2 text-center">
                              {row.ocr ? (
                                <div className="font-mono text-[10px] flex items-center justify-center gap-1">
                                  {row.ocrQuality === 'error' && <span className="text-red-400" title={`OCR: ${row.ocr.errors} errors`}>⚠</span>}
                                  {row.ocrQuality === 'warning' && <span className="text-amber-400" title={`OCR: ${row.ocr.warnings} warnings`}>⚠</span>}
                                  <span className="text-indigo-600">{fmtNum(row.ocr.turnout)}</span>
                                  {row.driveFolder ? (
                                    <a href={row.driveFolder} target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-indigo-600 hover:underline" title={`${row.ocr.stationCount} หน่วย / ${row.ocr.fileCount} ไฟล์ · เปิดใน Drive`} onClick={e => e.stopPropagation()}>({row.ocr.fileCount} ไฟล์)</a>
                                  ) : (
                                    <span className="text-gray-400" title={`${row.ocr.stationCount} หน่วย / ${row.ocr.fileCount} ไฟล์`}>({row.ocr.fileCount} ไฟล์)</span>
                                  )}
                                </div>
                              ) : <span className="text-gray-300 text-[10px]">—</span>}
                            </td>
                            <td className="px-2 py-2 text-center">
                              {row.ect ? (
                                <div className="font-mono text-[10px]">
                                  <span className="text-blue-600">{fmtNum(row.ect.turnout)}</span>
                                  <span className="text-gray-400 ml-1">({row.ect.percent_count}%)</span>
                                </div>
                              ) : <span className="text-gray-300 text-[10px]">—</span>}
                            </td>
                            <td className="px-2 py-2 text-center">
                              {row.kn ? (
                                <div className="font-mono text-[10px]">
                                  <span className="text-emerald-600">{fmtNum(row.kn.valid_votes)}</span>
                                </div>
                              ) : <span className="text-gray-300 text-[10px]">—</span>}
                            </td>
                            <td className="px-2 py-2 text-center">
                              {row.ln ? (
                                <div className="font-mono text-[10px]">
                                  <span className="text-purple-600">{fmtNum(row.ln.valid_votes)}</span>
                                </div>
                              ) : <span className="text-gray-300 text-[10px]">—</span>}
                            </td>
                            <td className="px-2 py-2 text-center">
                              {row.ocr ? (
                                row.maxDiff > 0 ? (
                                  <span className={`font-mono text-[10px] px-1 py-0.5 rounded ${
                                    row.maxDiff > 25 ? 'bg-red-100 text-red-700 font-semibold' :
                                    row.maxDiff > 10 ? 'bg-amber-100 text-amber-700' :
                                    row.maxDiff > 3 ? 'bg-orange-100 text-orange-700' : 'text-gray-500'
                                  }`}>{row.maxDiff}%</span>
                                ) : <span className="text-gray-300 text-[10px]">—</span>
                              ) : <span className="text-gray-300 text-[10px]">—</span>}
                            </td>
                            <td className="px-2 py-2 text-center">
                              <div className="flex items-center justify-center gap-1">
                                <div className="w-12 bg-gray-100 rounded-full h-1.5 overflow-hidden">
                                  <div className={`h-full rounded-full ${row.reviewPct >= 100 ? 'bg-emerald-500' : row.reviewPct > 50 ? 'bg-indigo-400' : 'bg-amber-400'}`}
                                    style={{ width: `${row.reviewPct}%` }} />
                                </div>
                                <span className="text-[9px] text-gray-400 w-6 text-right">{row.reviewPct.toFixed(0)}%</span>
                              </div>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Cards view */}
              {viewMode === 'cards' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {paged.map(row => {
                    const maxTurnout = Math.max(row.ocr?.turnout || 0, row.ect?.turnout || 0, row.kn?.valid_votes || 0, row.ln?.valid_votes || 0, 1)
                    const maxValid = Math.max(row.ocr?.valid || 0, row.ect?.valid_votes || 0, row.kn?.valid_votes || 0, row.ln?.valid_votes || 0, 1)
                    return (
                      <div key={row.key} className={`rounded-lg border p-3 space-y-2 ${
                        row.severity === 'error' ? 'border-red-200 bg-red-50/30' :
                        row.severity === 'warning' ? 'border-amber-200 bg-amber-50/30' :
                        'border-gray-100'
                      }`}>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <SeverityBadge severity={row.severity} />
                            <span className="font-semibold text-sm">{row.province}</span>
                            <span className="text-xs text-gray-500">เขต {row.zone}</span>
                          </div>
                          {row.ocr && row.maxDiff > 0 && (
                            <span className={`text-[10px] font-mono ${row.maxDiff > 25 ? 'text-red-600' : row.maxDiff > 10 ? 'text-amber-600' : row.maxDiff > 3 ? 'text-orange-500' : 'text-gray-400'}`}>
                              Δ {row.maxDiff}%
                            </span>
                          )}
                        </div>
                        {/* Valid votes comparison bars */}
                        <div className="space-y-1">
                          <div className="text-[9px] text-gray-500 uppercase font-medium">คะแนนดี / ผู้มาใช้สิทธิ</div>
                          {row.ocr && <DiffBar val={row.ocr.turnout} refVal={row.kn?.valid_votes || row.ln?.valid_votes} maxVal={maxTurnout} color="bg-indigo-400" />}
                          {row.ect && <DiffBar val={row.ect.turnout} refVal={row.kn?.valid_votes || row.ln?.valid_votes} maxVal={maxTurnout} color="bg-blue-400" />}
                          {row.kn && <DiffBar val={row.kn.valid_votes} refVal={row.ln?.valid_votes || row.ect?.valid_votes} maxVal={maxTurnout} color="bg-emerald-400" />}
                          {row.ln && <DiffBar val={row.ln.valid_votes} refVal={row.kn?.valid_votes || row.ect?.valid_votes} maxVal={maxTurnout} color="bg-purple-400" />}
                        </div>
                        {/* Valid votes */}
                        <div className="space-y-1">
                          <div className="text-[9px] text-gray-500 uppercase font-medium">คะแนนดี (Valid)</div>
                          {row.ocr && <DiffBar val={row.ocr.valid} refVal={row.ect?.valid_votes || row.kn?.valid_votes} maxVal={maxValid} color="bg-indigo-400" />}
                          {row.ect && <DiffBar val={row.ect.valid_votes} refVal={row.kn?.valid_votes || row.ln?.valid_votes} maxVal={maxValid} color="bg-blue-400" />}
                          {row.kn && <DiffBar val={row.kn.valid_votes} refVal={row.ect?.valid_votes || row.ln?.valid_votes} maxVal={maxValid} color="bg-emerald-400" />}
                          {row.ln && <DiffBar val={row.ln.valid_votes} refVal={row.ect?.valid_votes || row.kn?.valid_votes} maxVal={maxValid} color="bg-purple-400" />}
                        </div>
                        {/* Source legend */}
                        <div className="flex items-center gap-3 text-[9px] text-gray-400 pt-1 border-t border-gray-100">
                          {row.ocr && <span>🔬 OCR ({row.ocr.stationCount} หน่วย · {row.ocr.fileCount} ไฟล์)</span>}
                          {row.ect && <span>🏛️ กกต. ({row.ect.percent_count}% นับ)</span>}
                          {row.kn && <span>📊 Killernay</span>}
                          {row.ln && <span>📈 Luengnat</span>}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}

              {/* Detail panel for selected row */}
              {selectedRow && viewMode === 'table' && (() => {
                const row = comparisonData.find(r => r.key === selectedRow)
                if (!row) return null
                const maxTurnout = Math.max(row.ocr?.turnout || 0, row.ect?.turnout || 0, row.kn?.valid_votes || 0, row.ln?.valid_votes || 0, 1)
                const maxValid = Math.max(row.ocr?.valid || 0, row.ect?.valid_votes || 0, row.kn?.valid_votes || 0, row.ln?.valid_votes || 0, 1)
                return (
                  <div className="bg-gray-50 rounded-lg border border-gray-200 p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-semibold">{row.province} เขต {row.zone} — เปรียบเทียบ 4 แหล่ง</h4>
                      <button onClick={() => setSelectedRow(null)} className="text-gray-400 hover:text-gray-600 text-xs">✕ ปิด</button>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Turnout / Valid votes comparison */}
                      <div className="space-y-1.5">
                        <div className="text-[10px] text-gray-500 uppercase font-semibold">คะแนนดี / ผู้มาใช้สิทธิ</div>
                        {[
                          { key: 'ocr', icon: '🔬', label: 'OCR', val: row.ocr?.turnout, color: 'bg-indigo-500' },
                          { key: 'ect', icon: '🏛️', label: 'กกต.', val: row.ect?.turnout, color: 'bg-blue-500' },
                          { key: 'kn', icon: '📊', label: 'Killernay', val: row.kn?.valid_votes, color: 'bg-emerald-500' },
                          { key: 'ln', icon: '📈', label: 'Luengnat', val: row.ln?.valid_votes, color: 'bg-purple-500' },
                        ].map(s => (
                          <div key={s.key} className="flex items-center gap-2">
                            <span className="w-20 text-[10px] text-gray-600">{s.icon} {s.label}</span>
                            {s.val != null ? (
                              <>
                                <div className="flex-1 bg-gray-200 rounded-full h-2 overflow-hidden">
                                  <div className={`h-full rounded-full ${s.color}`} style={{ width: `${(s.val / maxTurnout) * 100}%` }} />
                                </div>
                                <span className="font-mono text-[10px] w-16 text-right">{s.val.toLocaleString()}</span>
                              </>
                            ) : <span className="text-[10px] text-gray-300 italic">ไม่มีข้อมูล</span>}
                          </div>
                        ))}
                      </div>
                      {/* Valid votes comparison */}
                      <div className="space-y-1.5">
                        <div className="text-[10px] text-gray-500 uppercase font-semibold">คะแนนดี (Valid Votes)</div>
                        {[
                          { key: 'ocr', icon: '🔬', label: 'OCR', val: row.ocr?.valid, color: 'bg-indigo-500' },
                          { key: 'ect', icon: '🏛️', label: 'กกต.', val: row.ect?.valid_votes, color: 'bg-blue-500' },
                          { key: 'kn', icon: '📊', label: 'Killernay', val: row.kn?.valid_votes, color: 'bg-emerald-500' },
                          { key: 'ln', icon: '📈', label: 'Luengnat', val: row.ln?.valid_votes, color: 'bg-purple-500' },
                        ].map(s => (
                          <div key={s.key} className="flex items-center gap-2">
                            <span className="w-20 text-[10px] text-gray-600">{s.icon} {s.label}</span>
                            {s.val != null ? (
                              <>
                                <div className="flex-1 bg-gray-200 rounded-full h-2 overflow-hidden">
                                  <div className={`h-full rounded-full ${s.color}`} style={{ width: `${(s.val / maxValid) * 100}%` }} />
                                </div>
                                <span className="font-mono text-[10px] w-16 text-right">{s.val.toLocaleString()}</span>
                              </>
                            ) : <span className="text-[10px] text-gray-300 italic">ไม่มีข้อมูล</span>}
                          </div>
                        ))}
                      </div>
                    </div>
                    {/* Winner info from Killernay */}
                    {row.kn?.winner && (
                      <div className="text-[10px] text-gray-600 bg-white rounded p-2 border border-gray-100">
                        📊 <strong>Killernay ผู้ชนะ:</strong> {row.kn.winner} ({row.kn.winner_party}) — {row.kn.winner_votes?.toLocaleString()} คะแนน
                        {row.kn.registered && <> · ผู้มีสิทธิ {row.kn.registered.toLocaleString()}</>}
                      </div>
                    )}
                    {/* Luengnat info */}
                    {row.ln && (
                      <div className="text-[10px] text-gray-600 bg-white rounded p-2 border border-gray-100">
                        📈 <strong>Luengnat:</strong> คะแนนดี {row.ln.valid_votes?.toLocaleString()}
                        {row.ln.ocr_exact ? <span className="text-emerald-600 ml-1">✓ OCR exact</span> : row.ln.ocr_delta != null && <span className="text-amber-600 ml-1">Δ {row.ln.ocr_delta?.toLocaleString()}</span>}
                        {row.ln.drive_url && <a href={row.ln.drive_url} target="_blank" rel="noopener noreferrer" className="text-purple-600 hover:underline ml-2 inline-flex items-center gap-0.5"><ExternalLink size={9} /> ดูเอกสาร</a>}
                      </div>
                    )}
                    {/* OCR summary */}
                    {row.ocr && (
                      <div className="text-[10px] text-gray-600 bg-white rounded p-2 border border-gray-100">
                        🔬 <strong>OCR:</strong> {row.ocr.stationCount} หน่วย · {row.ocr.fileCount} ไฟล์ · ตรวจแล้ว {row.ocr.reviewed}/{row.ocr.total}
                        {(row.ocr.errors > 0 || row.ocr.warnings > 0) && <> · <span className="text-red-500">{row.ocr.errors} errors</span>, <span className="text-amber-500">{row.ocr.warnings} warnings</span></>}
                        {row.refMax > 0 && <>
                          <br />📐 <strong>Diff:</strong> |{row.refMax.toLocaleString()} − {row.ocr.turnout.toLocaleString()}| / {row.refMax.toLocaleString()} = <strong>{row.maxDiff}%</strong>
                        </>}
                      </div>
                    )}
                  </div>
                )
              })()}

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>แสดง {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, sorted.length)} จาก {sorted.length}</span>
                  <div className="flex gap-1">
                    <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}
                      className="px-2 py-1 bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-30">← ก่อนหน้า</button>
                    <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1}
                      className="px-2 py-1 bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-30">ถัดไป →</button>
                  </div>
                </div>
              )}
            </>
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
