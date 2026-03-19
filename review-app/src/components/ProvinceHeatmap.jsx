import React, { useState, useMemo } from 'react'
import { Map, ChevronDown, ChevronRight } from 'lucide-react'
import ErrorBoundary from './ErrorBoundary'

// Thailand provinces arranged in rough geographic grid layout
// Each row represents a latitude band, columns represent longitude
const GRID = [
  // North
  [null, null, 'เชียงราย', 'เชียงราย', null, null, null],
  [null, 'เชียงใหม่', 'เชียงใหม่', 'พะเยา', 'น่าน', null, null],
  ['แม่ฮ่องสอน', 'เชียงใหม่', 'ลำพูน', 'ลำปาง', 'แพร่', 'อุตรดิตถ์', null],
  [null, null, null, 'สุโขทัย', 'พิษณุโลก', 'เลย', null],
  ['ตาก', 'ตาก', 'กำแพงเพชร', 'พิจิตร', 'เพชรบูรณ์', 'เลย', 'หนองคาย'],
  // Central / Northeast
  [null, 'นครสวรรค์', 'อุทัยธานี', 'ลพบุรี', 'ชัยภูมิ', 'ขอนแก่น', 'อุดรธานี'],
  [null, 'ชัยนาท', 'สิงห์บุรี', 'สระบุรี', 'นครราชสีมา', 'มหาสารคาม', 'กาฬสินธุ์'],
  ['กาญจนบุรี', 'สุพรรณบุรี', 'อ่างทอง', 'อยุธยา', 'นครราชสีมา', 'บุรีรัมย์', 'ร้อยเอ็ด'],
  ['กาญจนบุรี', 'นครปฐม', 'กรุงเทพ', 'กรุงเทพ', 'ปราจีนบุรี', 'สุรินทร์', 'ศรีสะเกษ'],
  [null, 'ราชบุรี', 'สมุทรสาคร', 'สมุทรปราการ', 'ฉะเชิงเทรา', 'สระแก้ว', 'อุบลราชธานี'],
  // East / South approaches
  ['เพชรบุรี', 'สมุทรสงคราม', 'กรุงเทพ', 'ชลบุรี', 'ชลบุรี', 'ระยอง', 'จันทบุรี'],
  ['ประจวบคีรีขันธ์', null, null, null, null, 'จันทบุรี', 'ตราด'],
  // South
  ['ชุมพร', null, null, null, null, null, null],
  ['ระนอง', 'สุราษฎร์ธานี', 'นครศรีธรรมราช', null, null, null, null],
  ['พังงา', 'กระบี่', 'นครศรีธรรมราช', 'พัทลุง', 'สงขลา', null, null],
  ['ภูเก็ต', 'ตรัง', 'สตูล', 'ปัตตานี', 'ยะลา', 'นราธิวาส', null],
]

// Map short names for display
const SHORT_NAMES = {
  'กรุงเทพ': 'กทม.',
  'นครราชสีมา': 'โคราช',
  'นครศรีธรรมราช': 'นครศรี',
  'ประจวบคีรีขันธ์': 'ประจวบฯ',
  'สมุทรปราการ': 'สมุทร ป.',
  'สมุทรสาคร': 'สมุทร ส.',
  'สมุทรสงคราม': 'สมุทร ง.',
  'อุบลราชธานี': 'อุบล',
  'กาญจนบุรี': 'กาญจน์',
  'สุราษฎร์ธานี': 'สุราษฎร์',
}

function getColor(pct) {
  if (pct >= 100) return 'bg-emerald-500 text-white'
  if (pct >= 75) return 'bg-emerald-300 text-emerald-900'
  if (pct >= 50) return 'bg-amber-300 text-amber-900'
  if (pct >= 25) return 'bg-amber-200 text-amber-800'
  if (pct > 0) return 'bg-red-200 text-red-800'
  return 'bg-gray-100 text-gray-400'
}

function ProvinceHeatmapInner({ allItems, review }) {
  const [expanded, setExpanded] = useState(false)
  const [hoveredProv, setHoveredProv] = useState(null)

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

  // Unique provinces in grid
  const uniqueProvs = useMemo(() => {
    const s = new Set()
    GRID.forEach(row => row.forEach(cell => { if (cell) s.add(cell) }))
    return s
  }, [])

  // Provinces with data but not in grid
  const missingFromGrid = useMemo(() => {
    return Object.keys(provStats).filter(p => !uniqueProvs.has(p) && p !== 'ไม่ระบุ')
  }, [provStats, uniqueProvs])

  // Summary
  const totalProvs = Object.keys(provStats).length
  const completedProvs = Object.values(provStats).filter(p => p.pct >= 100).length
  const partialProvs = Object.values(provStats).filter(p => p.pct > 0 && p.pct < 100).length

  if (allItems.length === 0) return null

  // Track rendered provinces to avoid duplicate cells
  const rendered = new Set()

  return (
    <div className="max-w-[1400px] mx-auto px-4 mt-3">
      <button
        onClick={() => setExpanded(v => !v)}
        className="flex items-center gap-2 text-sm font-semibold text-gray-700 hover:text-indigo-700 transition mb-2"
      >
        {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        <Map size={16} className="text-emerald-500" />
        🗺️ Province Review Heatmap
        <span className="text-xs font-normal text-gray-400 ml-2">
          {completedProvs} ครบ / {partialProvs} บางส่วน / {totalProvs} จังหวัดมีข้อมูล
        </span>
      </button>

      {expanded && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          {/* Legend */}
          <div className="flex items-center gap-3 mb-4 text-[10px]">
            <span className="text-gray-500 font-semibold">สัญลักษณ์:</span>
            {[
              { label: 'ครบ 100%', cls: 'bg-emerald-500 text-white' },
              { label: '75%+', cls: 'bg-emerald-300' },
              { label: '50%+', cls: 'bg-amber-300' },
              { label: '25%+', cls: 'bg-amber-200' },
              { label: '<25%', cls: 'bg-red-200' },
              { label: 'ไม่มีข้อมูล', cls: 'bg-gray-100' },
            ].map((l, i) => (
              <span key={i} className={`px-2 py-0.5 rounded ${l.cls}`}>{l.label}</span>
            ))}
          </div>

          {/* Grid Map */}
          <div className="inline-block">
            {GRID.map((row, ri) => (
              <div key={ri} className="flex">
                {row.map((cell, ci) => {
                  if (!cell) return <div key={ci} className="w-16 h-10 m-0.5" />

                  // Skip duplicate cells (merged provinces)
                  const cellKey = `${ri}_${ci}_${cell}`
                  if (rendered.has(`${ri}_${cell}`) && GRID[ri][ci - 1] === cell) {
                    return <div key={ci} className="w-16 h-10 m-0.5" />
                  }
                  if (ri > 0 && GRID[ri - 1]?.[ci] === cell && rendered.has(`prev_${cell}_${ci}`)) {
                    return <div key={ci} className="w-16 h-10 m-0.5" />
                  }

                  rendered.add(`${ri}_${cell}`)
                  rendered.add(`prev_${cell}_${ci}`)

                  const stats = provStats[cell]
                  const pct = stats ? stats.pct : -1
                  const colorCls = pct >= 0 ? getColor(pct) : 'bg-gray-50 text-gray-300 border border-dashed border-gray-200'
                  const shortName = SHORT_NAMES[cell] || (cell.length > 5 ? cell.slice(0, 4) + '.' : cell)

                  return (
                    <div
                      key={ci}
                      className={`w-16 h-10 m-0.5 rounded flex flex-col items-center justify-center cursor-default transition-all hover:ring-2 hover:ring-indigo-400 hover:z-10 relative ${colorCls}`}
                      onMouseEnter={() => setHoveredProv(cell)}
                      onMouseLeave={() => setHoveredProv(null)}
                      title={stats ? `${cell}: ${stats.reviewed}/${stats.total} (${pct.toFixed(0)}%)` : `${cell}: ไม่มีข้อมูล`}
                    >
                      <span className="text-[9px] font-medium leading-tight truncate w-full text-center px-0.5">{shortName}</span>
                      {stats && <span className="text-[8px] opacity-75">{pct.toFixed(0)}%</span>}
                    </div>
                  )
                })}
              </div>
            ))}
          </div>

          {/* Hover detail */}
          {hoveredProv && provStats[hoveredProv] && (
            <div className="mt-3 p-3 bg-gray-50 rounded-lg inline-block text-xs">
              <span className="font-semibold text-gray-700">{hoveredProv}</span>
              <span className="text-gray-400 mx-2">|</span>
              <span className="text-emerald-600">✅ {provStats[hoveredProv].confirmed}</span>
              <span className="text-gray-300 mx-1">·</span>
              <span className="text-amber-600">🔄 {provStats[hoveredProv].flagged}</span>
              <span className="text-gray-300 mx-1">·</span>
              <span className="text-red-600">🚫 {provStats[hoveredProv].rejected}</span>
              <span className="text-gray-300 mx-1">·</span>
              <span className="text-gray-500">⏳ {provStats[hoveredProv].total - provStats[hoveredProv].reviewed}</span>
              <span className="text-gray-400 ml-2">({provStats[hoveredProv].pct.toFixed(1)}%)</span>
            </div>
          )}

          {/* Missing provinces (in data but not in grid) */}
          {missingFromGrid.length > 0 && (
            <div className="mt-3">
              <h4 className="text-[10px] text-gray-400 uppercase mb-1">จังหวัดอื่นที่มีข้อมูล:</h4>
              <div className="flex flex-wrap gap-1">
                {missingFromGrid.map(p => {
                  const s = provStats[p]
                  return (
                    <span key={p} className={`text-[9px] px-2 py-0.5 rounded ${getColor(s.pct)}`}>
                      {p} ({s.reviewed}/{s.total})
                    </span>
                  )
                })}
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
