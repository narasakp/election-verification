import React from 'react'
import { Search } from 'lucide-react'

const STATUS_FILTERS = [
  { key: 'all', label: 'ทั้งหมด' },
  { key: 'pending', label: 'รอ' },
  { key: 'confirmed', label: '✅ ยืนยัน' },
  { key: 'flagged', label: '🔄 ตรวจซ้ำ' },
  { key: 'rejected', label: '🚫 ไม่ได้' },
  { key: 'anomaly', label: '🚨 ผิดปกติ' },
  { key: 'anomaly_summary', label: '📊 ภาพรวม', desc: 'ลายเซ็น/ว่าง/คุณภาพ' },
  { key: 'has_errors', label: '🔴 ข้อผิดพลาด' },
  { key: 'has_warnings', label: '🟡 คำเตือน' },
  { key: 'low', label: '🔶 Low' },
  { key: 'no_data', label: 'ไม่มีค่า' },
  { key: 'with_candidates', label: '👤 ผู้สมัคร' },
  { key: 'vision_ocr', label: '👁 Vision' },
  { key: 'no_station', label: '📍 ไม่ทราบ' },
  { key: 'cand_mismatch', label: '⚠ ไม่ตรง' },
]

const VOTE_TYPE_TABS = [
  { key: 'แบ่งเขต', label: 'แบ่งเขต', icon: '🗳️', desc: 'สส.' },
  { key: 'บัญชีรายชื่อ', label: 'บัญชีรายชื่อ', icon: '📝', desc: 'บช.' },
  { key: 'ประชามติ', label: 'ประชามติ', icon: '🗳️', desc: 'อ.ส.' },
  { key: 'นอกเขต', label: 'นอกเขต', icon: '📮', desc: null },
  { key: 'all', label: 'ทั้งหมด', icon: '📋', desc: null },
]

export default React.memo(function FilterBar({
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
    <nav className="bg-white/95 backdrop-blur-sm border-b border-gray-200 sticky top-[48px] z-40 shadow-sm" aria-label="ตัวกรองข้อมูล">
      {/* Vote type tabs — prominent row */}
      <div className="max-w-[1440px] mx-auto px-4 py-2">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[11px] text-gray-500 font-semibold uppercase tracking-wider" id="vote-type-label">ประเภท</span>
          {VOTE_TYPE_TABS.map(tab => {
            const count = tab.key === 'all' ? totalCount : (voteTypeCounts[tab.key] || 0)
            if (tab.key !== 'all' && count === 0) return null
            const isActive = filterVoteType === tab.key
            return (
              <button
                key={tab.key}
                onClick={() => setFilterVoteType(tab.key)}
                aria-pressed={isActive}
                aria-label={`${tab.label} (${count.toLocaleString()} รายการ)`}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
                  isActive
                    ? 'bg-indigo-700 text-white shadow-md ring-2 ring-indigo-300'
                    : 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200'
                }`}
              >
                <span className="text-sm">{tab.icon}</span>
                <span>{tab.label}</span>
                {tab.desc && <span className={`text-[9px] ${isActive ? 'opacity-80' : 'opacity-60'}`}>({tab.desc})</span>}
                <span className={`px-1 py-0 rounded text-[10px] font-bold ${isActive ? 'bg-white/25' : 'bg-black/8'}`}>
                  {count.toLocaleString()}
                </span>
                {tab.key !== 'all' && (voteTypeStations[tab.key] || 0) > 0 && (
                  <span className={`text-[8px] ${isActive ? 'opacity-70' : 'opacity-50'}`}>
                    {(voteTypeStations[tab.key] || 0).toLocaleString()}หน่วย
                  </span>
                )}
              </button>
            )
          })}
        </div>
      </div>

      {/* Secondary filters row */}
      <div className="max-w-[1440px] mx-auto px-4 py-2 flex items-center gap-2 flex-wrap">
        <select
          value={filterStatus}
          onChange={e => setFilterStatus(e.target.value)}
          className="px-2 py-1 border rounded text-xs bg-white"
          aria-label="กรองตามสถานะ"
        >
          {STATUS_FILTERS.map(f => (
            <option key={f.key} value={f.key}>{f.label}</option>
          ))}
        </select>

        <select
          value={filterProvince}
          onChange={e => setFilterProvince(e.target.value)}
          className="px-2 py-1 border rounded text-xs bg-white"
          aria-label="กรองตามจังหวัด"
        >
          <option value="all">จังหวัด ({provinces.length})</option>
          {provinces.map(p => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>

        <select
          value={filterConstituency}
          onChange={e => setFilterConstituency(e.target.value)}
          className="px-2 py-1 border rounded text-xs bg-white"
          aria-label="กรองตามเขตเลือกตั้ง"
        >
          <option value="all">เขต ({constituencies.length})</option>
          {constituencies.map(c => (
            <option key={c} value={String(c)}>เขต {c}</option>
          ))}
        </select>

        <div className="relative flex-1 min-w-[180px]">
          <Search size={12} className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="search"
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            placeholder="ค้นหาไฟล์..."
            className="w-full pl-6 pr-2 py-1 border rounded text-xs"
            aria-label="ค้นหาชื่อไฟล์หรือตำบล"
          />
        </div>
      </div>
    </nav>
  )
})
