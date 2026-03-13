import React from 'react'
import { Search } from 'lucide-react'

const STATUS_FILTERS = [
  { key: 'all', label: 'ทั้งหมด' },
  { key: 'pending', label: 'รอตรวจ' },
  { key: 'confirmed', label: '✅ ยืนยันแล้ว' },
  { key: 'flagged', label: '🔄 ตรวจอีกรอบ' },
  { key: 'rejected', label: '🚫 ใช้ไม่ได้' },
  { key: 'has_errors', label: '🔴 มีข้อผิดพลาด' },
  { key: 'has_warnings', label: '🟡 มีคำเตือน' },
  { key: 'low', label: '🔶 Low Confidence' },
  { key: 'no_data', label: 'ไม่พบค่า' },
  { key: 'with_candidates', label: '👤 มีผู้สมัคร' },
  { key: 'vision_ocr', label: '👁 Vision OCR' },
  { key: 'no_station', label: '📍 ไม่ทราบหน่วย' },
  { key: 'cand_mismatch', label: '⚠ ผู้สมัครไม่ตรง' },
]

const VOTE_TYPE_TABS = [
  { key: 'all', label: 'ทั้งหมด', icon: '📋', desc: null },
  { key: 'แบ่งเขต', label: 'แบ่งเขต', icon: '🗳️', desc: 'สส.5/16' },
  { key: 'บัญชีรายชื่อ', label: 'บัญชีรายชื่อ', icon: '📝', desc: 'สส.5/16(บช)' },
  { key: 'ประชามติ', label: 'ประชามติ', icon: '🗳️', desc: 'อ.ส.4/7' },
  { key: 'นอกเขต', label: 'นอกเขต', icon: '📮', desc: null },
]

export default function FilterBar({
  filterStatus, setFilterStatus,
  filterProvince, setFilterProvince,
  provinces,
  filterConstituency, setFilterConstituency,
  constituencies,
  filterVoteType, setFilterVoteType,
  voteTypeCounts = {},
  voteTypeStations = {},
  searchText, setSearchText,
}) {
  const totalCount = Object.values(voteTypeCounts).reduce((a, b) => a + b, 0)

  return (
    <div className="bg-white border-b sticky top-[52px] z-40">
      {/* Vote type tabs — prominent row */}
      <div className="max-w-[1400px] mx-auto px-4 pt-2.5 pb-1.5">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-gray-400 font-semibold uppercase tracking-wider mr-1">ประเภท</span>
          {VOTE_TYPE_TABS.map(tab => {
            const count = tab.key === 'all' ? totalCount : (voteTypeCounts[tab.key] || 0)
            if (tab.key !== 'all' && count === 0) return null
            const isActive = filterVoteType === tab.key
            return (
              <button
                key={tab.key}
                onClick={() => setFilterVoteType(tab.key)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-indigo-700 text-white shadow-md ring-2 ring-indigo-300'
                    : 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200'
                }`}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
                {tab.desc && <span className={`text-[10px] ${isActive ? 'opacity-80' : 'opacity-60'}`}>({tab.desc})</span>}
                <span className={`ml-0.5 px-1.5 py-0 rounded-full text-[11px] font-bold ${isActive ? 'bg-white/25' : 'bg-black/8'}`}>
                  {count.toLocaleString()}
                </span>
                {tab.key !== 'all' && (voteTypeStations[tab.key] || 0) > 0 && (
                  <span className={`text-[10px] ${isActive ? 'opacity-70' : 'opacity-50'}`}>
                    ({(voteTypeStations[tab.key] || 0).toLocaleString()} หน่วย)
                  </span>
                )}
              </button>
            )
          })}
        </div>
      </div>

      {/* Secondary filters row */}
      <div className="max-w-[1400px] mx-auto px-4 pb-2 flex items-center gap-3 flex-wrap">
        <select
          value={filterStatus}
          onChange={e => setFilterStatus(e.target.value)}
          className="px-3 py-1.5 border rounded text-sm bg-white"
        >
          {STATUS_FILTERS.map(f => (
            <option key={f.key} value={f.key}>{f.label}</option>
          ))}
        </select>

        <select
          value={filterProvince}
          onChange={e => setFilterProvince(e.target.value)}
          className="px-3 py-1.5 border rounded text-sm bg-white"
        >
          <option value="all">ทุกจังหวัด ({provinces.length})</option>
          {provinces.map(p => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>

        <select
          value={filterConstituency}
          onChange={e => setFilterConstituency(e.target.value)}
          className="px-3 py-1.5 border rounded text-sm bg-white"
        >
          <option value="all">ทุกเขต ({constituencies.length})</option>
          {constituencies.map(c => (
            <option key={c} value={String(c)}>เขต {c}</option>
          ))}
        </select>

        <div className="relative flex-1 min-w-[200px] max-w-[300px]">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            placeholder="ค้นหาชื่อไฟล์/ตำบล..."
            className="w-full pl-8 pr-3 py-1.5 border rounded text-sm"
          />
        </div>
      </div>
    </div>
  )
}
