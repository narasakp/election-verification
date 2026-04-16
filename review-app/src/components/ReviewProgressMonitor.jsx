import React, { useState, useMemo } from 'react'
import { BarChart3, ChevronDown, ChevronRight, User, FileText, CheckCircle2, Clock, AlertCircle, Search, Download, Filter } from 'lucide-react'
import ErrorBoundary from './ErrorBoundary'

/**
 * Review Progress Monitor — Admin tool to track hired reviewer progress.
 *
 * Shows:
 *  1. Overall progress bar (reviewed/total)
 *  2. Per-province / per-constituency breakdown
 *  3. Per-reviewer: which pages done, which remaining
 *  4. Remaining (unreviewed) item list
 *  5. Export progress report
 */

const STATUS_COLORS = {
  confirmed: { bg: 'bg-emerald-500', text: 'text-emerald-700', light: 'bg-emerald-50', label: 'ยืนยัน' },
  flagged: { bg: 'bg-amber-500', text: 'text-amber-700', light: 'bg-amber-50', label: 'ตรวจซ้ำ' },
  rejected: { bg: 'bg-red-500', text: 'text-red-700', light: 'bg-red-50', label: 'ใช้ไม่ได้' },
  pending: { bg: 'bg-gray-300', text: 'text-gray-500', light: 'bg-gray-50', label: 'รอตรวจ' },
}

function ProgressBar({ reviewed, total, height = 'h-3' }) {
  const pct = total > 0 ? (reviewed / total * 100) : 0
  return (
    <div className={`w-full ${height} bg-gray-200 rounded-full overflow-hidden`}>
      <div
        className={`${height} rounded-full transition-all duration-500 ${pct >= 100 ? 'bg-emerald-500' : pct >= 50 ? 'bg-blue-500' : 'bg-amber-500'}`}
        style={{ width: `${Math.min(100, pct)}%` }}
      />
    </div>
  )
}

function StatusBreakdownBar({ statusCounts, total }) {
  if (total === 0) return null
  const order = ['confirmed', 'flagged', 'rejected', 'pending']
  return (
    <div className="w-full h-2.5 bg-gray-200 rounded-full overflow-hidden flex">
      {order.map(st => {
        const count = statusCounts[st] || 0
        if (count === 0) return null
        return (
          <div
            key={st}
            className={`${STATUS_COLORS[st].bg} transition-all duration-500`}
            style={{ width: `${(count / total * 100)}%` }}
            title={`${STATUS_COLORS[st].label}: ${count}`}
          />
        )
      })}
    </div>
  )
}

const VOTE_TYPE_OPTIONS = [
  { key: 'แบ่งเขต', label: '🗳️ แบ่งเขต', cls: 'bg-blue-600 text-white', inactiveCls: 'bg-blue-50 text-blue-700 border-blue-200' },
  { key: 'บัญชีรายชื่อ', label: '📝 บัญชีรายชื่อ', cls: 'bg-purple-600 text-white', inactiveCls: 'bg-purple-50 text-purple-700 border-purple-200' },
  { key: 'ประชามติ', label: '🗳️ ประชามติ', cls: 'bg-teal-600 text-white', inactiveCls: 'bg-teal-50 text-teal-700 border-teal-200' },
  { key: 'all', label: '📋 ทั้งหมด', cls: 'bg-gray-700 text-white', inactiveCls: 'bg-gray-100 text-gray-600 border-gray-300' },
]

function ReviewProgressMonitorInner({ allItems, review, reviewLog }) {
  const [viewMode, setViewMode] = useState('overview') // overview | reviewer | remaining
  const [expandedGroups, setExpandedGroups] = useState({})
  const [searchText, setSearchText] = useState('')
  const [selectedReviewer, setSelectedReviewer] = useState(null)
  const [monitorVoteType, setMonitorVoteType] = useState('แบ่งเขต')

  const toggleGroup = (key) => setExpandedGroups(prev => ({ ...prev, [key]: !prev[key] }))

  // ── Vote type counts (from all items, unfiltered) ──
  const voteTypeCounts = useMemo(() => {
    const counts = {}
    allItems.forEach(item => {
      const vt = item.vote_type || 'ไม่ระบุ'
      counts[vt] = (counts[vt] || 0) + 1
    })
    return counts
  }, [allItems])

  // ── Filter items by vote type ──
  const monitorItems = useMemo(() => {
    if (monitorVoteType === 'all') return allItems
    return allItems.filter(item => (item.vote_type || 'ไม่ระบุ') === monitorVoteType)
  }, [allItems, monitorVoteType])

  // ── Set of filtered item IDs for reviewer filtering ──
  const monitorItemIds = useMemo(() => new Set(monitorItems.map(i => i.id)), [monitorItems])

  // ── Core computed data ──

  // Per-item status map (all items, for lookups)
  const itemStatusMap = useMemo(() => {
    const map = {}
    allItems.forEach(item => {
      const rev = review[item.id] || {}
      map[item.id] = rev.status || 'pending'
    })
    return map
  }, [allItems, review])

  // Overall stats (filtered by vote type)
  const overallStats = useMemo(() => {
    const total = monitorItems.length
    let confirmed = 0, flagged = 0, rejected = 0, pending = 0
    monitorItems.forEach(item => {
      const st = itemStatusMap[item.id]
      if (st === 'confirmed') confirmed++
      else if (st === 'flagged') flagged++
      else if (st === 'rejected') rejected++
      else pending++
    })
    const reviewed = confirmed + flagged + rejected
    return { total, reviewed, confirmed, flagged, rejected, pending }
  }, [monitorItems, itemStatusMap])

  // Per-province → per-constituency breakdown (filtered by vote type)
  const provinceBreakdown = useMemo(() => {
    const map = {} // province → { total, reviewed, constituencies: { con → { total, reviewed, statusCounts, items } } }
    monitorItems.forEach(item => {
      const prov = item.province || 'ไม่ระบุ'
      const con = item.constituency || '?'
      const vt = item.vote_type || 'ไม่ระบุ'
      if (!map[prov]) map[prov] = { total: 0, reviewed: 0, statusCounts: {}, constituencies: {} }
      if (!map[prov].constituencies[con]) map[prov].constituencies[con] = { total: 0, reviewed: 0, statusCounts: {}, voteTypes: {} }
      if (!map[prov].constituencies[con].voteTypes[vt]) map[prov].constituencies[con].voteTypes[vt] = { total: 0, reviewed: 0, statusCounts: {} }

      const st = itemStatusMap[item.id]
      const isReviewed = st !== 'pending'

      map[prov].total++
      map[prov].statusCounts[st] = (map[prov].statusCounts[st] || 0) + 1
      if (isReviewed) map[prov].reviewed++

      map[prov].constituencies[con].total++
      map[prov].constituencies[con].statusCounts[st] = (map[prov].constituencies[con].statusCounts[st] || 0) + 1
      if (isReviewed) map[prov].constituencies[con].reviewed++

      map[prov].constituencies[con].voteTypes[vt].total++
      map[prov].constituencies[con].voteTypes[vt].statusCounts[st] = (map[prov].constituencies[con].voteTypes[vt].statusCounts[st] || 0) + 1
      if (isReviewed) map[prov].constituencies[con].voteTypes[vt].reviewed++
    })
    return Object.entries(map).sort((a, b) => a[0].localeCompare(b[0], 'th'))
  }, [monitorItems, itemStatusMap])

  // Per-reviewer: which items each reviewer has reviewed (filtered by vote type)
  const reviewerBreakdown = useMemo(() => {
    if (!reviewLog || reviewLog.length === 0) return []
    const map = {} // email → { name, items: Set<itemId>, statusCounts, timestamps }
    reviewLog.forEach(entry => {
      if (entry.status === 'pending') return // skip resets
      if (!monitorItemIds.has(entry.itemId)) return // skip items not in current vote type
      const email = entry.email || 'anonymous'
      if (!map[email]) map[email] = { email, name: entry.name || email.split('@')[0], items: new Set(), statusCounts: {}, first: null, last: null }
      const r = map[email]
      r.items.add(entry.itemId)
      r.statusCounts[entry.status] = (r.statusCounts[entry.status] || 0) + 1
      if (!r.first || entry.timestamp < r.first) r.first = entry.timestamp
      if (!r.last || entry.timestamp > r.last) r.last = entry.timestamp
    })
    return Object.values(map)
      .map(r => ({ ...r, itemCount: r.items.size, itemIds: [...r.items] }))
      .filter(r => r.itemCount > 0)
      .sort((a, b) => b.itemCount - a.itemCount)
  }, [reviewLog, monitorItemIds])

  // Remaining (unreviewed) items (filtered by vote type)
  const remainingItems = useMemo(() => {
    return monitorItems
      .filter(item => itemStatusMap[item.id] === 'pending')
      .filter(item => {
        if (!searchText) return true
        const hay = `${item.file || ''} ${item.province || ''} ${item.district || ''} ${item.sub_district || ''}`.toLowerCase()
        return hay.includes(searchText.toLowerCase())
      })
  }, [monitorItems, itemStatusMap, searchText])

  // Items reviewed by selected reviewer
  const selectedReviewerItems = useMemo(() => {
    if (!selectedReviewer) return []
    const r = reviewerBreakdown.find(r => r.email === selectedReviewer)
    if (!r) return []
    return monitorItems.filter(item => r.itemIds.includes(item.id)).map(item => ({
      ...item,
      reviewStatus: itemStatusMap[item.id]
    }))
  }, [selectedReviewer, reviewerBreakdown, monitorItems, itemStatusMap])

  // Export progress report
  const exportReport = () => {
    const report = {
      generated_at: new Date().toISOString(),
      vote_type_filter: monitorVoteType,
      overall: overallStats,
      by_province: provinceBreakdown.map(([prov, data]) => ({
        province: prov,
        total: data.total,
        reviewed: data.reviewed,
        percent: data.total > 0 ? Math.round(data.reviewed / data.total * 100 * 10) / 10 : 0,
        status_counts: data.statusCounts,
        constituencies: Object.entries(data.constituencies).map(([con, cData]) => ({
          constituency: con,
          total: cData.total,
          reviewed: cData.reviewed,
          percent: cData.total > 0 ? Math.round(cData.reviewed / cData.total * 100 * 10) / 10 : 0,
          status_counts: cData.statusCounts,
        }))
      })),
      by_reviewer: reviewerBreakdown.map(r => ({
        email: r.email,
        name: r.name,
        items_reviewed: r.itemCount,
        status_counts: r.statusCounts,
        first_review: r.first,
        last_review: r.last,
      })),
      remaining_count: remainingItems.length,
      remaining_items: remainingItems.slice(0, 500).map(item => ({
        id: item.id,
        province: item.province,
        constituency: item.constituency,
        vote_type: item.vote_type,
        file: item.file,
      })),
    }
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `review_progress_${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart3 size={20} className="text-indigo-600" />
          <h2 className="text-lg font-bold text-gray-800">ติดตามความคืบหน้า</h2>
        </div>
        <button
          onClick={exportReport}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-100 text-indigo-700 rounded-lg text-xs hover:bg-indigo-200 transition font-medium"
        >
          <Download size={13} /> Export รายงาน
        </button>
      </div>

      {/* ── Vote Type Filter ── */}
      <div className="flex items-center gap-2 flex-wrap">
        <Filter size={14} className="text-gray-400" />
        <span className="text-xs text-gray-500 font-semibold">ประเภท:</span>
        {VOTE_TYPE_OPTIONS.map(opt => {
          const count = opt.key === 'all'
            ? allItems.length
            : (voteTypeCounts[opt.key] || 0)
          if (opt.key !== 'all' && count === 0) return null
          const isActive = monitorVoteType === opt.key
          return (
            <button
              key={opt.key}
              onClick={() => setMonitorVoteType(opt.key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all border ${
                isActive ? opt.cls : opt.inactiveCls
              }`}
            >
              {opt.label}
              <span className={`px-1.5 py-0 rounded text-[10px] font-bold ${isActive ? 'bg-white/25' : 'bg-black/8'}`}>
                {count.toLocaleString()}
              </span>
            </button>
          )
        })}
      </div>

      {/* ── Overall Progress ── */}
      <div className="bg-white rounded-xl border shadow-sm p-5">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-semibold text-gray-700">ความคืบหน้ารวม</span>
          <span className="text-2xl font-bold text-indigo-700">
            {overallStats.total > 0 ? (overallStats.reviewed / overallStats.total * 100).toFixed(1) : 0}%
          </span>
        </div>
        <ProgressBar reviewed={overallStats.reviewed} total={overallStats.total} height="h-4" />
        <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
          <span>ตรวจแล้ว {overallStats.reviewed.toLocaleString()} / {overallStats.total.toLocaleString()} หน้า</span>
          <span>เหลือ {overallStats.pending.toLocaleString()} หน้า</span>
        </div>
        <div className="grid grid-cols-4 gap-3 mt-4">
          {Object.entries(STATUS_COLORS).map(([st, c]) => (
            <div key={st} className={`${c.light} rounded-lg p-3 text-center`}>
              <div className={`text-xl font-bold ${c.text}`}>{(overallStats[st] || 0).toLocaleString()}</div>
              <div className={`text-[10px] ${c.text}`}>{c.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── View Mode Tabs ── */}
      <div className="flex gap-2 border-b pb-1">
        {[
          { key: 'overview', label: 'ภาพรวมรายจังหวัด', icon: BarChart3 },
          { key: 'reviewer', label: 'รายผู้ตรวจ', icon: User },
          { key: 'remaining', label: `รอตรวจ (${overallStats.pending.toLocaleString()})`, icon: Clock },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => { setViewMode(tab.key); setSelectedReviewer(null) }}
            className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-t-lg transition ${
              viewMode === tab.key
                ? 'bg-indigo-100 text-indigo-700 border-b-2 border-indigo-500'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
            }`}
          >
            <tab.icon size={14} /> {tab.label}
          </button>
        ))}
      </div>

      {/* ── Tab: Overview ── */}
      {viewMode === 'overview' && (
        <div className="space-y-3">
          {provinceBreakdown.map(([prov, data]) => {
            const provKey = `prov_${prov}`
            const isExpanded = expandedGroups[provKey]
            const pct = data.total > 0 ? (data.reviewed / data.total * 100).toFixed(1) : 0
            const conEntries = Object.entries(data.constituencies).sort((a, b) => Number(a[0]) - Number(b[0]))

            return (
              <div key={prov} className="bg-white rounded-xl border shadow-sm overflow-hidden">
                <button
                  onClick={() => toggleGroup(provKey)}
                  className="w-full flex items-center gap-3 px-5 py-4 hover:bg-gray-50 transition text-left"
                >
                  {isExpanded ? <ChevronDown size={16} className="text-gray-400" /> : <ChevronRight size={16} className="text-gray-400" />}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-gray-800">{prov}</span>
                      <span className="text-sm font-bold text-indigo-700">{pct}%</span>
                    </div>
                    <div className="mt-1.5">
                      <StatusBreakdownBar statusCounts={data.statusCounts} total={data.total} />
                    </div>
                    <div className="flex gap-3 mt-1.5 text-[10px] text-gray-500">
                      <span>{data.reviewed}/{data.total} หน้า</span>
                      <span>{conEntries.length} เขต</span>
                      {data.statusCounts.confirmed > 0 && <span className="text-emerald-600">✅ {data.statusCounts.confirmed}</span>}
                      {data.statusCounts.flagged > 0 && <span className="text-amber-600">🔄 {data.statusCounts.flagged}</span>}
                      {data.statusCounts.rejected > 0 && <span className="text-red-600">🚫 {data.statusCounts.rejected}</span>}
                    </div>
                  </div>
                </button>

                {isExpanded && (
                  <div className="border-t bg-gray-50/50">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-[10px] text-gray-500 uppercase border-b bg-gray-100">
                          <th className="px-4 py-2 text-left">เขต</th>
                          <th className="px-2 py-2 text-center">ทั้งหมด</th>
                          <th className="px-2 py-2 text-center">ตรวจแล้ว</th>
                          <th className="px-2 py-2 text-center">เหลือ</th>
                          <th className="px-4 py-2 text-left w-48">ความคืบหน้า</th>
                          <th className="px-2 py-2 text-center">%</th>
                        </tr>
                      </thead>
                      <tbody>
                        {conEntries.map(([con, cData]) => {
                          const cPct = cData.total > 0 ? (cData.reviewed / cData.total * 100).toFixed(1) : 0
                          const remaining = cData.total - cData.reviewed
                          const vtEntries = Object.entries(cData.voteTypes)
                          const conKey = `${provKey}_con${con}`
                          const conExpanded = expandedGroups[conKey]

                          return (
                            <React.Fragment key={con}>
                              <tr
                                className={`border-b border-gray-100 hover:bg-white/80 transition cursor-pointer ${Number(cPct) >= 100 ? 'bg-emerald-50/30' : ''}`}
                                onClick={() => vtEntries.length > 1 && toggleGroup(conKey)}
                              >
                                <td className="px-4 py-2.5 font-medium text-gray-700">
                                  <span className="flex items-center gap-1">
                                    {vtEntries.length > 1 && (conExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />)}
                                    เขต {con}
                                  </span>
                                </td>
                                <td className="px-2 py-2.5 text-center font-mono">{cData.total}</td>
                                <td className="px-2 py-2.5 text-center font-mono text-emerald-700 font-medium">{cData.reviewed}</td>
                                <td className="px-2 py-2.5 text-center font-mono">
                                  {remaining > 0 ? <span className="text-amber-600">{remaining}</span> : <span className="text-emerald-500">✓</span>}
                                </td>
                                <td className="px-4 py-2.5">
                                  <StatusBreakdownBar statusCounts={cData.statusCounts} total={cData.total} />
                                </td>
                                <td className={`px-2 py-2.5 text-center font-bold ${Number(cPct) >= 100 ? 'text-emerald-600' : Number(cPct) >= 50 ? 'text-blue-600' : 'text-gray-500'}`}>
                                  {cPct}%
                                </td>
                              </tr>
                              {conExpanded && vtEntries.map(([vt, vtData]) => {
                                const vtPct = vtData.total > 0 ? (vtData.reviewed / vtData.total * 100).toFixed(0) : 0
                                return (
                                  <tr key={`${con}_${vt}`} className="border-b border-gray-50 bg-white/50">
                                    <td className="pl-10 pr-4 py-1.5 text-gray-500">└ {vt}</td>
                                    <td className="px-2 py-1.5 text-center font-mono text-[10px]">{vtData.total}</td>
                                    <td className="px-2 py-1.5 text-center font-mono text-[10px] text-emerald-600">{vtData.reviewed}</td>
                                    <td className="px-2 py-1.5 text-center font-mono text-[10px]">{vtData.total - vtData.reviewed || '✓'}</td>
                                    <td className="px-4 py-1.5">
                                      <StatusBreakdownBar statusCounts={vtData.statusCounts} total={vtData.total} />
                                    </td>
                                    <td className="px-2 py-1.5 text-center text-[10px]">{vtPct}%</td>
                                  </tr>
                                )
                              })}
                            </React.Fragment>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* ── Tab: Per-Reviewer ── */}
      {viewMode === 'reviewer' && !selectedReviewer && (
        <div className="space-y-3">
          {reviewerBreakdown.length === 0 ? (
            <div className="bg-white rounded-xl border p-8 text-center text-gray-400">
              <User size={32} className="mx-auto mb-2 text-gray-200" />
              <div>ยังไม่มีข้อมูลผู้ตรวจ</div>
            </div>
          ) : reviewerBreakdown.map(r => {
            const pctOfTotal = overallStats.total > 0 ? (r.itemCount / overallStats.total * 100).toFixed(1) : 0
            return (
              <button
                key={r.email}
                onClick={() => setSelectedReviewer(r.email)}
                className="w-full bg-white rounded-xl border shadow-sm p-4 hover:border-indigo-300 hover:shadow-md transition text-left"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-gray-800">{r.name}</div>
                    <div className="text-[10px] text-gray-400">{r.email}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-xl font-bold text-indigo-700">{r.itemCount}</div>
                    <div className="text-[10px] text-gray-500">หน้า ({pctOfTotal}%)</div>
                  </div>
                </div>
                <div className="mt-3">
                  <ProgressBar reviewed={r.itemCount} total={overallStats.total} height="h-2" />
                </div>
                <div className="flex gap-3 mt-2 text-[10px] text-gray-500">
                  {r.statusCounts.confirmed && <span className="text-emerald-600">✅ {r.statusCounts.confirmed}</span>}
                  {r.statusCounts.flagged && <span className="text-amber-600">🔄 {r.statusCounts.flagged}</span>}
                  {r.statusCounts.rejected && <span className="text-red-600">🚫 {r.statusCounts.rejected}</span>}
                  {r.first && <span className="ml-auto">เริ่ม {new Date(r.first).toLocaleDateString('th-TH')}</span>}
                  {r.last && <span>→ ล่าสุด {new Date(r.last).toLocaleString('th-TH')}</span>}
                </div>
              </button>
            )
          })}
        </div>
      )}

      {/* ── Reviewer Detail ── */}
      {viewMode === 'reviewer' && selectedReviewer && (
        <div className="space-y-3">
          <button
            onClick={() => setSelectedReviewer(null)}
            className="text-sm text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
          >
            ← กลับรายชื่อผู้ตรวจ
          </button>
          <div className="bg-white rounded-xl border shadow-sm p-4">
            <div className="font-semibold text-gray-800 mb-1">
              {reviewerBreakdown.find(r => r.email === selectedReviewer)?.name || selectedReviewer}
            </div>
            <div className="text-xs text-gray-400 mb-3">{selectedReviewer}</div>
            <div className="text-sm text-gray-600 mb-3">
              ตรวจแล้ว <b>{selectedReviewerItems.length}</b> หน้า
            </div>
            <div className="max-h-[60vh] overflow-y-auto">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-gray-100">
                  <tr>
                    <th className="text-left px-3 py-2">ไฟล์</th>
                    <th className="text-center px-2 py-2">จังหวัด</th>
                    <th className="text-center px-2 py-2">เขต</th>
                    <th className="text-center px-2 py-2">ประเภท</th>
                    <th className="text-center px-2 py-2">สถานะ</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedReviewerItems.map(item => {
                    const stColor = STATUS_COLORS[item.reviewStatus] || STATUS_COLORS.pending
                    return (
                      <tr key={item.id} className="border-t hover:bg-gray-50">
                        <td className="px-3 py-2 font-mono text-[10px] truncate max-w-[200px]" title={item.file}>{item.file || item.id}</td>
                        <td className="px-2 py-2 text-center">{item.province}</td>
                        <td className="px-2 py-2 text-center">{item.constituency}</td>
                        <td className="px-2 py-2 text-center">{item.vote_type || '—'}</td>
                        <td className="px-2 py-2 text-center">
                          <span className={`${stColor.light} ${stColor.text} px-2 py-0.5 rounded text-[10px] font-medium`}>
                            {stColor.label}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab: Remaining ── */}
      {viewMode === 'remaining' && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={searchText}
                onChange={e => setSearchText(e.target.value)}
                placeholder="ค้นหาไฟล์ จังหวัด อำเภอ..."
                className="w-full pl-9 pr-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400 outline-none"
              />
            </div>
            <span className="text-xs text-gray-500 whitespace-nowrap">
              {remainingItems.length.toLocaleString()} รายการ
            </span>
          </div>

          {remainingItems.length === 0 ? (
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-8 text-center">
              <CheckCircle2 size={40} className="mx-auto mb-2 text-emerald-500" />
              <div className="text-emerald-700 font-semibold">ตรวจครบทุกหน้าแล้ว! 🎉</div>
            </div>
          ) : (
            <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
              <div className="max-h-[60vh] overflow-y-auto">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-gray-100">
                    <tr>
                      <th className="text-left px-3 py-2 w-8">#</th>
                      <th className="text-left px-3 py-2">ไฟล์</th>
                      <th className="text-center px-2 py-2">จังหวัด</th>
                      <th className="text-center px-2 py-2">เขต</th>
                      <th className="text-center px-2 py-2">ประเภท</th>
                      <th className="text-center px-2 py-2">หน่วย</th>
                    </tr>
                  </thead>
                  <tbody>
                    {remainingItems.slice(0, 500).map((item, idx) => (
                      <tr key={item.id} className={`border-t ${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'} hover:bg-amber-50 transition`}>
                        <td className="px-3 py-2 text-gray-400 font-mono">{idx + 1}</td>
                        <td className="px-3 py-2 font-mono text-[10px] truncate max-w-[250px]" title={item.file}>{item.file || item.id}</td>
                        <td className="px-2 py-2 text-center">{item.province}</td>
                        <td className="px-2 py-2 text-center">{item.constituency}</td>
                        <td className="px-2 py-2 text-center">{item.vote_type || '—'}</td>
                        <td className="px-2 py-2 text-center font-mono">{item.ocr_station_no || item.station_no || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {remainingItems.length > 500 && (
                  <div className="text-center text-xs text-gray-400 py-2">แสดง 500 / {remainingItems.length.toLocaleString()} รายการ — ใช้ Export เพื่อดูทั้งหมด</div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function ReviewProgressMonitor(props) {
  return (
    <ErrorBoundary compact>
      <ReviewProgressMonitorInner {...props} />
    </ErrorBoundary>
  )
}
