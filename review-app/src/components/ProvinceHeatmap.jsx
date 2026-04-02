import React, { useState, useMemo } from 'react'
import { Map, ChevronDown, ChevronRight } from 'lucide-react'
import ErrorBoundary from './ErrorBoundary'
import useThailandMap, { SHORT_NAMES, MAP_WIDTH, MAP_HEIGHT } from '../hooks/useThailandMap'

// ProvinceHeatmap uses 'กรุงเทพ' (short) instead of 'กรุงเทพมหานคร' and 'อยุธยา' instead of 'พระนครศรีอยุธยา'
const HEATMAP_ALIAS = {
  'Bangkok Metropolis': 'กรุงเทพ',
  'Phra Nakhon Si Ayutthaya': 'อยุธยา',
}

// Fill color based on review percentage — more vivid & distinct
// pct < 0 = no data at all, pct === 0 = has data but nothing reviewed
function getFillColor(pct) {
  if (pct < 0) return '#e5e7eb'        // gray-200 — no data at all
  if (pct >= 100) return '#059669'     // emerald-600 — complete
  if (pct >= 75) return '#34d399'      // emerald-400
  if (pct >= 50) return '#facc15'      // yellow-400
  if (pct >= 25) return '#fb923c'      // orange-400
  if (pct > 0) return '#f87171'        // red-400 — started
  return '#c7d2fe'                     // indigo-200 — has data, 0% reviewed
}

function getStrokeColor(pct) {
  if (pct < 0) return '#9ca3af'
  if (pct >= 100) return '#047857'
  if (pct >= 75) return '#059669'
  if (pct >= 50) return '#ca8a04'
  if (pct >= 25) return '#ea580c'
  if (pct > 0) return '#dc2626'
  return '#6366f1'                     // indigo-500
}

// Text color that contrasts with fill
function getLabelColor(pct) {
  if (pct < 0) return '#6b7280'
  if (pct >= 100) return '#ffffff'
  if (pct >= 75) return '#064e3b'
  if (pct >= 50) return '#713f12'
  if (pct >= 25) return '#7c2d12'
  if (pct > 0) return '#7f1d1d'
  return '#3730a3'                     // indigo-800
}

function ProvinceHeatmapInner({ allItems, review }) {
  const [expanded, setExpanded] = useState(true)

  const {
    geoFeatures, pathGen, loadError, resolveThaiName,
    svgRef, hoveredProv, setHoveredProv, mousePos, handleMouseMove,
  } = useThailandMap({ enabled: expanded, aliasMap: HEATMAP_ALIAS })

  // Per-province stats
  const provStats = useMemo(() => {
    const map = {}
    allItems.forEach(item => {
      const prov = item.province || 'ไม่ระบุ'
      if (!map[prov]) map[prov] = { total: 0, reviewed: 0, confirmed: 0, flagged: 0, rejected: 0 }
      map[prov].total++
      const st = (review[item.id] || {}).status || 'pending'
      if (st !== 'pending') map[prov].reviewed++
      if (st === 'confirmed') map[prov].confirmed++
      if (st === 'flagged') map[prov].flagged++
      if (st === 'rejected') map[prov].rejected++
    })
    for (const v of Object.values(map)) {
      v.pct = v.total > 0 ? (v.reviewed / v.total * 100) : 0
    }
    return map
  }, [allItems, review])

  // Summary
  const totalProvs = Object.keys(provStats).length
  const completedProvs = Object.values(provStats).filter(p => p.pct >= 100).length
  const partialProvs = Object.values(provStats).filter(p => p.pct > 0 && p.pct < 100).length

  if (allItems.length === 0) return null

  const hoveredStats = hoveredProv ? provStats[hoveredProv] : null

  return (
    <div>
      <button
        onClick={() => setExpanded(v => !v)}
        className="w-full flex items-center gap-2.5 py-3 text-sm font-semibold text-gray-700 hover:text-indigo-700 transition group"
      >
        <span className="w-7 h-7 rounded-lg bg-emerald-50 flex items-center justify-center group-hover:bg-emerald-100 transition">
          <Map size={15} className="text-emerald-500" />
        </span>
        Province Review Heatmap
        {expanded ? <ChevronDown size={14} className="text-gray-400" /> : <ChevronRight size={14} className="text-gray-400" />}
        <span className="text-xs font-normal text-gray-400">
          {completedProvs} ครบ / {partialProvs} บางส่วน / {totalProvs} จังหวัดมีข้อมูล
        </span>
      </button>

      {expanded && (
        <div className="pb-5">
          {loadError && (
            <div className="text-xs text-red-500 p-3 bg-red-50 rounded-lg mb-3">
              โหลดแผนที่ไม่สำเร็จ: {loadError}
            </div>
          )}

          {!geoFeatures && !loadError && (
            <div className="flex items-center gap-2 p-4 text-xs text-gray-400">
              <div className="w-4 h-4 border-2 border-indigo-300 border-t-transparent rounded-full animate-spin" />
              กำลังโหลดแผนที่...
            </div>
          )}

          {geoFeatures && pathGen && (
            <div className="space-y-4">
              {/* SVG Map */}
              <div className="relative flex-shrink-0">
                <svg
                  ref={svgRef}
                  viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`}
                  className="w-full h-auto"
                  style={{ filter: 'drop-shadow(0 4px 16px rgba(0,0,0,0.10))' }}
                  onMouseMove={handleMouseMove}
                  onMouseLeave={() => setHoveredProv(null)}
                >
                  {/* Background */}
                  <rect width={MAP_WIDTH} height={MAP_HEIGHT} fill="#f0f4f8" rx="24" />

                  {/* Province paths */}
                  {geoFeatures.features.map((feat, i) => {
                    const thName = resolveThaiName(feat.properties.NAME_1)
                    const stats = provStats[thName]
                    const pct = stats ? stats.pct : -1
                    const isHovered = hoveredProv === thName
                    const fill = getFillColor(pct)
                    const stroke = getStrokeColor(pct)

                    return (
                      <path
                        key={feat.properties.ID_1 || i}
                        d={pathGen(feat)}
                        fill={isHovered ? (pct >= 0 ? '#818cf8' : '#c7d2fe') : fill}
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
                    const stats = provStats[thName]
                    const pct = stats ? stats.pct : -1
                    const centroid = pathGen.centroid(feat)
                    if (!centroid || isNaN(centroid[0])) return null
                    const [cx, cy] = centroid
                    const displayName = SHORT_NAMES[thName] || thName
                    const isHovered = hoveredProv === thName
                    const textColor = isHovered ? '#312e81' : getLabelColor(pct)

                    return (
                      <g
                        key={`label-${feat.properties.ID_1 || i}`}
                        onMouseEnter={() => setHoveredProv(thName)}
                        className="cursor-pointer"
                        style={{ pointerEvents: 'none' }}
                      >
                        {/* Province name */}
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
                        {/* Stats line */}
                        {stats && (
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
                            {stats.reviewed}/{stats.total} ({pct.toFixed(0)}%)
                          </text>
                        )}
                        {!stats && (
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

                  {/* Title watermark */}
                  <text x="24" y={MAP_HEIGHT - 16} fontSize="18" fill="#94a3b8" fontFamily="sans-serif">
                    แผนที่ตรวจสอบจังหวัด — Election Verification
                  </text>
                </svg>

                {/* Floating tooltip */}
                {hoveredProv && (
                  <div
                    className="absolute pointer-events-none z-50 bg-white/95 backdrop-blur-sm border border-indigo-200 rounded-xl shadow-xl px-4 py-3 text-xs min-w-[200px]"
                    style={{
                      left: mousePos.x + 16,
                      top: mousePos.y - 12,
                      transform: 'translateY(-100%)',
                    }}
                  >
                    <div className="font-bold text-sm text-gray-800 mb-1.5 flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: hoveredStats ? getFillColor(hoveredStats.pct) : '#e5e7eb' }} />
                      {hoveredProv}
                    </div>
                    {hoveredStats ? (
                      <>
                        <div className="flex items-center gap-1 mb-1.5">
                          <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all duration-300"
                              style={{
                                width: `${hoveredStats.pct}%`,
                                backgroundColor: getFillColor(hoveredStats.pct),
                              }}
                            />
                          </div>
                          <span className="font-semibold text-gray-600 ml-1">{hoveredStats.pct.toFixed(1)}%</span>
                        </div>
                        <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[11px]">
                          <span className="text-gray-400">ทั้งหมด</span>
                          <span className="font-medium text-gray-700 text-right">{hoveredStats.total}</span>
                          <span className="text-emerald-500">✅ ยืนยัน</span>
                          <span className="font-medium text-emerald-700 text-right">{hoveredStats.confirmed}</span>
                          <span className="text-amber-500">🔄 ตรวจอีก</span>
                          <span className="font-medium text-amber-700 text-right">{hoveredStats.flagged}</span>
                          <span className="text-red-500">🚫 ใช้ไม่ได้</span>
                          <span className="font-medium text-red-700 text-right">{hoveredStats.rejected}</span>
                          <span className="text-gray-400">⏳ รอตรวจ</span>
                          <span className="font-medium text-gray-500 text-right">{hoveredStats.total - hoveredStats.reviewed}</span>
                        </div>
                      </>
                    ) : (
                      <span className="text-gray-400">ไม่มีข้อมูล</span>
                    )}
                  </div>
                )}
              </div>

              {/* Bottom panel: Legend + Summary + Province list */}
              <div className="flex flex-col lg:flex-row gap-4">
                {/* Legend */}
                <div className="bg-white border border-gray-100 rounded-xl p-4 shadow-sm">
                  <h4 className="text-xs font-bold text-gray-600 uppercase tracking-wider mb-3">สัญลักษณ์</h4>
                  <div className="space-y-1.5">
                    {[
                      { label: 'ครบ 100%', color: '#059669' },
                      { label: '75–99%', color: '#34d399' },
                      { label: '50–74%', color: '#facc15' },
                      { label: '25–49%', color: '#fb923c' },
                      { label: '1–24%', color: '#f87171' },
                      { label: 'รอตรวจ 0%', color: '#c7d2fe' },
                      { label: 'ไม่มีข้อมูล', color: '#e5e7eb' },
                    ].map((l, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs">
                        <span className="w-4 h-4 rounded" style={{ backgroundColor: l.color, border: '1px solid rgba(0,0,0,0.1)' }} />
                        <span className="text-gray-600">{l.label}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Summary stats */}
                <div className="bg-white border border-gray-100 rounded-xl p-4 shadow-sm">
                  <h4 className="text-xs font-bold text-gray-600 uppercase tracking-wider mb-3">สรุป</h4>
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="bg-emerald-50 rounded-lg py-2 px-1">
                      <div className="text-lg font-bold text-emerald-600">{completedProvs}</div>
                      <div className="text-[10px] text-emerald-500">ครบ 100%</div>
                    </div>
                    <div className="bg-amber-50 rounded-lg py-2 px-1">
                      <div className="text-lg font-bold text-amber-600">{partialProvs}</div>
                      <div className="text-[10px] text-amber-500">บางส่วน</div>
                    </div>
                    <div className="bg-gray-50 rounded-lg py-2 px-1">
                      <div className="text-lg font-bold text-gray-600">{totalProvs}</div>
                      <div className="text-[10px] text-gray-400">มีข้อมูล</div>
                    </div>
                  </div>
                </div>

                {/* Province list sorted by completion */}
                <div className="bg-white border border-gray-100 rounded-xl p-4 shadow-sm max-h-[500px] overflow-y-auto flex-1">
                  <h4 className="text-xs font-bold text-gray-600 uppercase tracking-wider mb-3">รายจังหวัด</h4>
                  <div className="space-y-1">
                    {Object.entries(provStats)
                      .filter(([name]) => name !== 'ไม่ระบุ')
                      .sort((a, b) => b[1].pct - a[1].pct)
                      .map(([name, stats]) => (
                        <div
                          key={name}
                          className={`flex items-center gap-2 text-xs py-1 px-2 rounded cursor-default transition-colors ${hoveredProv === name ? 'bg-indigo-50 ring-1 ring-indigo-200' : 'hover:bg-gray-50'}`}
                          onMouseEnter={() => setHoveredProv(name)}
                          onMouseLeave={() => setHoveredProv(null)}
                        >
                          <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: getFillColor(stats.pct) }} />
                          <span className="flex-1 truncate text-gray-700">{name}</span>
                          <span className="text-gray-400 text-[10px]">{stats.reviewed}/{stats.total}</span>
                          <span className="font-semibold text-gray-600 w-10 text-right">{stats.pct.toFixed(0)}%</span>
                        </div>
                      ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function ProvinceHeatmap(props) {
  return (
    <ErrorBoundary compact>
      <ProvinceHeatmapInner {...props} />
    </ErrorBoundary>
  )
}
