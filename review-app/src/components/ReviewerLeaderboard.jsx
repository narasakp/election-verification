import React, { useState, useMemo } from 'react'
import { Users, ChevronDown, ChevronRight, Trophy, Clock, AlertTriangle, CheckCircle2, Zap } from 'lucide-react'
import ErrorBoundary from './ErrorBoundary'

function Medal({ rank }) {
  if (rank === 1) return <span className="text-amber-400">🥇</span>
  if (rank === 2) return <span className="text-gray-400">🥈</span>
  if (rank === 3) return <span className="text-amber-700">🥉</span>
  return <span className="text-gray-300 text-xs font-mono w-5 text-center inline-block">{rank}</span>
}

function ReviewerLeaderboardInner({ reviewLog, allItems, review }) {
  const [expanded, setExpanded] = useState(true)
  const [sortBy, setSortBy] = useState('reviews') // reviews | speed | accuracy

  // Parse reviewLog to extract per-reviewer stats
  const reviewers = useMemo(() => {
    if (!reviewLog || reviewLog.length === 0) return []

    const map = {}
    reviewLog.forEach(entry => {
      const email = entry.email || 'anonymous'
      const name = entry.name || email.split('@')[0]
      if (!map[email]) {
        map[email] = {
          email,
          name,
          reviews: 0,
          confirmed: 0,
          flagged: 0,
          rejected: 0,
          resets: 0,
          edits: 0,
          timestamps: [],
          firstReview: null,
          lastReview: null,
        }
      }
      const r = map[email]
      r.reviews++
      if (entry.status === 'confirmed') r.confirmed++
      else if (entry.status === 'flagged') r.flagged++
      else if (entry.status === 'rejected') r.rejected++
      else if (entry.status === 'pending') r.resets++
      if (entry.edits && Object.keys(entry.edits).length > 0) r.edits++

      if (entry.timestamp) {
        const ts = new Date(entry.timestamp).getTime()
        r.timestamps.push(ts)
        if (!r.firstReview || ts < new Date(r.firstReview).getTime()) r.firstReview = entry.timestamp
        if (!r.lastReview || ts > new Date(r.lastReview).getTime()) r.lastReview = entry.timestamp
      }
    })

    // Calculate avg speed per reviewer
    return Object.values(map).map(r => {
      const sorted = r.timestamps.sort((a, b) => a - b)
      let totalDiff = 0, diffCount = 0
      for (let i = 1; i < sorted.length; i++) {
        const diff = (sorted[i] - sorted[i - 1]) / 1000
        if (diff > 1 && diff < 600) { totalDiff += diff; diffCount++ }
      }
      r.avgSpeed = diffCount > 0 ? Math.round(totalDiff / diffCount) : null
      r.activeReviews = r.reviews - r.resets
      // Session duration in minutes
      if (r.firstReview && r.lastReview) {
        r.sessionMinutes = Math.round((new Date(r.lastReview) - new Date(r.firstReview)) / 60000)
      }
      return r
    })
  }, [reviewLog])

  // Sort
  const sorted = useMemo(() => {
    const arr = [...reviewers]
    if (sortBy === 'reviews') arr.sort((a, b) => b.activeReviews - a.activeReviews)
    else if (sortBy === 'speed') arr.sort((a, b) => (a.avgSpeed || 9999) - (b.avgSpeed || 9999))
    else if (sortBy === 'edits') arr.sort((a, b) => b.edits - a.edits)
    return arr
  }, [reviewers, sortBy])

  const totalUniqueReviewers = reviewers.length
  const totalActiveReviews = reviewers.reduce((s, r) => s + r.activeReviews, 0)

  if (!reviewLog || reviewLog.length === 0) return (
    <div className="p-8 text-center text-gray-400 text-sm">
      <Trophy size={32} className="mx-auto mb-2 text-gray-200" />
      <div>ยังไม่มีข้อมูล Review Log</div>
      <div className="text-xs mt-1">เริ่มตรวจสอบ OCR เพื่อดูสถิติผู้ตรวจที่นี่</div>
    </div>
  )

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
      </button>

      {expanded && (
        <div className="p-5">
          {/* Sort buttons */}
          <div className="flex items-center gap-2 mb-4">
            <span className="text-xs text-gray-500">เรียงตาม:</span>
            {[
              { key: 'reviews', label: 'จำนวน', icon: CheckCircle2 },
              { key: 'speed', label: 'ความเร็ว', icon: Zap },
              { key: 'edits', label: 'แก้ไข', icon: AlertTriangle },
            ].map(s => (
              <button
                key={s.key}
                onClick={() => setSortBy(s.key)}
                className={`flex items-center gap-1 px-3 py-1 rounded-full text-xs transition ${
                  sortBy === s.key
                    ? 'bg-indigo-100 text-indigo-700 font-semibold'
                    : 'bg-gray-50 text-gray-500 hover:bg-gray-100'
                }`}
              >
                <s.icon size={11} /> {s.label}
              </button>
            ))}
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-[10px] text-gray-500 uppercase border-b border-gray-200">
                  <th className="px-2 py-2 text-left w-8">#</th>
                  <th className="px-2 py-2 text-left">ผู้ตรวจ</th>
                  <th className="px-2 py-2 text-center">✅ ยืนยัน</th>
                  <th className="px-2 py-2 text-center">🔄 ตรวจซ้ำ</th>
                  <th className="px-2 py-2 text-center">🚫 ใช้ไม่ได้</th>
                  <th className="px-2 py-2 text-center">✏️ แก้ไข</th>
                  <th className="px-2 py-2 text-center">รวม</th>
                  <th className="px-2 py-2 text-center">⏱ เฉลี่ย</th>
                  <th className="px-2 py-2 text-right">เวลาทำงาน</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((r, i) => (
                  <tr key={r.email} className="border-b border-gray-50 hover:bg-gray-50 transition">
                    <td className="px-2 py-2"><Medal rank={i + 1} /></td>
                    <td className="px-2 py-2">
                      <div className="font-medium text-gray-700">{r.name}</div>
                      <div className="text-[10px] text-gray-400">{r.email}</div>
                    </td>
                    <td className="px-2 py-2 text-center">
                      <span className="bg-emerald-50 text-emerald-700 px-1.5 py-0.5 rounded font-mono">{r.confirmed}</span>
                    </td>
                    <td className="px-2 py-2 text-center">
                      <span className="bg-amber-50 text-amber-700 px-1.5 py-0.5 rounded font-mono">{r.flagged}</span>
                    </td>
                    <td className="px-2 py-2 text-center">
                      <span className="bg-red-50 text-red-700 px-1.5 py-0.5 rounded font-mono">{r.rejected}</span>
                    </td>
                    <td className="px-2 py-2 text-center">
                      <span className="bg-indigo-50 text-indigo-700 px-1.5 py-0.5 rounded font-mono">{r.edits}</span>
                    </td>
                    <td className="px-2 py-2 text-center font-semibold text-gray-700">{r.activeReviews}</td>
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
                ))}
              </tbody>
            </table>
          </div>

          {/* Summary */}
          <div className="mt-4 flex items-center gap-4 text-[10px] text-gray-400">
            <span>📊 คำนวณจาก {reviewLog.length} entries ใน review log</span>
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
