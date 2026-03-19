import React, { useState, useEffect, useMemo } from 'react'
import { HardDrive, CheckCircle2, FileText, ChevronDown, ChevronRight, Search, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import ErrorBoundary from './ErrorBoundary'

const BACKUP_URL = './data/backup_status.json'

function fmt(n) {
  return n == null ? '—' : n.toLocaleString()
}

function BackupDashboardInner() {
  const [data, setData] = useState(null)
  const [expanded, setExpanded] = useState(false)
  const [search, setSearch] = useState('')
  const [sortCol, setSortCol] = useState('name')
  const [sortAsc, setSortAsc] = useState(true)

  useEffect(() => {
    fetch(BACKUP_URL)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setData(d) })
      .catch(() => {})
  }, [])

  const toggleSort = (col) => {
    if (sortCol === col) setSortAsc(v => !v)
    else { setSortCol(col); setSortAsc(col === 'name') }
  }

  const filteredProvs = useMemo(() => {
    if (!data?.provinces) return []
    let list = data.provinces
    if (search.trim()) {
      const q = search.trim().toLowerCase()
      list = list.filter(p => p.name.toLowerCase().includes(q))
    }
    const sorted = [...list].sort((a, b) => {
      let va, vb
      switch (sortCol) {
        case 'name': va = a.name; vb = b.name; return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va)
        case 'actual': va = a.actual || 0; vb = b.actual || 0; break
        case 'expected': va = a.expected || 0; vb = b.expected || 0; break
        case 'pct': va = a.pct || 0; vb = b.pct || 0; break
        case 'status': va = a.complete ? 2 : (a.actual || 0) > 0 ? 1 : 0; vb = b.complete ? 2 : (b.actual || 0) > 0 ? 1 : 0; break
        default: return 0
      }
      return sortAsc ? va - vb : vb - va
    })
    return sorted
  }, [data, search, sortCol, sortAsc])

  if (!data) return null

  const s = data.summary || {}
  const allComplete = s.complete === s.total

  return (
    <div className="bg-white border-b">
      <div className="max-w-[1400px] mx-auto px-4">
        <button
          onClick={() => setExpanded(v => !v)}
          className="w-full flex items-center gap-2 py-2.5 text-sm font-semibold text-slate-700 hover:text-slate-900 transition"
        >
          <HardDrive size={16} className="text-blue-600" />
          ECT Backup — Google Drive
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          <span className="text-xs font-normal text-gray-400 ml-2">
            {fmt(s.total_actual)} PDF / {s.total} จังหวัด
          </span>
          {allComplete && !expanded && (
            <span className="ml-auto flex items-center gap-1 text-xs font-normal text-emerald-600">
              <CheckCircle2 size={12} /> ครบทุกจังหวัด
            </span>
          )}
        </button>

        {expanded && (
          <div className="pb-4">
            {/* Summary Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
              <SummaryCard
                icon="📂"
                label="มีข้อมูล"
                value={s.has_data}
                sub={`/ ${s.total} จังหวัด`}
              />
              <SummaryCard
                icon="✅"
                label="ครบ 100%"
                value={s.complete}
                sub="verified complete"
                valueColor="text-emerald-600"
              />
              <SummaryCard
                icon="📄"
                label="PDF ทั้งหมด"
                value={fmt(s.total_actual)}
                sub={s.total_expected ? `/ ${fmt(s.total_expected)} expected` : ''}
              />
              <SummaryCard
                icon="📊"
                label="ความคืบหน้า"
                value={`${s.pct}%`}
                sub="overall progress"
                valueColor={s.pct >= 100 ? 'text-emerald-600' : 'text-blue-600'}
              />
            </div>

            {/* Overall Progress Bar */}
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-4">
              <div className="flex justify-between items-center mb-1.5">
                <span className="text-xs font-semibold text-gray-600">📊 ความคืบหน้ารวม (ไฟล์จริงบน Google Drive)</span>
                <span className="text-xs text-gray-500 font-mono">{s.pct}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div
                  className="bg-gradient-to-r from-blue-500 to-emerald-500 h-2.5 rounded-full transition-all duration-700"
                  style={{ width: `${Math.min(s.pct, 100)}%` }}
                />
              </div>
            </div>

            {/* Province Table */}
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <div className="px-3 py-2 bg-gray-50 border-b border-gray-200 flex items-center justify-between gap-2 flex-wrap">
                <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wider flex items-center gap-1.5">
                  🏛 รายจังหวัด ({filteredProvs.length})
                </h3>
                <div className="flex items-center gap-2">
                  <div className="relative">
                    <Search size={12} className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                      type="text"
                      value={search}
                      onChange={e => setSearch(e.target.value)}
                      placeholder="ค้นหาจังหวัด..."
                      className="pl-7 pr-2 py-1 text-xs border border-gray-200 rounded w-40 focus:outline-none focus:ring-1 focus:ring-blue-300"
                    />
                  </div>
                  <div className="flex gap-1.5 text-[10px]">
                    <span className="px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700">✅ ครบ</span>
                    <span className="px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">📂 มีข้อมูล</span>
                    <span className="px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">⏳ รอ</span>
                  </div>
                </div>
              </div>
              <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 z-10">
                    <tr className="text-[10px] text-gray-500 uppercase border-b border-gray-200 bg-gray-50">
                      <th className="px-3 py-1.5 text-left w-8">#</th>
                      <SortTh col="name" current={sortCol} asc={sortAsc} onClick={toggleSort} align="left">จังหวัด</SortTh>
                      <SortTh col="status" current={sortCol} asc={sortAsc} onClick={toggleSort} align="center">สถานะ</SortTh>
                      <SortTh col="actual" current={sortCol} asc={sortAsc} onClick={toggleSort} align="right">PDF บน Drive</SortTh>
                      <SortTh col="expected" current={sortCol} asc={sortAsc} onClick={toggleSort} align="right">คาดหวัง</SortTh>
                      <SortTh col="pct" current={sortCol} asc={sortAsc} onClick={toggleSort} align="center" className="w-52">ความคืบหน้า</SortTh>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredProvs.map((p, i) => {
                      const actual = p.actual || 0
                      const exp = p.expected || 0

                      let badge
                      if (p.complete) {
                        badge = <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-emerald-100 text-emerald-700 border border-emerald-200">✅ ครบ</span>
                      } else if (actual > 0) {
                        badge = <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-blue-100 text-blue-700 border border-blue-200">📂 มีข้อมูล</span>
                      } else {
                        badge = <span className="text-gray-400 text-[10px]">⏳ รอ</span>
                      }

                      const barPct = Math.min(p.pct || 0, 100)
                      const barColor = p.complete ? 'bg-emerald-500' : 'bg-blue-500'

                      return (
                        <tr key={p.name} className={`border-b border-gray-100 hover:bg-gray-50 ${actual === 0 ? 'opacity-40' : ''}`}>
                          <td className="px-3 py-1.5 text-gray-400 font-mono">{i + 1}</td>
                          <td className={`px-3 py-1.5 font-semibold ${actual > 0 ? 'text-gray-900' : 'text-gray-400'}`}>{p.name}</td>
                          <td className="px-3 py-1.5 text-center">{badge}</td>
                          <td className={`px-3 py-1.5 text-right font-mono ${actual > 0 ? 'text-gray-700' : 'text-gray-300'}`}>{actual > 0 ? fmt(actual) : '—'}</td>
                          <td className="px-3 py-1.5 text-right font-mono text-gray-400">{exp > 0 ? fmt(exp) : '—'}</td>
                          <td className="px-3 py-1.5 text-center">
                            {actual > 0 && exp > 0 ? (
                              <div className="flex items-center gap-2 justify-center">
                                <div className="w-20 bg-gray-200 rounded-full h-1.5">
                                  <div className={`${barColor} h-1.5 rounded-full transition-all`} style={{ width: `${barPct}%` }} />
                                </div>
                                <span className={`text-[10px] font-mono font-semibold ${p.complete ? 'text-emerald-700' : 'text-blue-700'}`}>
                                  {fmt(actual)}/{fmt(exp)} ({p.pct}%)
                                </span>
                              </div>
                            ) : actual > 0 ? (
                              <span className="text-gray-600 text-[10px] font-mono">{fmt(actual)} PDFs</span>
                            ) : (
                              <span className="text-gray-300">—</span>
                            )}
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
      </div>
    </div>
  )
}

export default function BackupDashboard(props) {
  return (
    <ErrorBoundary compact>
      <BackupDashboardInner {...props} />
    </ErrorBoundary>
  )
}

function SortTh({ col, current, asc, onClick, align = 'left', className = '', children }) {
  const active = current === col
  return (
    <th
      className={`px-3 py-1.5 text-${align} cursor-pointer select-none hover:text-gray-700 transition ${className}`}
      onClick={() => onClick(col)}
    >
      <span className="inline-flex items-center gap-0.5">
        {children}
        {active ? (asc ? <ArrowUp size={10} /> : <ArrowDown size={10} />) : <ArrowUpDown size={9} className="opacity-30" />}
      </span>
    </th>
  )
}

function SummaryCard({ icon, label, value, sub, valueColor = 'text-gray-900' }) {
  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
      <div className="text-[10px] text-gray-500 uppercase tracking-wide font-semibold">{icon} {label}</div>
      <div className={`text-2xl font-bold mt-1 ${valueColor}`}>{value}</div>
      {sub && <div className="text-[10px] text-gray-400 mt-0.5">{sub}</div>}
    </div>
  )
}
