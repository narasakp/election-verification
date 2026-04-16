import React, { useState, useMemo, useEffect, useCallback } from 'react'
import { Users, ChevronDown, ChevronRight, Trophy, Clock, AlertTriangle, CheckCircle2, Zap, ArrowLeft, RefreshCw, Cloud, CloudOff, Wifi } from 'lucide-react'
import ErrorBoundary from './ErrorBoundary'
import { fetchRemoteReviews, mergeLocalAndRemote } from '../utils/fetchRemoteReviews'

function Medal({ rank }) {
  if (rank === 1) return <span className="text-amber-400">🥇</span>
  if (rank === 2) return <span className="text-gray-400">🥈</span>
  if (rank === 3) return <span className="text-amber-700">🥉</span>
  return <span className="text-gray-300 text-xs font-mono w-5 text-center inline-block">{rank}</span>
}

function ReviewerLeaderboardInner({ reviewLog, allItems, review }) {
  const [expanded, setExpanded] = useState(true)
  const [sortBy, setSortBy] = useState('reviews')
  const [selectedReviewer, setSelectedReviewer] = useState(null) // { email, filterStatus }

  // Remote sync state
  const [remoteEntries, setRemoteEntries] = useState([])
  const [syncStatus, setSyncStatus] = useState('idle') // idle | loading | success | error
  const [syncError, setSyncError] = useState(null)
  const [syncInfo, setSyncInfo] = useState(null) // { fetchedAt, fromCache, addedCount }

  const doSync = useCallback(async (force = false) => {
    setSyncStatus('loading')
    setSyncError(null)
    try {
      const result = await fetchRemoteReviews(force)
      if (result.error) {
        setSyncStatus('error')
        setSyncError(result.error)
        return
      }
      setRemoteEntries(result.entries)
      setSyncStatus('success')
      setSyncInfo({ fetchedAt: result.fetchedAt, fromCache: result.fromCache, count: result.entries.length })
    } catch (err) {
      setSyncStatus('error')
      setSyncError(err.message)
    }
  }, [])

  // Auto-fetch on mount
  useEffect(() => { doSync(false) }, [doSync])

  // Combine local + remote logs for display
  const combinedLog = useMemo(() => {
    if (remoteEntries.length === 0) return reviewLog || []
    const { merged } = mergeLocalAndRemote(reviewLog || [], remoteEntries)
    return merged
  }, [reviewLog, remoteEntries])

  const itemMap = useMemo(() => {
    const m = {}; allItems.forEach(item => { m[item.id] = item }); return m
  }, [allItems])

  const itemStatusMap = useMemo(() => {
    const m = {}; allItems.forEach(item => { m[item.id] = (review[item.id] || {}).status || 'pending' }); return m
  }, [allItems, review])

  const reviewers = useMemo(() => {
    if (!combinedLog || combinedLog.length === 0) return []
    const map = {}
    combinedLog.forEach(entry => {
      const email = entry.email || 'anonymous'
      const name = entry.name || email.split('@')[0]
      if (!map[email]) {
        map[email] = { email, name, reviews: 0, confirmed: 0, flagged: 0, rejected: 0, resets: 0, edits: 0,
          timestamps: [], firstReview: null, lastReview: null,
          reviewedIds: new Set(), idsByStatus: { confirmed: new Set(), flagged: new Set(), rejected: new Set() } }
      }
      const r = map[email]
      r.reviews++
      if (entry.status === 'confirmed') { r.confirmed++; r.idsByStatus.confirmed.add(entry.itemId) }
      else if (entry.status === 'flagged') { r.flagged++; r.idsByStatus.flagged.add(entry.itemId) }
      else if (entry.status === 'rejected') { r.rejected++; r.idsByStatus.rejected.add(entry.itemId) }
      else if (entry.status === 'pending') r.resets++
      if (entry.edits && Object.keys(entry.edits).length > 0) r.edits++
      if (entry.status !== 'pending') r.reviewedIds.add(entry.itemId)
      if (entry.timestamp) {
        const ts = new Date(entry.timestamp).getTime()
        r.timestamps.push(ts)
        if (!r.firstReview || ts < new Date(r.firstReview).getTime()) r.firstReview = entry.timestamp
        if (!r.lastReview || ts > new Date(r.lastReview).getTime()) r.lastReview = entry.timestamp
      }
    })
    return Object.values(map).map(r => {
      const sorted = r.timestamps.sort((a, b) => a - b)
      let totalDiff = 0, diffCount = 0
      for (let i = 1; i < sorted.length; i++) {
        const diff = (sorted[i] - sorted[i - 1]) / 1000
        if (diff > 1 && diff < 600) { totalDiff += diff; diffCount++ }
      }
      r.avgSpeed = diffCount > 0 ? Math.round(totalDiff / diffCount) : null
      r.activeReviews = r.reviews - r.resets
      r.uniqueItems = r.reviewedIds.size
      if (r.firstReview && r.lastReview) r.sessionMinutes = Math.round((new Date(r.lastReview) - new Date(r.firstReview)) / 60000)
      return r
    })
  }, [combinedLog])

  // Sort — all columns sortable
  const sorted = useMemo(() => {
    const arr = [...reviewers]
    const sorters = {
      confirmed: (a, b) => b.idsByStatus.confirmed.size - a.idsByStatus.confirmed.size,
      flagged: (a, b) => b.idsByStatus.flagged.size - a.idsByStatus.flagged.size,
      rejected: (a, b) => b.idsByStatus.rejected.size - a.idsByStatus.rejected.size,
      edits: (a, b) => b.edits - a.edits,
      reviews: (a, b) => b.uniqueItems - a.uniqueItems,
      pct: (a, b) => b.uniqueItems - a.uniqueItems,
      remaining: (a, b) => a.uniqueItems - b.uniqueItems,
      speed: (a, b) => (a.avgSpeed || 9999) - (b.avgSpeed || 9999),
      session: (a, b) => (b.sessionMinutes || 0) - (a.sessionMinutes || 0),
    }
    const fn = sorters[sortBy] || sorters.reviews
    arr.sort(fn)
    return arr
  }, [reviewers, sortBy])

  const totalUniqueReviewers = reviewers.length
  const totalActiveReviews = reviewers.reduce((s, r) => s + r.activeReviews, 0)

  const remainingCount = useMemo(() => allItems.filter(i => itemStatusMap[i.id] === 'pending').length, [allItems, itemStatusMap])

  // Detail items for selected reviewer
  const detailItems = useMemo(() => {
    if (!selectedReviewer) return []
    const r = reviewers.find(rv => rv.email === selectedReviewer.email)
    if (!r) return []
    const ids = selectedReviewer.filterStatus ? (r.idsByStatus[selectedReviewer.filterStatus] || new Set()) : r.reviewedIds
    return [...ids].map(id => itemMap[id]).filter(Boolean).map(item => ({ ...item, _st: itemStatusMap[item.id] }))
  }, [selectedReviewer, reviewers, itemMap, itemStatusMap])

  if ((!combinedLog || combinedLog.length === 0) && syncStatus !== 'loading') return (
    <div className="p-8 text-center text-gray-400 text-sm">
      <Trophy size={32} className="mx-auto mb-2 text-gray-200" />
      <div>ยังไม่มีข้อมูล Review Log</div>
      <div className="text-xs mt-1">เริ่มตรวจสอบ OCR เพื่อดูสถิติผู้ตรวจที่นี่</div>
      <button onClick={() => doSync(true)} className="mt-3 px-3 py-1.5 text-xs bg-indigo-100 text-indigo-700 rounded-full hover:bg-indigo-200 transition inline-flex items-center gap-1">
        <RefreshCw size={11} /> ดึงข้อมูลจาก Google Sheet
      </button>
      {syncError && <div className="text-xs text-red-500 mt-2">{syncError}</div>}
    </div>
  )

  // ── Detail View ──
  if (selectedReviewer) {
    const r = reviewers.find(rv => rv.email === selectedReviewer.email)
    const pctDone = allItems.length > 0 && r ? (r.uniqueItems / allItems.length * 100) : 0
    const stLabels = { confirmed: '✅ ยืนยัน', flagged: '🔄 ตรวจซ้ำ', rejected: '🚫 ใช้ไม่ได้' }
    return (
      <div className="p-5">
        <button onClick={() => setSelectedReviewer(null)} className="flex items-center gap-1.5 text-sm text-indigo-600 hover:text-indigo-800 mb-4">
          <ArrowLeft size={14} /> กลับรายชื่อผู้ตรวจ
        </button>
        <div className="bg-gradient-to-r from-indigo-50 to-blue-50 rounded-xl border border-indigo-200 p-4 mb-4">
          <div className="flex items-center justify-between mb-2">
            <div>
              <div className="font-bold text-gray-800">{r?.name}</div>
              <div className="text-[10px] text-gray-400">{selectedReviewer.email}</div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-indigo-700">{pctDone.toFixed(1)}%</div>
              <div className="text-[10px] text-gray-500">{r?.uniqueItems || 0} / {allItems.length.toLocaleString()} หน้า</div>
            </div>
          </div>
          <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden mb-2">
            <div className={`h-3 rounded-full ${pctDone >= 50 ? 'bg-blue-500' : 'bg-amber-500'}`} style={{ width: `${Math.min(100, pctDone)}%` }} />
          </div>
          <div className="flex gap-4 text-xs flex-wrap">
            <span className="text-emerald-700">✅ {r?.confirmed || 0}</span>
            <span className="text-amber-700">🔄 {r?.flagged || 0}</span>
            <span className="text-red-700">🚫 {r?.rejected || 0}</span>
            <span className="text-gray-500 ml-auto">เหลือ {remainingCount.toLocaleString()} หน้า ({allItems.length > 0 ? (remainingCount / allItems.length * 100).toFixed(1) : 0}%)</span>
          </div>
        </div>
        {/* Filter pills */}
        <div className="flex gap-2 mb-3 flex-wrap">
          {[
            { key: null, label: `ทั้งหมด (${r?.uniqueItems || 0})` },
            { key: 'confirmed', label: `✅ (${r?.idsByStatus.confirmed.size || 0})` },
            { key: 'flagged', label: `🔄 (${r?.idsByStatus.flagged.size || 0})` },
            { key: 'rejected', label: `🚫 (${r?.idsByStatus.rejected.size || 0})` },
          ].map(f => (
            <button key={f.key || 'all'} onClick={() => setSelectedReviewer({ email: selectedReviewer.email, filterStatus: f.key })}
              className={`px-3 py-1 rounded-full text-xs font-medium transition ${selectedReviewer.filterStatus === f.key ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
              {f.label}
            </button>
          ))}
        </div>
        {/* Per-constituency summary */}
        {(() => {
          const conMap = {}
          detailItems.forEach(item => {
            const key = `${item.province} เขต ${item.constituency}`
            if (!conMap[key]) conMap[key] = { province: item.province, constituency: item.constituency, total: 0, reviewed: 0 }
            conMap[key].total++
            if (item._st !== 'pending') conMap[key].reviewed++
          })
          // Also add total items per constituency from allItems for full context
          const fullConMap = {}
          allItems.forEach(item => {
            const key = `${item.province} เขต ${item.constituency}`
            if (!fullConMap[key]) fullConMap[key] = { total: 0, reviewed: 0 }
            fullConMap[key].total++
            if (itemStatusMap[item.id] !== 'pending') fullConMap[key].reviewed++
          })
          const entries = Object.entries(conMap).sort((a, b) => a[0].localeCompare(b[0], 'th'))
          if (entries.length === 0) return null
          return (
            <div className="mb-4 rounded-lg border overflow-hidden">
              <table className="w-full text-xs">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="text-left px-3 py-2">เขต</th>
                    <th className="text-center px-2 py-2">ทั้งหมด (เขต)</th>
                    <th className="text-center px-2 py-2">ตรวจแล้ว</th>
                    <th className="text-center px-2 py-2">เหลือ</th>
                    <th className="text-center px-2 py-2">ความคืบหน้า</th>
                    <th className="text-center px-2 py-2">%</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map(([key, d]) => {
                    const full = fullConMap[key] || { total: d.total, reviewed: d.reviewed }
                    const pct = full.total > 0 ? (full.reviewed / full.total * 100) : 0
                    return (
                      <tr key={key} className="border-t hover:bg-gray-50">
                        <td className="px-3 py-1.5 font-medium">{key}</td>
                        <td className="px-2 py-1.5 text-center font-mono">{full.total}</td>
                        <td className="px-2 py-1.5 text-center font-mono text-emerald-700">{full.reviewed}</td>
                        <td className="px-2 py-1.5 text-center font-mono text-amber-600">{full.total - full.reviewed}</td>
                        <td className="px-2 py-1.5 text-center">
                          <div className="w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden mx-auto">
                            <div className={`h-full rounded-full ${pct >= 50 ? 'bg-blue-500' : 'bg-amber-500'}`} style={{ width: `${Math.min(100, pct)}%` }} />
                          </div>
                        </td>
                        <td className="px-2 py-1.5 text-center font-mono text-gray-600">{pct.toFixed(1)}%</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )
        })()}

        <div className="text-xs text-gray-500 mb-2">แสดง {detailItems.length} หน้า</div>
        <div className="max-h-[50vh] overflow-y-auto rounded-lg border">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-gray-100">
              <tr>
                <th className="text-left px-3 py-2 w-8">#</th>
                <th className="text-left px-3 py-2">ไฟล์</th>
                <th className="text-center px-2 py-2">จังหวัด</th>
                <th className="text-center px-2 py-2">เขต</th>
                <th className="text-center px-2 py-2">ประเภท</th>
                <th className="text-center px-2 py-2">หน่วย</th>
                <th className="text-center px-2 py-2">สถานะ</th>
              </tr>
            </thead>
            <tbody>
              {detailItems.map((item, idx) => {
                const stColor = item._st === 'confirmed' ? 'bg-emerald-100 text-emerald-700' : item._st === 'flagged' ? 'bg-amber-100 text-amber-700' : item._st === 'rejected' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-500'
                const vtColor = item.vote_type === 'แบ่งเขต' ? 'text-blue-700 bg-blue-50' : item.vote_type === 'บัญชีรายชื่อ' ? 'text-purple-700 bg-purple-50' : 'text-gray-600 bg-gray-50'
                return (
                  <tr key={item.id} className={`border-t hover:bg-blue-50/50 ${idx % 2 ? 'bg-gray-50/30' : ''}`}>
                    <td className="px-3 py-1.5 text-gray-400 font-mono">{idx + 1}</td>
                    <td className="px-3 py-1.5 font-mono text-[10px] truncate max-w-[200px]" title={item.file}>{item.file || item.id}</td>
                    <td className="px-2 py-1.5 text-center">{item.province}</td>
                    <td className="px-2 py-1.5 text-center">{item.constituency}</td>
                    <td className="px-2 py-1.5 text-center"><span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${vtColor}`}>{item.vote_type || '?'}</span></td>
                    <td className="px-2 py-1.5 text-center">{item.station_no || item.ocr_station_no || '?'}</td>
                    <td className="px-2 py-1.5 text-center"><span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${stColor}`}>{item._st}</span></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  return (
    <div>
      <button
        onClick={() => setExpanded(v => !v)}
        className="w-full flex items-center gap-2.5 py-3 text-sm font-semibold text-gray-700 hover:text-indigo-700 transition group"
      >
        <span className="w-7 h-7 rounded-lg bg-amber-50 flex items-center justify-center group-hover:bg-amber-100 transition">
          <Users size={15} className="text-amber-500" />
        </span>
        Reviewer Leaderboard
        {expanded ? <ChevronDown size={14} className="text-gray-400" /> : <ChevronRight size={14} className="text-gray-400" />}
        <span className="text-xs font-normal text-gray-400">
          {totalUniqueReviewers} คน · {totalActiveReviews} reviews
        </span>
        {remoteEntries.length > 0 && (
          <span className="text-[10px] font-normal text-emerald-500 flex items-center gap-0.5" title="เชื่อมต่อ Google Sheet แล้ว">
            <Cloud size={10} /> Cloud
          </span>
        )}
      </button>

      {expanded && (
        <div className="p-5">
          {/* Cloud sync bar */}
          <div className="flex items-center gap-2 mb-3 px-3 py-2 rounded-lg bg-gradient-to-r from-indigo-50 to-blue-50 border border-indigo-100">
            <div className="flex items-center gap-1.5 flex-1 min-w-0">
              {syncStatus === 'success' ? (
                <Cloud size={13} className="text-emerald-500 flex-shrink-0" />
              ) : syncStatus === 'error' ? (
                <CloudOff size={13} className="text-red-400 flex-shrink-0" />
              ) : syncStatus === 'loading' ? (
                <RefreshCw size={13} className="text-indigo-400 animate-spin flex-shrink-0" />
              ) : (
                <Wifi size={13} className="text-gray-300 flex-shrink-0" />
              )}
              <span className="text-[10px] text-gray-500 truncate">
                {syncStatus === 'loading' ? 'กำลังดึงข้อมูลจาก Google Sheet...' :
                 syncStatus === 'success' ? `Google Sheet: ${syncInfo?.count || 0} reviews${syncInfo?.fromCache ? ' (cached)' : ''} · อัปเดต ${syncInfo?.fetchedAt ? new Date(syncInfo.fetchedAt).toLocaleTimeString('th-TH') : ''}` :
                 syncStatus === 'error' ? `ไม่สามารถเชื่อมต่อ: ${syncError}` :
                 'ยังไม่ได้เชื่อมต่อ Google Sheet'}
              </span>
            </div>
            <button
              onClick={() => doSync(true)}
              disabled={syncStatus === 'loading'}
              className="flex-shrink-0 flex items-center gap-1 px-2.5 py-1 text-[10px] font-medium rounded-full bg-white border border-indigo-200 text-indigo-600 hover:bg-indigo-50 transition disabled:opacity-50"
              title="ดึงข้อมูลใหม่จาก Google Sheet"
            >
              <RefreshCw size={10} className={syncStatus === 'loading' ? 'animate-spin' : ''} />
              Sync
            </button>
          </div>


          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-[10px] text-gray-500 uppercase border-b border-gray-200">
                  <th className="px-2 py-2 text-left w-8">#</th>
                  <th className="px-2 py-2 text-left">ผู้ตรวจ</th>
                  {[
                    { key: 'confirmed', label: '✅ ยืนยัน' },
                    { key: 'flagged', label: '🔄 ตรวจซ้ำ' },
                    { key: 'rejected', label: '🚫 ใช้ไม่ได้' },
                    { key: 'edits', label: '✏️ แก้ไข' },
                    { key: 'reviews', label: '📄 หน้า (unique)' },
                    { key: 'pct', label: '% ความคืบหน้า' },
                    { key: 'remaining', label: '⏳ รอตรวจ' },
                    { key: 'speed', label: '⏱ เฉลี่ย' },
                    { key: 'session', label: 'เวลาทำงาน' },
                  ].map(col => (
                    <th key={col.key}
                      onClick={() => setSortBy(col.key)}
                      className={`px-2 py-2 ${col.key === 'session' ? 'text-right' : 'text-center'} cursor-pointer hover:bg-indigo-50 transition select-none ${sortBy === col.key ? 'text-indigo-700 bg-indigo-50/50' : ''}`}
                    >
                      {col.label}{sortBy === col.key ? ' ▼' : ''}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sorted.map((r, i) => {
                  const pct = allItems.length > 0 ? (r.uniqueItems / allItems.length * 100) : 0
                  return (
                  <tr key={r.email} className="border-b border-gray-50 hover:bg-gray-50 transition">
                    <td className="px-2 py-2"><Medal rank={i + 1} /></td>
                    <td className="px-2 py-2">
                      <button onClick={() => setSelectedReviewer({ email: r.email, filterStatus: null })} className="text-left hover:text-indigo-600 transition">
                        <div className="font-medium text-gray-700 hover:text-indigo-700">{r.name}</div>
                        <div className="text-[10px] text-gray-400">{r.email}</div>
                      </button>
                    </td>
                    <td className="px-2 py-2 text-center">
                      <button onClick={() => setSelectedReviewer({ email: r.email, filterStatus: 'confirmed' })} className="bg-emerald-50 text-emerald-700 px-1.5 py-0.5 rounded font-mono hover:bg-emerald-100 hover:ring-2 hover:ring-emerald-300 transition cursor-pointer" title={`${r.confirmed} actions / ${r.idsByStatus.confirmed.size} unique pages`}>{r.idsByStatus.confirmed.size}</button>
                    </td>
                    <td className="px-2 py-2 text-center">
                      <button onClick={() => setSelectedReviewer({ email: r.email, filterStatus: 'flagged' })} className="bg-amber-50 text-amber-700 px-1.5 py-0.5 rounded font-mono hover:bg-amber-100 hover:ring-2 hover:ring-amber-300 transition cursor-pointer" title={`${r.flagged} actions / ${r.idsByStatus.flagged.size} unique pages`}>{r.idsByStatus.flagged.size}</button>
                    </td>
                    <td className="px-2 py-2 text-center">
                      <button onClick={() => setSelectedReviewer({ email: r.email, filterStatus: 'rejected' })} className="bg-red-50 text-red-700 px-1.5 py-0.5 rounded font-mono hover:bg-red-100 hover:ring-2 hover:ring-red-300 transition cursor-pointer" title={`${r.rejected} actions / ${r.idsByStatus.rejected.size} unique pages`}>{r.idsByStatus.rejected.size}</button>
                    </td>
                    <td className="px-2 py-2 text-center">
                      <span className="bg-indigo-50 text-indigo-700 px-1.5 py-0.5 rounded font-mono">{r.edits}</span>
                    </td>
                    <td className="px-2 py-2 text-center">
                      <button onClick={() => setSelectedReviewer({ email: r.email, filterStatus: null })} className="font-semibold text-gray-700 hover:text-indigo-600 cursor-pointer" title={`${r.activeReviews} total actions / ${r.uniqueItems} unique pages`}>{r.uniqueItems}</button>
                    </td>
                    <td className="px-2 py-2 text-center">
                      <div className="flex items-center gap-1">
                        <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full ${pct >= 50 ? 'bg-blue-500' : 'bg-amber-500'}`} style={{ width: `${Math.min(100, pct)}%` }} />
                        </div>
                        <span className="text-[10px] font-mono text-gray-500">{pct.toFixed(1)}%</span>
                      </div>
                    </td>
                    <td className="px-2 py-2 text-center">
                      <span className="bg-gray-50 text-gray-500 px-1.5 py-0.5 rounded font-mono">{(allItems.length - r.uniqueItems).toLocaleString()}</span>
                    </td>
                    <td className="px-2 py-2 text-center">
                      {r.avgSpeed ? (
                        <span className={`font-mono ${r.avgSpeed < 10 ? 'text-amber-600' : r.avgSpeed < 30 ? 'text-emerald-600' : 'text-gray-500'}`}>
                          {r.avgSpeed}s
                        </span>
                      ) : (
                        <span className="text-gray-300">—</span>
                      )}
                    </td>
                    <td className="px-2 py-2 text-right text-gray-400">
                      {r.sessionMinutes != null ? (
                        r.sessionMinutes >= 60
                          ? `${Math.floor(r.sessionMinutes / 60)}h ${r.sessionMinutes % 60}m`
                          : `${r.sessionMinutes}m`
                      ) : '—'}
                    </td>
                  </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Summary */}
          <div className="mt-4 flex items-center gap-4 text-[10px] text-gray-400 flex-wrap">
            <span>📊 Local: {(reviewLog || []).length} entries · Cloud: {remoteEntries.length} entries · รวม: {combinedLog.length} entries</span>
            <span>📋 รวม {allItems.length.toLocaleString()} หน้า · เหลือ {remainingCount.toLocaleString()} หน้า</span>
            {sorted.length > 0 && sorted[0].avgSpeed && (
              <span>⚡ เร็วที่สุด: {sorted.reduce((best, r) => r.avgSpeed && (!best || r.avgSpeed < best) ? r.avgSpeed : best, null)}s / หน้า</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default function ReviewerLeaderboard(props) {
  return (
    <ErrorBoundary compact>
      <ReviewerLeaderboardInner {...props} />
    </ErrorBoundary>
  )
}
