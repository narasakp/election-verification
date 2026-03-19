import React, { useState, useMemo } from 'react'
import { BarChart3, PieChart, TrendingUp, ChevronDown, ChevronRight, AlertTriangle, CheckCircle2, XCircle, Clock, Eye } from 'lucide-react'
import ErrorBoundary from './ErrorBoundary'
import { validateItem } from '../utils/validation'

// Pure SVG Donut Chart
function DonutChart({ data, size = 160, strokeWidth = 28 }) {
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const cx = size / 2, cy = size / 2
  let offset = 0

  return (
    <svg width={size} height={size} className="transform -rotate-90">
      {data.map((d, i) => {
        const pct = d.value / (data.reduce((s, x) => s + x.value, 0) || 1)
        const dash = pct * circumference
        const el = (
          <circle
            key={i}
            cx={cx} cy={cy} r={radius}
            fill="none"
            stroke={d.color}
            strokeWidth={strokeWidth}
            strokeDasharray={`${dash} ${circumference - dash}`}
            strokeDashoffset={-offset}
            className="transition-all duration-500"
          />
        )
        offset += dash
        return el
      })}
    </svg>
  )
}

// Horizontal Bar
function HBar({ label, value, max, color = 'bg-indigo-500', suffix = '' }) {
  const pct = max > 0 ? (value / max) * 100 : 0
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-20 text-right text-gray-600 truncate" title={label}>{label}</span>
      <div className="flex-1 bg-gray-100 rounded-full h-4 overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-14 text-right text-gray-500 font-mono">{value}{suffix}</span>
    </div>
  )
}

// Validation Summary Bar Chart (vertical)
function ValidationBarChart({ data, height = 120 }) {
  const maxVal = Math.max(...data.map(d => d.value), 1)
  return (
    <div className="flex items-end gap-1.5 justify-center" style={{ height }}>
      {data.map((d, i) => {
        const h = (d.value / maxVal) * (height - 24)
        return (
          <div key={i} className="flex flex-col items-center gap-0.5">
            <span className="text-[9px] text-gray-500 font-mono">{d.value || ''}</span>
            <div
              className="rounded-t transition-all duration-500"
              style={{ width: 18, height: Math.max(h, 2), backgroundColor: d.color }}
              title={`${d.label}: ${d.value}`}
            />
            <span className="text-[8px] text-gray-400 w-8 text-center truncate" title={d.label}>{d.short}</span>
          </div>
        )
      })}
    </div>
  )
}

function AnalyticsDashboardInner({ allItems, review, reviewLog, anomalyFlags }) {
  const [expanded, setExpanded] = useState(false)

  // Review status breakdown
  const statusData = useMemo(() => {
    const counts = { pending: 0, confirmed: 0, flagged: 0, rejected: 0 }
    allItems.forEach(item => {
      const st = (review[item.id] || {}).status || 'pending'
      counts[st] = (counts[st] || 0) + 1
    })
    return counts
  }, [allItems, review])

  const donutData = useMemo(() => [
    { label: 'รอตรวจ', value: statusData.pending, color: '#d1d5db' },
    { label: 'ยืนยัน', value: statusData.confirmed, color: '#22c55e' },
    { label: 'ตรวจซ้ำ', value: statusData.flagged, color: '#f59e0b' },
    { label: 'ใช้ไม่ได้', value: statusData.rejected, color: '#ef4444' },
  ], [statusData])

  const totalReviewed = statusData.confirmed + statusData.flagged + statusData.rejected
  const reviewPct = allItems.length > 0 ? ((totalReviewed / allItems.length) * 100).toFixed(1) : 0

  // Per-province review progress
  const provinceProgress = useMemo(() => {
    const map = {}
    allItems.forEach(item => {
      const prov = item.province || 'ไม่ระบุ'
      if (!map[prov]) map[prov] = { total: 0, reviewed: 0 }
      map[prov].total++
      const st = (review[item.id] || {}).status || 'pending'
      if (st !== 'pending') map[prov].reviewed++
    })
    return Object.entries(map)
      .map(([name, d]) => ({ name, ...d, pct: d.total > 0 ? (d.reviewed / d.total * 100) : 0 }))
      .sort((a, b) => b.pct - a.pct)
  }, [allItems, review])

  // Per-constituency progress
  const constProgress = useMemo(() => {
    const map = {}
    allItems.forEach(item => {
      const key = `${item.province || '?'} เขต ${item.constituency || '?'}`
      if (!map[key]) map[key] = { total: 0, reviewed: 0, errors: 0 }
      map[key].total++
      const st = (review[item.id] || {}).status || 'pending'
      if (st !== 'pending') map[key].reviewed++
      const warns = validateItem(item)
      if (warns.some(w => w.severity === 'error')) map[key].errors++
    })
    return Object.entries(map)
      .map(([name, d]) => ({ name, ...d, pct: d.total > 0 ? (d.reviewed / d.total * 100) : 0 }))
      .sort((a, b) => b.errors - a.errors || a.pct - b.pct)
  }, [allItems, review])

  // Validation summary
  const validationSummary = useMemo(() => {
    const ruleCount = {}
    let errorCount = 0, warningCount = 0, infoCount = 0, cleanCount = 0
    allItems.forEach(item => {
      const warns = validateItem(item)
      if (warns.length === 0) { cleanCount++; return }
      warns.forEach(w => {
        const code = w.code || w.rule || 'unknown'
        ruleCount[code] = (ruleCount[code] || 0) + 1
        if (w.severity === 'error') errorCount++
        else if (w.severity === 'warning') warningCount++
        else infoCount++
      })
    })
    const ruleData = Object.entries(ruleCount)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 11)
      .map(([code, count]) => ({
        label: code,
        short: code.replace('V', ''),
        value: count,
        color: count > allItems.length * 0.3 ? '#ef4444' : count > allItems.length * 0.1 ? '#f59e0b' : '#6366f1',
      }))
    return { errorCount, warningCount, infoCount, cleanCount, ruleData }
  }, [allItems])

  // Review log timeline (last 7 days)
  const timelineData = useMemo(() => {
    if (!reviewLog || reviewLog.length === 0) return []
    const now = Date.now()
    const days = {}
    for (let i = 6; i >= 0; i--) {
      const d = new Date(now - i * 86400000)
      const key = d.toISOString().slice(0, 10)
      const label = `${d.getDate()}/${d.getMonth() + 1}`
      days[key] = { label, count: 0 }
    }
    reviewLog.forEach(entry => {
      if (!entry.timestamp) return
      const key = entry.timestamp.slice(0, 10)
      if (days[key]) days[key].count++
    })
    return Object.values(days)
  }, [reviewLog])

  // Review speed (avg seconds between reviews from log)
  const avgSpeed = useMemo(() => {
    if (!reviewLog || reviewLog.length < 2) return null
    const times = reviewLog
      .filter(e => e.timestamp && e.status !== 'pending')
      .map(e => new Date(e.timestamp).getTime())
      .sort((a, b) => a - b)
    if (times.length < 2) return null
    let totalDiff = 0, count = 0
    for (let i = 1; i < times.length; i++) {
      const diff = (times[i] - times[i - 1]) / 1000
      if (diff > 1 && diff < 600) { totalDiff += diff; count++ }
    }
    return count > 0 ? (totalDiff / count).toFixed(0) : null
  }, [reviewLog])

  if (allItems.length === 0) return null

  return (
    <div className="max-w-[1400px] mx-auto px-4 mt-3">
      <button
        onClick={() => setExpanded(v => !v)}
        className="flex items-center gap-2 text-sm font-semibold text-gray-700 hover:text-indigo-700 transition mb-2"
      >
        {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        <BarChart3 size={16} className="text-indigo-500" />
        📊 Analytics Dashboard
        <span className="text-xs font-normal text-gray-400 ml-2">
          {reviewPct}% ตรวจแล้ว ({totalReviewed}/{allItems.length})
        </span>
      </button>

      {expanded && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-6 animate-in fade-in">

          {/* Row 1: Donut + Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Donut Chart */}
            <div className="flex flex-col items-center">
              <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">สถานะ Review</h3>
              <div className="relative">
                <DonutChart data={donutData} size={160} strokeWidth={28} />
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-2xl font-bold text-gray-800">{reviewPct}%</span>
                  <span className="text-[10px] text-gray-400">ตรวจแล้ว</span>
                </div>
              </div>
              <div className="flex flex-wrap justify-center gap-3 mt-3">
                {donutData.map((d, i) => (
                  <div key={i} className="flex items-center gap-1 text-xs">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: d.color }} />
                    <span className="text-gray-600">{d.label}</span>
                    <span className="font-mono text-gray-400">{d.value}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-gray-50 rounded-lg p-3 text-center">
                <Clock size={18} className="mx-auto text-gray-400 mb-1" />
                <div className="text-lg font-bold text-gray-700">{statusData.pending}</div>
                <div className="text-[10px] text-gray-400">รอตรวจ</div>
              </div>
              <div className="bg-emerald-50 rounded-lg p-3 text-center">
                <CheckCircle2 size={18} className="mx-auto text-emerald-500 mb-1" />
                <div className="text-lg font-bold text-emerald-700">{statusData.confirmed}</div>
                <div className="text-[10px] text-gray-400">ยืนยัน</div>
              </div>
              <div className="bg-amber-50 rounded-lg p-3 text-center">
                <Eye size={18} className="mx-auto text-amber-500 mb-1" />
                <div className="text-lg font-bold text-amber-700">{statusData.flagged}</div>
                <div className="text-[10px] text-gray-400">ตรวจซ้ำ</div>
              </div>
              <div className="bg-red-50 rounded-lg p-3 text-center">
                <XCircle size={18} className="mx-auto text-red-500 mb-1" />
                <div className="text-lg font-bold text-red-700">{statusData.rejected}</div>
                <div className="text-[10px] text-gray-400">ใช้ไม่ได้</div>
              </div>
              {avgSpeed && (
                <div className="col-span-2 bg-indigo-50 rounded-lg p-3 text-center">
                  <TrendingUp size={18} className="mx-auto text-indigo-500 mb-1" />
                  <div className="text-lg font-bold text-indigo-700">{avgSpeed}s</div>
                  <div className="text-[10px] text-gray-400">เวลาเฉลี่ยต่อหน้า</div>
                </div>
              )}
            </div>

            {/* Validation Summary */}
            <div>
              <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">ปัญหาข้อมูล (Validation)</h3>
              <div className="grid grid-cols-3 gap-2 mb-3">
                <div className="bg-red-50 rounded px-2 py-1.5 text-center">
                  <div className="text-sm font-bold text-red-600">{validationSummary.errorCount}</div>
                  <div className="text-[9px] text-red-400">errors</div>
                </div>
                <div className="bg-amber-50 rounded px-2 py-1.5 text-center">
                  <div className="text-sm font-bold text-amber-600">{validationSummary.warningCount}</div>
                  <div className="text-[9px] text-amber-400">warnings</div>
                </div>
                <div className="bg-emerald-50 rounded px-2 py-1.5 text-center">
                  <div className="text-sm font-bold text-emerald-600">{validationSummary.cleanCount}</div>
                  <div className="text-[9px] text-emerald-400">สะอาด</div>
                </div>
              </div>
              {validationSummary.ruleData.length > 0 && (
                <ValidationBarChart data={validationSummary.ruleData} height={100} />
              )}
            </div>
          </div>

          {/* Row 2: Review Timeline + Province Progress */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Timeline (last 7 days) */}
            {timelineData.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">📅 การตรวจ 7 วันล่าสุด</h3>
                <div className="flex items-end gap-2 justify-between" style={{ height: 80 }}>
                  {timelineData.map((d, i) => {
                    const maxVal = Math.max(...timelineData.map(x => x.count), 1)
                    const h = (d.count / maxVal) * 60
                    return (
                      <div key={i} className="flex flex-col items-center gap-0.5 flex-1">
                        <span className="text-[9px] text-gray-500 font-mono">{d.count || ''}</span>
                        <div
                          className="w-full rounded-t bg-indigo-400 transition-all duration-500"
                          style={{ height: Math.max(h, 2) }}
                        />
                        <span className="text-[9px] text-gray-400">{d.label}</span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Province Progress */}
            <div>
              <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">🗺️ ความคืบหน้าต่อจังหวัด</h3>
              <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                {provinceProgress.map((p, i) => (
                  <HBar
                    key={i}
                    label={p.name}
                    value={p.reviewed}
                    max={p.total}
                    color={p.pct >= 100 ? 'bg-emerald-500' : p.pct > 50 ? 'bg-indigo-500' : p.pct > 0 ? 'bg-amber-400' : 'bg-gray-300'}
                    suffix={`/${p.total}`}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Row 3: Constituency with most errors */}
          <div>
            <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">
              <AlertTriangle size={12} className="inline text-amber-500 mr-1" />
              เขตที่มีปัญหามากที่สุด
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
              {constProgress.filter(c => c.errors > 0).slice(0, 9).map((c, i) => (
                <div key={i} className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2 text-xs">
                  <span className="text-gray-700 truncate flex-1" title={c.name}>{c.name}</span>
                  <div className="flex items-center gap-2 ml-2">
                    <span className="text-red-500 font-mono font-semibold">{c.errors} err</span>
                    <span className="text-gray-400">{c.reviewed}/{c.total}</span>
                  </div>
                </div>
              ))}
              {constProgress.filter(c => c.errors > 0).length === 0 && (
                <div className="text-xs text-gray-400 col-span-3">ไม่พบ error ในข้อมูล ✅</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function AnalyticsDashboard(props) {
  return (
    <ErrorBoundary compact>
      <AnalyticsDashboardInner {...props} />
    </ErrorBoundary>
  )
}
