import React from 'react'

export default React.memo(function StatsBar({ stats }) {
  const reviewed = stats.confirmed + stats.flagged + stats.rejected
  const pct = stats.total > 0 ? Math.round((reviewed / stats.total) * 100) : 0

  return (
    <div className="flex items-center gap-3 text-sm" role="status" aria-label={`ความคืบหน้า ${pct}% ตรวจแล้ว ${reviewed} จาก ${stats.total}`}>
      {/* Progress bar */}
      <div className="hidden sm:flex items-center gap-2">
        <div className="w-24 bg-white/20 rounded-full h-2 overflow-hidden" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label={`ตรวจแล้ว ${pct}%`}>
          <div
            className="bg-emerald-400 h-full rounded-full transition-all duration-300"
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="text-xs font-bold opacity-90">{pct}%</span>
      </div>
      {/* Compact stats */}
      <div className="hidden md:flex items-center gap-3 opacity-80 text-xs">
        <span aria-label={`รอตรวจ ${stats.pending}`}>📋 {stats.pending}</span>
        <span aria-label={`ยืนยันแล้ว ${stats.confirmed}`}>✅ {stats.confirmed}</span>
        <span aria-label={`ตรวจอีกรอบ ${stats.flagged}`}>⚠️ {stats.flagged}</span>
        <span aria-label={`ใช้ไม่ได้ ${stats.rejected}`}>❌ {stats.rejected}</span>
      </div>
      {/* Mobile: just percentage */}
      <span className="sm:hidden text-xs font-bold opacity-90">{pct}% ({reviewed}/{stats.total})</span>
    </div>
  )
})
