import React, { useState, useEffect, useMemo } from 'react'
import { HardDrive, CheckCircle2, FileText, ChevronDown, ChevronRight, Search, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import ErrorBoundary from './ErrorBoundary'
import useThailandMap, { SHORT_NAMES, MAP_WIDTH, MAP_HEIGHT } from '../hooks/useThailandMap'

const BACKUP_URL = './data/backup_status.json'
const DRIVE_URL = 'https://drive.google.com/drive/u/0/folders/14TWIziWEesoRiyii38yvVA5gVFC4joNm'


// Backup quality color: based on actual/expected pct
function getBackupFill(prov) {
  if (!prov) return '#e5e7eb'              // gray — no data
  const pct = prov.pct || 0
  if (prov.complete && pct >= 100) return '#059669'  // emerald-600 — complete
  if (pct >= 90) return '#34d399'          // emerald-400
  if (pct >= 75) return '#facc15'          // yellow-400
  if (pct >= 50) return '#fb923c'          // orange-400
  if (pct > 0) return '#f87171'            // red-400
  return '#c7d2fe'                         // indigo-200 — loaded but 0 actual
}

function getBackupStroke(prov) {
  if (!prov) return '#9ca3af'
  const pct = prov.pct || 0
  if (prov.complete && pct >= 100) return '#047857'
  if (pct >= 90) return '#059669'
  if (pct >= 75) return '#ca8a04'
  if (pct >= 50) return '#ea580c'
  if (pct > 0) return '#dc2626'
  return '#6366f1'
}

function getBackupLabelColor(prov) {
  if (!prov) return '#6b7280'
  const pct = prov.pct || 0
  if (prov.complete && pct >= 100) return '#ffffff'
  if (pct >= 90) return '#064e3b'
  if (pct >= 75) return '#713f12'
  if (pct >= 50) return '#7c2d12'
  if (pct > 0) return '#7f1d1d'
  return '#3730a3'
}

function fmt(n) {
  return n == null ? '—' : n.toLocaleString()
}

function BackupDashboardInner() {
  const [data, setData] = useState(null)
  const [expanded, setExpanded] = useState(true)
  const [search, setSearch] = useState('')
  const [sortCol, setSortCol] = useState('name')
  const [sortAsc, setSortAsc] = useState(true)

  const {
    geoFeatures, pathGen, resolveThaiName,
    svgRef, hoveredProv, setHoveredProv, mousePos, handleMouseMove,
  } = useThailandMap({ enabled: expanded })

  useEffect(() => {
    fetch(BACKUP_URL)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setData(d) })
      .catch(() => {})
  }, [])

  // Province lookup by Thai name
  const provMap = useMemo(() => {
    if (!data?.provinces) return {}
    const m = {}
    data.provinces.forEach(p => { m[p.name] = p })
    return m
  }, [data])

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
    <div>
        <button
          onClick={() => setExpanded(v => !v)}
          className="w-full flex items-center gap-2.5 py-3 text-sm font-semibold text-slate-700 hover:text-slate-900 transition group"
        >
          <span className="w-7 h-7 rounded-lg bg-blue-50 flex items-center justify-center group-hover:bg-blue-100 transition">
            <HardDrive size={15} className="text-blue-500" />
          </span>
          Backup ข้อมูล กกต. —{' '}
          <a
            href={DRIVE_URL}
            target="_blank"
            rel="noopener noreferrer"
            onClick={e => e.stopPropagation()}
            className="text-blue-500 hover:text-blue-700 hover:underline transition"
          >Google Drive</a>
          {expanded ? <ChevronDown size={14} className="text-gray-400" /> : <ChevronRight size={14} className="text-gray-400" />}
          <span className="text-xs font-normal text-gray-400">
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
                sub={s.pct > 100 ? `เกิน 100% เพราะบาง จ. มี PDF จริงมากกว่าที่คาดไว้ (${fmt(s.total_actual)}/${fmt(s.total_expected)})` : 'overall progress'}
                valueColor={s.pct >= 100 ? 'text-emerald-600' : 'text-blue-600'}
              />
            </div>

            {/* Overall Progress Bar */}
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-4">
              <div className="flex justify-between items-center mb-1.5">
                <span className="text-xs font-semibold text-gray-600">
                  📊 ความคืบหน้ารวม (ไฟล์จริงบน{' '}
                  <a href={DRIVE_URL} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:text-blue-700 hover:underline">Google Drive</a>)
                </span>
                <span className="text-xs text-gray-500 font-mono flex items-center gap-2">
                  {s.pct}%
                  {s.pct > 100 && (
                    <span className="inline-flex items-center gap-1 text-[11px] bg-amber-50 text-amber-700 border border-amber-200 rounded-md px-2 py-0.5 font-sans font-medium">
                      ⚠️ เกิน 100% — PDF จริง ({fmt(s.total_actual)}) มากกว่าที่คาดไว้ ({fmt(s.total_expected)})
                    </span>
                  )}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div
                  className="bg-gradient-to-r from-blue-500 to-emerald-500 h-2.5 rounded-full transition-all duration-700"
                  style={{ width: `${Math.min(s.pct, 100)}%` }}
                />
              </div>
            </div>

            {/* Thailand Map — Backup Data Quality */}
            {geoFeatures && pathGen && (
              <div className="mb-4 space-y-4">
                <div className="relative">
                  <svg
                    ref={svgRef}
                    viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`}
                    className="w-full h-auto"
                    style={{ filter: 'drop-shadow(0 4px 16px rgba(0,0,0,0.10))' }}
                    onMouseMove={handleMouseMove}
                    onMouseLeave={() => setHoveredProv(null)}
                  >
                    <rect width={MAP_WIDTH} height={MAP_HEIGHT} fill="#f0f4f8" rx="24" />

                    {/* Province paths */}
                    {geoFeatures.features.map((feat, i) => {
                      const thName = resolveThaiName(feat.properties.NAME_1)
                      const prov = provMap[thName]
                      const isHovered = hoveredProv === thName
                      const fill = getBackupFill(prov)
                      const stroke = getBackupStroke(prov)

                      return (
                        <path
                          key={feat.properties.ID_1 || i}
                          d={pathGen(feat)}
                          fill={isHovered ? (prov ? '#818cf8' : '#c7d2fe') : fill}
                          stroke={isHovered ? '#4338ca' : stroke}
                          strokeWidth={isHovered ? 3.5 : 1.2}
                          className="transition-colors duration-150 cursor-pointer"
                          onMouseEnter={() => setHoveredProv(thName)}
                          style={{ filter: isHovered ? 'brightness(1.1) drop-shadow(0 0 6px rgba(67,56,202,0.4))' : 'none' }}
                        />
                      )
                    })}

                    {/* Province labels on map */}
                    {geoFeatures.features.map((feat, i) => {
                      const thName = resolveThaiName(feat.properties.NAME_1)
                      const prov = provMap[thName]
                      const centroid = pathGen.centroid(feat)
                      if (!centroid || isNaN(centroid[0])) return null
                      const [cx, cy] = centroid
                      const displayName = SHORT_NAMES[thName] || thName
                      const isHovered = hoveredProv === thName
                      const textColor = isHovered ? '#312e81' : getBackupLabelColor(prov)

                      return (
                        <g key={`label-${feat.properties.ID_1 || i}`} style={{ pointerEvents: 'none' }}>
                          <text
                            x={cx} y={cy - 6}
                            textAnchor="middle"
                            fontSize={isHovered ? 16 : 13}
                            fontWeight={isHovered ? 800 : 600}
                            fill={textColor}
                            fontFamily="sans-serif"
                            style={{ textShadow: '0 1px 2px rgba(255,255,255,0.7)', transition: 'font-size 0.15s' }}
                          >
                            {displayName}
                          </text>
                          {prov ? (
                            <text
                              x={cx} y={cy + 12}
                              textAnchor="middle"
                              fontSize={isHovered ? 14 : 11}
                              fontWeight={500}
                              fill={textColor}
                              opacity={0.85}
                              fontFamily="sans-serif"
                              style={{ textShadow: '0 1px 2px rgba(255,255,255,0.7)' }}
                            >
                              {fmt(prov.actual)} PDF ({prov.pct}%)
                            </text>
                          ) : (
                            <text
                              x={cx} y={cy + 12}
                              textAnchor="middle"
                              fontSize={10}
                              fill="#9ca3af"
                              fontFamily="sans-serif"
                              opacity={0.7}
                            >
                              ไม่มีข้อมูล
                            </text>
                          )}
                        </g>
                      )
                    })}

                    <a href={DRIVE_URL} target="_blank" rel="noopener noreferrer">
                      <text x="24" y={MAP_HEIGHT - 16} fontSize="18" fill="#94a3b8" fontFamily="sans-serif" style={{ cursor: 'pointer' }}>
                        แผนที่คุณภาพข้อมูล Backup ข้อมูล กกต. — Google Drive ↗
                      </text>
                    </a>
                  </svg>

                  {/* Floating tooltip */}
                  {hoveredProv && (() => {
                    const hp = provMap[hoveredProv]
                    return (
                      <div
                        className="absolute pointer-events-none z-50 bg-white/95 backdrop-blur-sm border border-indigo-200 rounded-xl shadow-xl px-4 py-3 text-xs min-w-[220px]"
                        style={{
                          left: mousePos.x + 16,
                          top: mousePos.y - 12,
                          transform: 'translateY(-100%)',
                        }}
                      >
                        <div className="font-bold text-sm text-gray-800 mb-1.5 flex items-center gap-1.5">
                          <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: getBackupFill(hp) }} />
                          {hoveredProv}
                        </div>
                        {hp ? (
                          <>
                            <div className="flex items-center gap-1 mb-1.5">
                              <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                                <div
                                  className="h-full rounded-full transition-all duration-300"
                                  style={{
                                    width: `${Math.min(hp.pct || 0, 100)}%`,
                                    backgroundColor: getBackupFill(hp),
                                  }}
                                />
                              </div>
                              <span className="font-semibold text-gray-600 ml-1">{hp.pct}%</span>
                            </div>
                            <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[11px]">
                              <span className="text-gray-400">PDF บน Drive</span>
                              <span className="font-medium text-gray-700 text-right">{fmt(hp.actual)}</span>
                              <span className="text-gray-400">คาดหวัง</span>
                              <span className="font-medium text-gray-700 text-right">{fmt(hp.expected)}</span>
                              <span className="text-emerald-500">อัปโหลด</span>
                              <span className="font-medium text-emerald-700 text-right">{fmt(hp.uploaded)}</span>
                              {hp.skipped > 0 && <>
                                <span className="text-amber-500">ข้าม</span>
                                <span className="font-medium text-amber-700 text-right">{fmt(hp.skipped)}</span>
                              </>}
                              {hp.failed > 0 && <>
                                <span className="text-red-500">ล้มเหลว</span>
                                <span className="font-medium text-red-700 text-right">{fmt(hp.failed)}</span>
                              </>}
                              <span className="text-gray-400">สถานะ</span>
                              <span className={`font-medium text-right ${hp.complete ? 'text-emerald-600' : 'text-blue-600'}`}>
                                {hp.complete ? '✅ ครบ' : '📂 กำลังดำเนินการ'}
                              </span>
                            </div>
                          </>
                        ) : (
                          <span className="text-gray-400">ไม่มีข้อมูล</span>
                        )}
                      </div>
                    )
                  })()}
                </div>

                {/* Legend + Summary row */}
                <div className="flex flex-col lg:flex-row gap-4">
                  <div className="bg-white border border-gray-100 rounded-xl p-4 shadow-sm">
                    <h4 className="text-xs font-bold text-gray-600 uppercase tracking-wider mb-3">สัญลักษณ์</h4>
                    <div className="space-y-1.5">
                      {[
                        { label: 'ครบ 100%', color: '#059669' },
                        { label: '≥90%', color: '#34d399' },
                        { label: '75–89%', color: '#facc15' },
                        { label: '50–74%', color: '#fb923c' },
                        { label: '1–49%', color: '#f87171' },
                        { label: 'รอข้อมูล 0%', color: '#c7d2fe' },
                        { label: 'ไม่มีข้อมูล', color: '#e5e7eb' },
                      ].map((l, i) => (
                        <div key={i} className="flex items-center gap-2 text-xs">
                          <span className="w-4 h-4 rounded" style={{ backgroundColor: l.color, border: '1px solid rgba(0,0,0,0.1)' }} />
                          <span className="text-gray-600">{l.label}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="bg-white border border-gray-100 rounded-xl p-4 shadow-sm">
                    <h4 className="text-xs font-bold text-gray-600 uppercase tracking-wider mb-3">สรุป</h4>
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div className="bg-emerald-50 rounded-lg py-2 px-1">
                        <div className="text-lg font-bold text-emerald-600">{s.complete}</div>
                        <div className="text-[10px] text-emerald-500">ครบ 100%</div>
                      </div>
                      <div className="bg-blue-50 rounded-lg py-2 px-1">
                        <div className="text-lg font-bold text-blue-600">{s.has_data}</div>
                        <div className="text-[10px] text-blue-500">มีข้อมูล</div>
                      </div>
                      <div className="bg-gray-50 rounded-lg py-2 px-1">
                        <div className="text-lg font-bold text-gray-600">{s.total}</div>
                        <div className="text-[10px] text-gray-400">ทั้งหมด</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {!geoFeatures && expanded && (
              <div className="flex items-center gap-2 p-4 text-xs text-gray-400 mb-4">
                <div className="w-4 h-4 border-2 border-blue-300 border-t-transparent rounded-full animate-spin" />
                กำลังโหลดแผนที่...
              </div>
            )}

            {/* Province Table */}
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <div className="px-3 py-2 bg-gray-50 border-b border-gray-200 flex items-center justify-between gap-2 flex-wrap">
                <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wider flex items-center gap-1.5">
                  🏛 รายจังหวัด ({filteredProvs.length})
                  <a href={DRIVE_URL} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:text-blue-700 hover:underline font-normal normal-case tracking-normal ml-1">📂 Google Drive ↗</a>
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
                                <span className={`text-[10px] font-mono font-semibold ${p.pct > 100 ? 'text-amber-700' : p.complete ? 'text-emerald-700' : 'text-blue-700'}`}>
                                  {fmt(actual)}/{fmt(exp)}{p.pct > 100 ? ` ⚠️ (${p.pct}%)` : ` (${p.pct}%)`}
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
