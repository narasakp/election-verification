import React, { useMemo, useState } from 'react'
import { ChevronDown, ChevronRight, BarChart3, AlertTriangle, FileText, Info, ExternalLink } from 'lucide-react'

export default function DataStatsPanel({ allItems, review, anomalyFlags }) {
  const [expanded, setExpanded] = useState(false)

  const provStats = useMemo(() => {
    const map = {}
    allItems.forEach(d => {
      const p = d.province || 'ไม่ระบุ'
      if (!map[p]) map[p] = {
        total: 0, constituency: 0, partyList: 0, other: 0,
        withCands: 0, flagged: 0, reviewed: 0,
        visionOcr: 0, noBallotData: 0, candMismatch: 0, noStationNo: 0, multiPage: 0,
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
      if ((d.total_pages || 1) > 2) s.multiPage++
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

  // PDF document statistics
  const pdfStats = useMemo(() => {
    const multiPageItems = allItems.filter(d => (d.total_pages || 1) > 2)
    const singlePageItems = allItems.filter(d => (d.total_pages || 1) <= 2)
    let maxPages = 0
    let maxPageFile = ''
    // Group by pdf_url to find shared PDFs
    const pdfGroups = {}
    allItems.forEach(d => {
      const tp = d.total_pages || 1
      if (tp > maxPages) { maxPages = tp; maxPageFile = d.file || '' }
      const url = d.pdf_url || ''
      if (url) {
        if (!pdfGroups[url]) pdfGroups[url] = { count: 0, totalPages: tp }
        pdfGroups[url].count++
      }
    })
    // Find most shared PDF
    let maxShared = 0
    let maxSharedPages = 0
    Object.values(pdfGroups).forEach(g => {
      if (g.count > maxShared) { maxShared = g.count; maxSharedPages = g.totalPages }
    })
    const splitDone = singlePageItems.length
    const splitRemaining = multiPageItems.length
    return { multiPageItems: splitRemaining, singlePageItems: splitDone, maxPages, maxPageFile, maxShared, maxSharedPages, total: allItems.length }
  }, [allItems])

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
    if (pdfStats.multiPageItems > 0) issues.push({ icon: '📄', text: `${pdfStats.multiPageItems.toLocaleString()} รายการยัง PDF รวมหลายหน้า (กกต. รวมหลายหน่วยใน PDF เดียว สูงสุด ${pdfStats.maxPages} หน้า / ${pdfStats.maxShared} items) — กำลังตัดอัตโนมัติ`, severity: 'warn' })
    if (totals.vision > 0) issues.push({ icon: '👁', text: `${totals.vision} หน้าใช้ Vision OCR (คุณภาพต่ำกว่า Gemini) — ควรตรวจละเอียด`, severity: 'warn' })
    if (totals.noBallot > 0) issues.push({ icon: '📭', text: `${totals.noBallot} หน้าไม่มีข้อมูลตัวเลข (บัตร/คะแนน) — OCR อาจอ่านไม่ออก`, severity: 'warn' })
    if (totals.mismatch > 0) issues.push({ icon: '⚠', text: `${totals.mismatch} หน้าผู้สมัครไม่ตรง กกต. — อาจมีแถวผีหรืออ่านผิด`, severity: 'warn' })
    if (totals.noStation > 0) issues.push({ icon: '📍', text: `${totals.noStation} หน้าไม่ทราบหมายเลขหน่วย — จับคู่ข้ามไฟล์ยาก`, severity: 'info' })
    return issues
  }, [provStats, pdfStats])

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
            {/* PDF Document Info */}
            {pdfStats.multiPageItems > 0 && (
              <div className="mb-4 bg-blue-50 border border-blue-200 rounded-lg px-4 py-3">
                <h4 className="text-xs font-bold text-blue-800 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <FileText size={13} />
                  สถานะเอกสาร PDF
                </h4>
                <p className="text-xs text-blue-800 mb-2">
                  <strong>ปัญหา:</strong> กกต. รวมหลายหน่วยเลือกตั้งไว้ใน PDF เดียว (เช่น 14, 18 หรือสูงสุด {pdfStats.maxPages} หน้า)
                  แต่ OCR แต่ละรายการใช้เพียง 1–2 หน้า ทำให้ผู้ตรวจสอบต้องเลื่อนหาหน้าที่ถูกต้องเอง
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-2">
                  <div className="bg-white border border-blue-100 rounded px-2.5 py-1.5 text-center">
                    <div className="text-base font-bold text-green-700">{pdfStats.singlePageItems.toLocaleString()}</div>
                    <div className="text-[10px] text-gray-500">ตัดเป็นหน้าเดียวแล้ว</div>
                  </div>
                  <div className="bg-white border border-blue-100 rounded px-2.5 py-1.5 text-center">
                    <div className="text-base font-bold text-amber-600">{pdfStats.multiPageItems.toLocaleString()}</div>
                    <div className="text-[10px] text-gray-500">ยังรวมหลายหน้า (กำลังตัด)</div>
                  </div>
                  <div className="bg-white border border-blue-100 rounded px-2.5 py-1.5 text-center">
                    <div className="text-base font-bold text-red-600">{pdfStats.maxPages}</div>
                    <div className="text-[10px] text-gray-500">PDF ใหญ่สุด (หน้า)</div>
                  </div>
                  <div className="bg-white border border-blue-100 rounded px-2.5 py-1.5 text-center">
                    <div className="text-base font-bold text-indigo-700">{pdfStats.maxShared}</div>
                    <div className="text-[10px] text-gray-500">items ชี้ PDF เดียวกัน (สูงสุด)</div>
                  </div>
                </div>
                <div className="w-full bg-blue-100 rounded-full h-2 mb-1">
                  <div
                    className="bg-green-500 h-2 rounded-full transition-all"
                    style={{ width: `${Math.round(pdfStats.singlePageItems / pdfStats.total * 100)}%` }}
                  />
                </div>
                <p className="text-[10px] text-blue-600">
                  ตัดแล้ว {Math.round(pdfStats.singlePageItems / pdfStats.total * 100)}% — รายการที่เหลือกำลังตัดอัตโนมัติ อาจใช้เวลาหลายชั่วโมง
                </p>
              </div>
            )}

            {/* ECT Anomaly Analysis cross-reference */}
            {anomalyFlags && Object.keys(anomalyFlags).length > 0 && (() => {
              // Compute summary from flags
              const allFlags = Object.values(anomalyFlags).flat()
              const highCount = allFlags.filter(f => f.severity === 'high').length
              const categories = {}
              allFlags.forEach(f => { categories[f.category] = (categories[f.category] || 0) + 1 })
              const catLabels = { turnout: 'Turnout ผิดปกติ', invalid: 'บัตรเสียสูง', blank: 'ไม่ประสงค์ฯ สูง', wasted: 'คะแนนสูญเปล่า', dominance: 'ชนะขาดลอย' }
              // Which flagged constituencies overlap with our provinces?
              const ourProvs = new Set(allItems.map(d => d.province))
              const relevantFlags = Object.entries(anomalyFlags).filter(([key]) => {
                const prov = key.split('_')[0]
                return ourProvs.has(prov)
              })
              return (
                <div className="mb-4 bg-purple-50 border border-purple-200 rounded-lg px-4 py-3">
                  <h4 className="text-xs font-bold text-purple-800 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <span>🔬</span>
                    วิเคราะห์ความผิดปกติ — ข้อมูล กกต. ระดับเขต (400 เขตทั่วประเทศ)
                    <a href="https://narasakp.github.io/election-verification/anomaly.html" target="_blank" rel="noopener noreferrer"
                       className="ml-auto text-[11px] text-purple-600 hover:text-purple-800 underline flex items-center gap-0.5 font-medium normal-case">
                      <ExternalLink size={11} /> เปิดหน้าวิเคราะห์ฉบับเต็ม
                    </a>
                  </h4>
                  <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2 mb-2">
                    <div className="bg-white border border-purple-100 rounded px-2.5 py-1.5 text-center">
                      <div className="text-base font-bold text-purple-700">{Object.keys(anomalyFlags).length}</div>
                      <div className="text-[10px] text-gray-500">เขตที่ถูก flag</div>
                    </div>
                    {highCount > 0 && (
                      <div className="bg-white border border-red-100 rounded px-2.5 py-1.5 text-center">
                        <div className="text-base font-bold text-red-600">{highCount}</div>
                        <div className="text-[10px] text-gray-500">flag ระดับสูง</div>
                      </div>
                    )}
                    {Object.entries(categories).sort((a,b) => b[1]-a[1]).map(([cat, cnt]) => (
                      <div key={cat} className="bg-white border border-purple-100 rounded px-2.5 py-1.5 text-center">
                        <div className="text-base font-bold text-purple-700">{cnt}</div>
                        <div className="text-[10px] text-gray-500">{catLabels[cat] || cat}</div>
                      </div>
                    ))}
                  </div>
                  {relevantFlags.length > 0 && (
                    <div className="mt-2">
                      <p className="text-[11px] font-semibold text-purple-700 mb-1">เขตในข้อมูล OCR ที่ถูก flag:</p>
                      <div className="flex flex-wrap gap-1">
                        {relevantFlags.map(([key, flags]) => {
                          const [prov, con] = [key.substring(0, key.lastIndexOf('_')), key.substring(key.lastIndexOf('_') + 1)]
                          const hasHigh = flags.some(f => f.severity === 'high')
                          return (
                            <span key={key} className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium ${
                              hasHigh ? 'bg-red-100 text-red-800 border border-red-200' : 'bg-amber-100 text-amber-800 border border-amber-200'
                            }`}>
                              {hasHigh ? '🚨' : '⚠️'} {prov} เขต {con}: {flags.map(f => f.flag).join(', ')}
                            </span>
                          )
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )
            })()}

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
                    {s.multiPage > 0 && <StatCard label="PDF หลายหน้า" value={s.multiPage} color="amber" />}
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
