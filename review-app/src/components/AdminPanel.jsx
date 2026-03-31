import React, { useMemo, useState } from 'react'
import { getAllAnomalyScores, getAllSummaries, verifyLogIntegrity } from '../utils/reviewLog'
import { X, Upload, AlertTriangle, Shield, Users, Activity } from 'lucide-react'
import ErrorBoundary from './ErrorBoundary'

/**
 * Admin Panel (F6) — shows user activity, anomaly scores, consensus conflicts,
 * integrity checks, and allows importing external review logs.
 */
function AdminPanelInner({ reviewLog, allItems, review, onClose, onImportLog }) {
  const [activeTab, setActiveTab] = useState('users')

  // Anomaly scores for all users
  const anomalyScores = useMemo(() => getAllAnomalyScores(reviewLog), [reviewLog])

  // All item summaries
  const summaries = useMemo(() => getAllSummaries(reviewLog), [reviewLog])

  // Integrity check
  const corrupted = useMemo(() => verifyLogIntegrity(reviewLog), [reviewLog])

  // Conflict items
  const conflictItems = useMemo(() => {
    return Object.entries(summaries)
      .filter(([_, s]) => s.hasConflict)
      .map(([itemId, s]) => ({ itemId, ...s }))
      .sort((a, b) => b.reviewerCount - a.reviewerCount)
  }, [summaries])

  // User activity summary
  const userActivity = useMemo(() => {
    const byUser = {}
    reviewLog.forEach(r => {
      if (!r.email) return
      if (!byUser[r.email]) {
        byUser[r.email] = { email: r.email, name: r.name || r.email, reviews: [], statuses: {} }
      }
      byUser[r.email].reviews.push(r)
      const st = r.status || 'pending'
      byUser[r.email].statuses[st] = (byUser[r.email].statuses[st] || 0) + 1
    })
    return Object.values(byUser)
      .map(u => {
        const sorted = u.reviews.sort((a, b) => a.timestamp.localeCompare(b.timestamp))
        const first = sorted[0]?.timestamp
        const last = sorted[sorted.length - 1]?.timestamp
        const anomaly = anomalyScores[u.email] || { score: 0, level: 'ok', factors: [] }
        return { ...u, reviewCount: u.reviews.length, first, last, anomaly }
      })
      .sort((a, b) => b.anomaly.score - a.anomaly.score)
  }, [reviewLog, anomalyScores])

  // Overall stats
  const overallStats = useMemo(() => {
    const totalReviews = reviewLog.length
    const uniqueUsers = new Set(reviewLog.map(r => r.email).filter(Boolean)).size
    const itemsReviewed = Object.keys(summaries).length
    const conflictCount = conflictItems.length
    const dangerUsers = Object.values(anomalyScores).filter(a => a.level === 'danger').length
    const warningUsers = Object.values(anomalyScores).filter(a => a.level === 'warning').length
    return { totalReviews, uniqueUsers, itemsReviewed, conflictCount, dangerUsers, warningUsers, corruptedCount: corrupted.length }
  }, [reviewLog, summaries, conflictItems, anomalyScores, corrupted])

  const handleImportLog = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      try {
        const data = JSON.parse(ev.target.result)
        // Support both raw array and { log: [...] } format
        const logArray = Array.isArray(data) ? data : (data.log || [])
        // Validate entry structure — require essential fields
        const validEntries = logArray.filter(entry =>
          entry && typeof entry === 'object' &&
          typeof entry.itemId === 'string' && entry.itemId.length > 0 &&
          typeof entry.email === 'string' &&
          typeof entry.status === 'string' &&
          typeof entry.timestamp === 'string' &&
          ['confirmed', 'flagged', 'rejected', 'pending'].includes(entry.status)
        )
        const skipped = logArray.length - validEntries.length
        if (validEntries.length > 0) {
          onImportLog(validEntries)
          if (skipped > 0) {
            alert(`⚠️ ข้าม ${skipped} รายการที่โครงสร้างไม่ถูกต้อง`)
          }
        } else {
          alert(`ไม่พบข้อมูล review log ที่ถูกต้องในไฟล์${skipped > 0 ? ` (พบ ${skipped} รายการที่โครงสร้างผิด)` : ''}`)
        }
      } catch {
        alert('ไฟล์ไม่ถูกต้อง (JSON parse error)')
      }
    }
    reader.readAsText(file)
    e.target.value = ''
  }

  const levelColor = (level) => {
    if (level === 'danger') return 'text-red-600 bg-red-50 border-red-200'
    if (level === 'warning') return 'text-amber-600 bg-amber-50 border-amber-200'
    return 'text-green-600 bg-green-50 border-green-200'
  }

  const levelBadge = (level) => {
    if (level === 'danger') return '🔴 อันตราย'
    if (level === 'warning') return '🟡 น่าสงสัย'
    return '🟢 ปกติ'
  }

  const tabs = [
    { id: 'users', label: 'ผู้ตรวจ', icon: Users },
    { id: 'conflicts', label: 'ขัดแย้ง', icon: AlertTriangle },
    { id: 'integrity', label: 'ความสมบูรณ์', icon: Shield },
    { id: 'activity', label: 'Log ล่าสุด', icon: Activity },
  ]

  return (
    <div className="fixed inset-0 z-[90] bg-black/60 flex items-start justify-center pt-10 overflow-y-auto">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl mx-4 mb-10">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b bg-gradient-to-r from-amber-50 to-orange-50 rounded-t-xl">
          <div>
            <h2 className="text-lg font-bold text-gray-800 flex items-center gap-2">
              🛡️ Admin Panel — ระบบตรวจสอบ
            </h2>
            <p className="text-xs text-gray-500 mt-0.5">
              {overallStats.uniqueUsers} ผู้ตรวจ · {overallStats.totalReviews} ครั้ง · {overallStats.itemsReviewed} หน้า
            </p>
          </div>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-1 px-3 py-1.5 bg-indigo-100 text-indigo-700 rounded text-xs hover:bg-indigo-200 transition cursor-pointer font-medium">
              <Upload size={12} /> นำเข้า Log
              <input type="file" accept=".json" className="hidden" onChange={handleImportLog} />
            </label>
            <button onClick={onClose} className="p-1.5 hover:bg-gray-200 rounded-full transition">
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Alert bar */}
        {(overallStats.dangerUsers > 0 || overallStats.corruptedCount > 0) && (
          <div className="px-6 py-2 bg-red-50 border-b border-red-200 flex items-center gap-2 text-sm text-red-700">
            <AlertTriangle size={14} />
            {overallStats.dangerUsers > 0 && <span>⚠️ {overallStats.dangerUsers} ผู้ตรวจมีคะแนนความเสี่ยงสูง</span>}
            {overallStats.corruptedCount > 0 && <span>🔴 พบ {overallStats.corruptedCount} รายการ log ที่ถูกแก้ไข</span>}
          </div>
        )}

        {/* Summary cards */}
        <div className="grid grid-cols-4 gap-3 px-6 py-4 border-b">
          <div className="bg-blue-50 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-blue-700">{overallStats.uniqueUsers}</div>
            <div className="text-xs text-blue-600">ผู้ตรวจ</div>
          </div>
          <div className="bg-green-50 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-green-700">{overallStats.itemsReviewed}</div>
            <div className="text-xs text-green-600">หน้าที่ตรวจแล้ว</div>
          </div>
          <div className={`rounded-lg p-3 text-center ${overallStats.conflictCount > 0 ? 'bg-amber-50' : 'bg-gray-50'}`}>
            <div className={`text-2xl font-bold ${overallStats.conflictCount > 0 ? 'text-amber-700' : 'text-gray-400'}`}>{overallStats.conflictCount}</div>
            <div className={`text-xs ${overallStats.conflictCount > 0 ? 'text-amber-600' : 'text-gray-400'}`}>ขัดแย้ง</div>
          </div>
          <div className={`rounded-lg p-3 text-center ${overallStats.dangerUsers > 0 ? 'bg-red-50' : 'bg-gray-50'}`}>
            <div className={`text-2xl font-bold ${overallStats.dangerUsers > 0 ? 'text-red-700' : 'text-gray-400'}`}>{overallStats.dangerUsers}</div>
            <div className={`text-xs ${overallStats.dangerUsers > 0 ? 'text-red-600' : 'text-gray-400'}`}>ผู้ตรวจเสี่ยง</div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b px-6">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition ${
                activeTab === t.id
                  ? 'border-amber-500 text-amber-700'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <t.icon size={14} /> {t.label}
              {t.id === 'conflicts' && overallStats.conflictCount > 0 && (
                <span className="ml-1 bg-amber-100 text-amber-700 text-xs px-1.5 py-0.5 rounded-full">{overallStats.conflictCount}</span>
              )}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="px-6 py-4 max-h-[60vh] overflow-y-auto">
          {/* Users tab */}
          {activeTab === 'users' && (
            <div className="space-y-3">
              {userActivity.length === 0 ? (
                <p className="text-center text-gray-400 py-8">ยังไม่มีข้อมูลผู้ตรวจ</p>
              ) : userActivity.map(u => (
                <div key={u.email} className={`border rounded-lg p-4 ${levelColor(u.anomaly.level)}`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium text-sm">{u.name}</div>
                      <div className="text-xs opacity-70">{u.email}</div>
                    </div>
                    <div className="text-right">
                      <span className="text-xs font-bold px-2 py-1 rounded-full border">
                        {levelBadge(u.anomaly.level)} (คะแนน {u.anomaly.score})
                      </span>
                    </div>
                  </div>
                  <div className="mt-2 flex gap-4 text-xs">
                    <span>ตรวจ {u.reviewCount} ครั้ง</span>
                    {u.statuses.confirmed && <span className="text-green-700">✓ {u.statuses.confirmed}</span>}
                    {u.statuses.flagged && <span className="text-amber-700">🔄 {u.statuses.flagged}</span>}
                    {u.statuses.rejected && <span className="text-red-700">✗ {u.statuses.rejected}</span>}
                  </div>
                  {u.anomaly.factors.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {u.anomaly.factors.map((f, i) => (
                        <div key={i} className="text-xs flex items-center gap-2">
                          <span className="font-mono text-[10px] bg-white/50 px-1 rounded">+{f.points}</span>
                          {f.desc}
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="mt-1 text-[10px] opacity-50">
                    {u.first && `เริ่ม ${new Date(u.first).toLocaleString('th-TH')}`}
                    {u.last && ` → ล่าสุด ${new Date(u.last).toLocaleString('th-TH')}`}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Conflicts tab */}
          {activeTab === 'conflicts' && (
            <div className="space-y-3">
              {conflictItems.length === 0 ? (
                <p className="text-center text-gray-400 py-8">ไม่พบรายการที่ขัดแย้ง 🎉</p>
              ) : conflictItems.map(c => (
                <div key={c.itemId} className="border border-amber-200 bg-amber-50 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div className="font-mono text-sm font-medium text-gray-800">{c.itemId}</div>
                    <div className="text-xs">
                      <span className="bg-amber-200 text-amber-800 px-2 py-0.5 rounded-full font-medium">
                        {c.reviewerCount} ผู้ตรวจ · {c.totalReviews} ครั้ง
                      </span>
                    </div>
                  </div>
                  <div className="mt-2 flex gap-3 text-xs">
                    <span className="font-medium">
                      {c.majorityStatus
                        ? `Consensus: ${c.majorityStatus}${c.consensusRatio < 1 ? ` (${Math.round(c.consensusRatio * 100)}%)` : ''}`
                        : c.isTie
                          ? `⚖️ เสมอ: ${c.tiedStatuses?.join(' vs ')}`
                          : 'ไม่มี consensus'}
                    </span>
                    {Object.entries(c.statusCounts).map(([st, cnt]) => (
                      <span key={st} className={st === c.majorityStatus ? 'font-bold' : 'opacity-60'}>
                        {st}: {cnt}
                      </span>
                    ))}
                  </div>
                  {c.outliers.length > 0 && (
                    <div className="mt-2 text-xs text-red-600">
                      Outliers: {c.outliers.map(o => `${o.name || o.email} (${o.status})`).join(', ')}
                    </div>
                  )}
                  {Object.keys(c.editConflicts).length > 0 && (
                    <div className="mt-2 text-xs">
                      <span className="font-medium text-amber-800">ค่าแก้ไขขัดแย้ง:</span>
                      {Object.entries(c.editConflicts).map(([field, vals]) => (
                        <div key={field} className="ml-2">
                          <span className="font-mono">{field}</span>: {vals.map(v => `${v.value} (×${v.count})`).join(' vs ')}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Integrity tab */}
          {activeTab === 'integrity' && (
            <div className="space-y-4">
              <div className={`border rounded-lg p-4 ${corrupted.length > 0 ? 'bg-red-50 border-red-200' : 'bg-green-50 border-green-200'}`}>
                <div className="flex items-center gap-2 text-sm font-medium">
                  <Shield size={16} />
                  {corrupted.length === 0
                    ? <span className="text-green-700">✅ Log ทั้งหมดผ่านการตรวจ checksum</span>
                    : <span className="text-red-700">⚠️ พบ {corrupted.length} รายการที่ checksum ไม่ตรง (อาจถูกแก้ไขจาก DevTools)</span>
                  }
                </div>
                {corrupted.length > 0 && (
                  <div className="mt-2 text-xs text-red-600">
                    Index ที่ผิด: {corrupted.slice(0, 20).join(', ')}{corrupted.length > 20 ? '...' : ''}
                  </div>
                )}
              </div>

              <div className="border rounded-lg p-4 bg-gray-50">
                <div className="text-sm font-medium text-gray-700 mb-2">📊 สถิติ Log</div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>จำนวน log ทั้งหมด: <b>{reviewLog.length}</b></div>
                  <div>ผู้ตรวจทั้งหมด: <b>{overallStats.uniqueUsers}</b></div>
                  <div>หน้าที่ถูกตรวจ: <b>{overallStats.itemsReviewed}</b></div>
                  <div>Log ที่มี edits: <b>{reviewLog.filter(r => r.edits && Object.keys(r.edits).length > 0).length}</b></div>
                  <div>Log ที่มี checksum: <b>{reviewLog.filter(r => r.checksum).length}</b></div>
                  <div>Log ไม่มี checksum (เก่า): <b>{reviewLog.filter(r => !r.checksum).length}</b></div>
                </div>
              </div>
            </div>
          )}

          {/* Activity tab */}
          {activeTab === 'activity' && (
            <div className="space-y-1">
              {reviewLog.length === 0 ? (
                <p className="text-center text-gray-400 py-8">ยังไม่มี log</p>
              ) : (
                <div className="max-h-[50vh] overflow-y-auto">
                  <table className="w-full text-xs">
                    <thead className="sticky top-0 bg-gray-100">
                      <tr>
                        <th className="text-left px-2 py-1.5">เวลา</th>
                        <th className="text-left px-2 py-1.5">ผู้ตรวจ</th>
                        <th className="text-left px-2 py-1.5">Item</th>
                        <th className="text-left px-2 py-1.5">สถานะ</th>
                        <th className="text-left px-2 py-1.5">แก้ไข</th>
                        <th className="text-left px-2 py-1.5">✓</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...reviewLog].reverse().slice(0, 200).map((r, i) => {
                        const hasValidChecksum = r.checksum ? '✅' : '—'
                        const editCount = r.edits ? Object.keys(r.edits).length : 0
                        return (
                          <tr key={i} className={`border-t ${i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}`}>
                            <td className="px-2 py-1 font-mono text-[10px] text-gray-500 whitespace-nowrap">
                              {r.timestamp ? new Date(r.timestamp).toLocaleString('th-TH') : '—'}
                            </td>
                            <td className="px-2 py-1 truncate max-w-[120px]">{r.name || r.email || '—'}</td>
                            <td className="px-2 py-1 font-mono truncate max-w-[150px]">{r.itemId}</td>
                            <td className="px-2 py-1">
                              <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                                r.status === 'confirmed' ? 'bg-green-100 text-green-700' :
                                r.status === 'flagged' ? 'bg-amber-100 text-amber-700' :
                                r.status === 'rejected' ? 'bg-red-100 text-red-700' :
                                'bg-gray-100 text-gray-500'
                              }`}>
                                {r.status}
                              </span>
                            </td>
                            <td className="px-2 py-1 text-center">
                              {editCount > 0 ? <span className="text-indigo-600 font-medium">{editCount}</span> : '—'}
                            </td>
                            <td className="px-2 py-1 text-center text-[10px]">{hasValidChecksum}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                  {reviewLog.length > 200 && (
                    <p className="text-center text-xs text-gray-400 py-2">แสดง 200 / {reviewLog.length} รายการ</p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function AdminPanel(props) {
  return (
    <ErrorBoundary compact>
      <AdminPanelInner {...props} />
    </ErrorBoundary>
  )
}
