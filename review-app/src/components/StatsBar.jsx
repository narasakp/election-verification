import React from 'react'

export default React.memo(function StatsBar({ stats }) {
  const reviewed = stats.confirmed + stats.flagged + stats.rejected
  const pct = stats.total > 0 ? Math.round((reviewed / stats.total) * 100) : 0

  return (
    <div className="flex items-center gap-3 text-sm">
      {/* Progress bar */}
      <div className="hidden sm:flex items-center gap-2">
        <div className="w-24 bg-white/20 rounded-full h-2 overflow-hidden">
          <div
            className="bg-emerald-400 h-full rounded-full transition-all duration-300"
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="text-xs font-bold opacity-90">{pct}%</span>
      </div>
      {/* Compact stats */}
      <div className="hidden md:flex items-center gap-3 opacity-80 text-xs">
        <span>📋 {stats.pending}</span>
        <span>✅ {stats.confirmed}</span>
        <span>⚠️ {stats.flagged}</span>
        <span>❌ {stats.rejected}</span>
      </div>
      {/* Mobile: just percentage */}
      <span className="sm:hidden text-xs font-bold opacity-90">{pct}% ({reviewed}/{stats.total})</span>
    </div>
  )
})
