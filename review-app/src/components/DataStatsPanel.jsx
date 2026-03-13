import React, { useMemo, useState } from 'react'
import { ChevronDown, ChevronRight, BarChart3, AlertTriangle } from 'lucide-react'

export default function DataStatsPanel({ allItems, review }) {
  const [expanded, setExpanded] = useState(false)

  const provStats = useMemo(() => {
    const map = {}
    allItems.forEach(d => {
      const p = d.province || 'ไม่ระบุ'
      if (!map[p]) map[p] = {
        total: 0, constituency: 0, partyList: 0, other: 0,
        withCands: 0, flagged: 0, reviewed: 0,
        visionOcr: 0, noBallotData: 0, candMismatch: 0, noStationNo: 0,
        bkStations: new Set(), bnStations: new Set(), byZone: {}
      }
      const s = map[p]
      s.total++
      const stnKey = `${d.constituency || '?'}_${d.ocr_station_no || d.station_no || '?'}`
      if (d.vote_type === 'แบ่งเขต') { s.constituency++; if (d.ocr_station_no) s.bkStations.add(stnKey) }
      else if (d.vote_type === 'บัญชีรายชื่อ') { s.partyList++; if (d.ocr_station_no) s.bnStations.add(stnKey) }
      else s.other++
      if ((d.candidates || []).length > 0) s.withCands++
      if (d._candidate_mismatch || d._flag_incomplete_candidates) s.flagged++
      if (d._source_type === 'vision') s.visionOcr++
      if (d._candidate_mismatch) s.candMismatch++
      if (!d.ocr_station_no && !d.station_no) s.noStationNo++
      const hasBallot = ['registered_voters', 'turnout', 'ballots_received', 'valid_ballots', 'invalid_ballots', 'remaining_ballots']
        .some(f => d[f] != null)
      if (!hasBallot) s.noBallotData++
      const rev = review[d.id]
      if (rev && rev.status && rev.status !== 'pending') s.reviewed++
      // Zone breakdown
      const z = d.constituency || '?'
      if (!map[p].byZone[z]) map[p].byZone[z] = { total: 0, constituency: 0, partyList: 0, bkStations: new Set(), bnStations: new Set() }
      map[p].byZone[z].total++
      if (d.vote_type === 'แบ่งเขต') {
        map[p].byZone[z].constituency++
        if (d.ocr_station_no) map[p].byZone[z].bkStations.add(d.ocr_station_no)
      } else if (d.vote_type === 'บัญชีรายชื่อ') {
        map[p].byZone[z].partyList++
        if (d.ocr_station_no) map[p].byZone[z].bnStations.add(d.ocr_station_no)
      }
    })
    return map
  }, [allItems, review])

  // Global data quality issues
  const qualityIssues = useMemo(() => {
    const issues = []
    const totals = { vision: 0, noBallot: 0, mismatch: 0, noStation: 0 }
    Object.values(provStats).forEach(s => {
      totals.vision += s.visionOcr
      totals.noBallot += s.noBallotData
      totals.mismatch += s.candMismatch
      totals.noStation += s.noStationNo
    })
    if (totals.vision > 0) issues.push({ icon: '👁', text: `${totals.vision} หน้าใช้ Vision OCR (คุณภาพต่ำกว่า Gemini) — ควรตรวจละเอียด`, severity: 'warn' })
    if (totals.noBallot > 0) issues.push({ icon: '📭', text: `${totals.noBallot} หน้าไม่มีข้อมูลตัวเลข (บัตร/คะแนน) — OCR อาจอ่านไม่ออก`, severity: 'warn' })
    if (totals.mismatch > 0) issues.push({ icon: '⚠', text: `${totals.mismatch} หน้าผู้สมัครไม่ตรง กกต. — อาจมีแถวผีหรืออ่านผิด`, severity: 'warn' })
    if (totals.noStation > 0) issues.push({ icon: '📍', text: `${totals.noStation} หน้าไม่ทราบหมายเลขหน่วย — จับคู่ข้ามไฟล์ยาก`, severity: 'info' })
    return issues
  }, [provStats])

  if (allItems.length === 0) return null

  return (
    <div className="bg-white border-b">
      <div className="max-w-[1400px] mx-auto px-4">
        <button
          onClick={() => setExpanded(v => !v)}
          className="w-full flex items-center gap-2 py-2.5 text-sm font-semibold text-indigo-700 hover:text-indigo-900 transition"
        >
          <BarChart3 size={16} />
          สถิติข้อมูล
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          <span className="text-xs font-normal text-gray-400 ml-2">{allItems.length.toLocaleString()} รายการ</span>
          {qualityIssues.length > 0 && !expanded && (
            <span className="ml-auto flex items-center gap-1 text-xs font-normal text-amber-600">
              <AlertTriangle size={12} />
              {qualityIssues.length} ข้อสังเกต
            </span>
          )}
        </button>

        {expanded && (
          <div className="pb-4">
            {/* Data Quality Warnings */}
            {qualityIssues.length > 0 && (
              <div className="mb-4 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3">
                <h4 className="text-xs font-bold text-amber-800 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <AlertTriangle size={13} />
                  คุณภาพข้อมูล
                </h4>
                <ul className="space-y-1">
                  {qualityIssues.map((issue, i) => (
                    <li key={i} className="text-xs text-amber-700 flex items-start gap-1.5">
                      <span className="flex-shrink-0">{issue.icon}</span>
                      <span>{issue.text}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {Object.entries(provStats).sort((a, b) => a[0].localeCompare(b[0])).map(([prov, s]) => {
              const reviewPct = s.total > 0 ? Math.round(s.reviewed / s.total * 100) : 0
              const flagPct = s.total > 0 ? Math.round(s.flagged / s.total * 100) : 0
              return (
                <div key={prov} className="mb-4">
                  <h4 className="text-sm font-bold text-gray-800 mb-2">{prov}</h4>

                  {/* Stat cards */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2 mb-3">
                    <StatCard label="รวม (หน้า)" value={s.total} />
                    <StatCard label="แบ่งเขต" value={`${s.constituency} (${s.bkStations.size} หน่วย)`} />
                    <StatCard label="บัญชีรายชื่อ" value={`${s.partyList} (${s.bnStations.size} หน่วย)`} />
                    <StatCard label="มีผู้สมัคร" value={s.withCands} />
                    <StatCard label="ตรวจแล้ว" value={`${s.reviewed} (${reviewPct}%)`} color={reviewPct > 50 ? 'green' : reviewPct > 0 ? 'amber' : 'gray'} />
                    <StatCard label="มีปัญหา" value={`${s.flagged} (${flagPct}%)`} color={flagPct > 20 ? 'red' : flagPct > 10 ? 'amber' : 'gray'} />
                    {s.visionOcr > 0 && <StatCard label="Vision OCR" value={s.visionOcr} color="amber" />}
                    {s.noBallotData > 0 && <StatCard label="ไม่มีตัวเลข" value={s.noBallotData} color="red" />}
                  </div>

                  {/* Zone table */}
                  {(() => {
                    const zones = Object.entries(s.byZone)
                      .filter(([z]) => z !== '?')
                      .sort((a, b) => Number(a[0]) - Number(b[0]))
                    if (zones.length === 0) return null
                    return (
                      <table className="w-full text-xs border-collapse">
                        <thead>
                          <tr className="bg-gray-50 text-gray-500">
                            <th className="text-left px-3 py-1.5 font-semibold">เขต</th>
                            <th className="text-right px-3 py-1.5 font-semibold">รวม</th>
                            <th className="text-right px-3 py-1.5 font-semibold">แบ่งเขต (หน้า)</th>
                            <th className="text-right px-3 py-1.5 font-semibold">หน่วย แบ่งเขต</th>
                            <th className="text-right px-3 py-1.5 font-semibold">บัญชีฯ (หน้า)</th>
                            <th className="text-right px-3 py-1.5 font-semibold">หน่วย บัญชีฯ</th>
                          </tr>
                        </thead>
                        <tbody>
                          {zones.map(([z, zs]) => (
                            <tr key={z} className="border-t border-gray-100 hover:bg-gray-50">
                              <td className="px-3 py-1.5">เขต {z}</td>
                              <td className="text-right px-3 py-1.5">{zs.total}</td>
                              <td className="text-right px-3 py-1.5">{zs.constituency}</td>
                              <td className="text-right px-3 py-1.5 font-medium text-indigo-700">{zs.bkStations.size}</td>
                              <td className="text-right px-3 py-1.5">{zs.partyList}</td>
                              <td className="text-right px-3 py-1.5 font-medium text-indigo-700">{zs.bnStations.size}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )
                  })()}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value, color = 'indigo' }) {
  const colorMap = {
    indigo: 'text-indigo-700',
    green: 'text-green-700',
    amber: 'text-amber-600',
    red: 'text-red-600',
    gray: 'text-gray-500',
  }
  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-center">
      <div className={`text-lg font-bold ${colorMap[color] || colorMap.indigo}`}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </div>
      <div className="text-[11px] text-gray-500 mt-0.5">{label}</div>
    </div>
  )
}
