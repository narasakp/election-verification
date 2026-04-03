import React, { useMemo, useState } from 'react'
import { AlertTriangle, FileText, Wrench, Database, ChevronDown, ChevronUp, BarChart3, Info } from 'lucide-react'
import { getSeverityColor, getSeverityLabel } from '../utils/anomalyScore'

function AnomalySummaryPanel({ allItems, anomalyScoreMap, anomalyFlags, filterProvince, filterConstituency }) {
  // Split reasons by source: 'electoral' (default) vs 'ocr_quality'
  const { electoralGroups, ocrGroups } = useMemo(() => {
    const electoral = { critical: {}, high: {}, medium: {}, low: {} }
    const ocr = {}

    allItems.forEach(item => {
      const scoreData = anomalyScoreMap[item.id]
      if (!scoreData || scoreData.score === 0) return
      if (filterProvince !== 'all' && item.province !== filterProvince) return
      if (filterConstituency !== 'all' && String(item.constituency) !== filterConstituency) return

      scoreData.reasons.forEach(reason => {
        const isOcr = reason.source === 'ocr_quality'
        const target = isOcr ? ocr : electoral[reason.severity]
        if (!target) return

        const label = reason.label
        if (!target[label]) {
          target[label] = { count: 0, items: [], example: reason.detail, severity: reason.severity, fixed: reason.points === 0 }
        }
        target[label].count++
        target[label].items.push({
          id: item.id,
          province: item.province,
          constituency: item.constituency,
          file: item.file,
          detail: reason.detail,
        })
      })
    })

    return { electoralGroups: electoral, ocrGroups: ocr }
  }, [allItems, anomalyScoreMap, filterProvince, filterConstituency])

  // Totals count only electoral (not OCR quality)
  const totals = useMemo(() => {
    const result = { critical: 0, high: 0, medium: 0, low: 0 }
    Object.entries(electoralGroups).forEach(([severity, types]) => {
      Object.values(types).forEach(t => { result[severity] += t.count })
    })
    result.total = result.critical + result.high + result.medium + result.low
    return result
  }, [electoralGroups])

  const ocrTotals = useMemo(() => {
    let pending = 0, fixed = 0
    Object.values(ocrGroups).forEach(g => {
      if (g.fixed) fixed += g.count
      else pending += g.count
    })
    return { pending, fixed }
  }, [ocrGroups])

  const severityOrder = ['critical', 'high', 'medium', 'low']
  const hasElectoral = totals.total > 0
  const hasOcr = Object.keys(ocrGroups).length > 0

  return (
    <div className="max-w-[1440px] mx-auto px-4 py-6">

      {/* ── Section 1: Electoral Anomalies ── */}
      <div className="mb-8">
        <div className="mb-5">
          <h2 className="text-xl font-bold text-gray-800 mb-1 flex items-center gap-2">
            <AlertTriangle className="text-orange-500" size={24} />
            ความผิดปกติที่ต้องตรวจสอบ
          </h2>
          <p className="text-gray-500 text-sm">
            ค่าสถิติผิดปกติ, ความขัดแย้งของข้อมูล และตัวชี้วัดที่ต้องการการตรวจสอบจากมนุษย์
          </p>
        </div>

        {/* Summary Stats */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="text-red-600 text-2xl font-bold">{totals.critical}</div>
            <div className="text-red-800 text-sm font-medium">วิกฤต</div>
            <div className="text-red-600 text-xs">ต้องการตรวจด่วน</div>
          </div>
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
            <div className="text-orange-600 text-2xl font-bold">{totals.high}</div>
            <div className="text-orange-800 text-sm font-medium">สูง</div>
            <div className="text-orange-600 text-xs">ตรวจก่อน</div>
          </div>
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <div className="text-yellow-600 text-2xl font-bold">{totals.medium}</div>
            <div className="text-yellow-800 text-sm font-medium">ปานกลาง</div>
            <div className="text-yellow-600 text-xs">ตรวจตามลำดับ</div>
          </div>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="text-blue-600 text-2xl font-bold">{totals.low}</div>
            <div className="text-blue-800 text-sm font-medium">ต่ำ</div>
            <div className="text-blue-600 text-xs">ตรวจทีหลัง</div>
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <div className="text-gray-600 text-2xl font-bold">{totals.total}</div>
            <div className="text-gray-800 text-sm font-medium">รวม</div>
            <div className="text-gray-600 text-xs">รายการทั้งหมด</div>
          </div>
        </div>

        {/* Anomaly Types by Severity */}
        {severityOrder.map(severity => {
          const types = electoralGroups[severity]
          const typeKeys = Object.keys(types)
          if (typeKeys.length === 0) return null
          const colors = getSeverityColor(severity)
          return (
            <div key={severity} className="mb-6">
              <h3 className={`text-lg font-semibold mb-3 flex items-center gap-2 ${colors.text}`}>
                <div className={`w-3 h-3 rounded-full ${colors.badge}`} />
                {getSeverityLabel(severity)} ({Object.values(types).reduce((s, t) => s + t.count, 0)} รายการ)
              </h3>
              <div className="space-y-3">
                {typeKeys.map(typeLabel => {
                  const typeData = types[typeLabel]
                  return (
                    <div key={typeLabel} className={`${colors.bg} border ${colors.border} rounded-lg p-4`}>
                      <div className="flex items-start justify-between mb-2">
                        <h4 className="font-medium text-gray-800">{typeLabel}</h4>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${colors.badge} text-white`}>
                          {typeData.count} รายการ
                        </span>
                      </div>
                      {typeData.example && (
                        <p className="text-sm text-gray-600 mb-2 italic">ตัวอย่าง: {typeData.example}</p>
                      )}
                      <div className="text-xs text-gray-500">
                        จังหวัด: {[...new Set(typeData.items.map(i => i.province))].join(', ')}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )
        })}

        {!hasElectoral && (
          <div className="text-center py-10 text-gray-400">
            <FileText size={40} className="mx-auto mb-3 opacity-40" />
            <p>ไม่พบความผิดปกติในช่วงที่กรอง</p>
          </div>
        )}
      </div>

      {/* ── Section 2: Known OCR Quality Issues ── */}
      {hasOcr && (
        <div className="border-t border-gray-200 pt-6">
          <div className="mb-5">
            <h2 className="text-xl font-bold text-gray-700 mb-1 flex items-center gap-2">
              <Wrench className="text-slate-500" size={22} />
              ปัญหาคุณภาพ OCR ที่รับทราบแล้ว
            </h2>
            <p className="text-gray-400 text-sm">
              ปัญหาเหล่านี้เกิดจากข้อจำกัดของ OCR ที่ระบุสาเหตุได้แล้ว — แยกออกเพื่อไม่ให้ปนกับตัวชี้วัดข้างต้น
            </p>
          </div>

          {/* OCR Summary Stats */}
          <div className="flex gap-4 mb-5">
            {ocrTotals.pending > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg px-5 py-3 flex items-center gap-3">
                <div>
                  <div className="text-amber-600 text-xl font-bold">{ocrTotals.pending}</div>
                  <div className="text-amber-800 text-xs font-medium">ยังไม่ได้แก้ไข</div>
                </div>
                <span className="text-[10px] text-amber-600 bg-amber-100 rounded px-1.5 py-0.5 font-semibold">ต้องระวัง</span>
              </div>
            )}
            {ocrTotals.fixed > 0 && (
              <div className="bg-teal-50 border border-teal-200 rounded-lg px-5 py-3 flex items-center gap-3">
                <div>
                  <div className="text-teal-600 text-xl font-bold">{ocrTotals.fixed}</div>
                  <div className="text-teal-800 text-xs font-medium">แก้ไขอัตโนมัติแล้ว</div>
                </div>
                <span className="text-[10px] text-teal-700 bg-teal-100 rounded px-1.5 py-0.5 font-semibold">ไม่ต้องดำเนินการ</span>
              </div>
            )}
          </div>

          {/* OCR Issue Cards */}
          <div className="space-y-3">
            {Object.entries(ocrGroups).map(([label, data]) => (
              <div
                key={label}
                className={`border rounded-lg p-4 ${
                  data.fixed
                    ? 'bg-teal-50 border-teal-200'
                    : 'bg-amber-50 border-amber-200'
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <h4 className="font-medium text-gray-800">{label}</h4>
                    {data.fixed
                      ? <span className="text-[10px] px-1.5 py-0.5 rounded font-semibold bg-teal-200 text-teal-800">แก้แล้ว</span>
                      : <span className="text-[10px] px-1.5 py-0.5 rounded font-semibold bg-amber-200 text-amber-800">ยังผิดอยู่</span>
                    }
                  </div>
                  <span className={`px-2 py-1 rounded text-xs font-medium text-white ${data.fixed ? 'bg-teal-500' : 'bg-amber-500'}`}>
                    {data.count} รายการ
                  </span>
                </div>
                {data.example && (
                  <p className="text-sm text-gray-600 mb-2 italic">ตัวอย่าง: {data.example}</p>
                )}
                <div className="text-xs text-gray-500">
                  จังหวัด: {[...new Set(data.items.map(i => i.province))].join(', ')}
                  {' — '}เขต: {[...new Set(data.items.map(i => i.constituency))].sort((a,b)=>a-b).join(', ')}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      {/* ── Section 3: Data Quality Overview ── */}
      <DataQualityOverview allItems={allItems} filterProvince={filterProvince} filterConstituency={filterConstituency} />
    </div>
  )
}


/* ────────────────────────────────────────────────────────────── */
/*  Sub-component: Data Quality Overview                         */
/* ────────────────────────────────────────────────────────────── */
function DataQualityOverview({ allItems, filterProvince, filterConstituency }) {
  const [expandedSection, setExpandedSection] = useState(null)
  const toggle = (key) => setExpandedSection(prev => prev === key ? null : key)

  const stats = useMemo(() => {
    const filtered = allItems.filter(item => {
      if (filterProvince !== 'all' && item.province !== filterProvince) return false
      if (filterConstituency !== 'all' && String(item.constituency) !== filterConstituency) return false
      return true
    })

    const total = filtered.length
    const byVoteType = {}
    filtered.forEach(item => {
      const vt = item.vote_type || 'ไม่ระบุ'
      if (!byVoteType[vt]) byVoteType[vt] = []
      byVoteType[vt].push(item)
    })

    // Party list completeness
    const partyList = byVoteType['บัญชีรายชื่อ'] || []
    const plTotal = partyList.length
    const pl57 = partyList.filter(r => (r.candidates || []).length === 57).length
    const plPct = plTotal > 0 ? (pl57 / plTotal * 100).toFixed(1) : 0

    // Party list breakdown by n
    const plByN = {}
    partyList.forEach(r => {
      const n = (r.candidates || []).length
      if (!plByN[n]) plByN[n] = { count: 0, items: [] }
      plByN[n].count++
      plByN[n].items.push(r)
    })

    // Province breakdown for party list
    const plByProvince = {}
    partyList.forEach(r => {
      const prov = r.province || '?'
      if (!plByProvince[prov]) plByProvince[prov] = { total: 0, n57: 0 }
      plByProvince[prov].total++
      if ((r.candidates || []).length === 57) plByProvince[prov].n57++
    })

    // Constituency (แบ่งเขต) stats
    const constituency = byVoteType['แบ่งเขต'] || []
    const consTotal = constituency.length
    const consWithCands = constituency.filter(r => (r.candidates || []).length > 0).length

    // Ballot data completeness
    const ballotFields = ['registered_voters', 'turnout', 'valid_ballots', 'invalid_ballots']
    const withBallot = filtered.filter(r => ballotFields.some(f => r[f] != null && r[f] !== 0)).length
    const noBallot = total - withBallot

    // Categorize remaining issues
    const issues = []

    // Issue 1: Party list n≠57
    const plIncomplete = plTotal - pl57
    if (plIncomplete > 0) {
      const groups = []
      // n=23 group
      const n23 = (plByN[23] || { count: 0 }).count
      if (n23 > 0) groups.push({
        label: 'n=23 (มีเฉพาะหน้าสุดท้าย พรรคที่ 35-57)',
        count: n23,
        cause: 'หน้าที่ 1-2 ของบัญชีรายชื่อไม่ได้ถูก OCR หรืออยู่ในไฟล์ PDF รวมที่ layout ต่างออกไป',
        fixable: 'ยาก — ต้อง re-OCR หน้าที่ขาด',
        severity: 'medium',
      })
      // n=10 group
      const n10 = (plByN[10] || { count: 0 }).count
      if (n10 > 0) groups.push({
        label: 'n=10 (มีเฉพาะหน้าแรก พรรคที่ 1-10)',
        count: n10,
        cause: 'OCR คุณภาพต่ำ — หน้าที่ 2-3 อ่านได้แค่ 3-4 ผู้สมัคร และหมายเลข reset จาก 1 ทุกหน้า',
        fixable: 'ยาก — ต้อง re-OCR ด้วย prompt ที่ดีกว่า',
        severity: 'medium',
      })
      // n>57 group
      const nOver = Object.entries(plByN).filter(([k]) => Number(k) > 57).reduce((s, [, v]) => s + v.count, 0)
      if (nOver > 0) groups.push({
        label: 'n>57 (ผู้สมัครเกิน — over-merged)',
        count: nOver,
        cause: 'การรวมหน้าหลายหน่วยเข้าด้วยกันผิดพลาด หรือ OCR อ่านหมายเลขผู้สมัครผิด (>57)',
        fixable: 'แก้ไขอัตโนมัติบางส่วนแล้ว — ส่วนที่เหลือต้องตรวจ manually',
        severity: 'low',
      })
      // Other n<57
      const nOther = plIncomplete - n23 - n10 - nOver
      if (nOther > 0) groups.push({
        label: `อื่นๆ (n=4-56 กระจัดกระจาย)`,
        count: nOther,
        cause: 'OCR ไม่สมบูรณ์ — อ่านได้บางส่วน, หน้าหาย, หรือ candidate number ซ้ำ',
        fixable: 'ยากมาก — กระจายหลายสาเหตุ ต้องตรวจทีละไฟล์',
        severity: 'low',
      })

      issues.push({
        title: 'บัญชีรายชื่อไม่ครบ 57 พรรค',
        icon: '📋',
        total: plIncomplete,
        pctOfAll: plTotal > 0 ? (plIncomplete / plTotal * 100).toFixed(1) : 0,
        groups,
      })
    }

    // Issue 2: No ballot data
    if (noBallot > 0) {
      issues.push({
        title: 'ไม่มีข้อมูลสถิติบัตร',
        icon: '📊',
        total: noBallot,
        pctOfAll: total > 0 ? (noBallot / total * 100).toFixed(1) : 0,
        groups: [{
          label: 'ไม่มีค่า registered_voters, turnout, valid_ballots',
          count: noBallot,
          cause: 'หน้าที่ OCR เป็นหน้าลายเซ็น, หน้าหลัง, หรือ OCR อ่านไม่ออก',
          fixable: 'ส่วนใหญ่คือหน้าที่ไม่มีข้อมูลจริง (หน้าลายเซ็น)',
          severity: 'low',
        }],
      })
    }

    return { total, byVoteType, plTotal, pl57, plPct, plByN, plByProvince, consTotal, consWithCands, noBallot, issues }
  }, [allItems, filterProvince, filterConstituency])

  const plPctNum = parseFloat(stats.plPct)
  const pctColor = plPctNum >= 95 ? 'text-green-600' : plPctNum >= 85 ? 'text-yellow-600' : 'text-red-600'
  const pctBg = plPctNum >= 95 ? 'bg-green-500' : plPctNum >= 85 ? 'bg-yellow-500' : 'bg-red-500'

  const provColors = (pctN) => {
    if (pctN >= 95) return { card: 'bg-green-50 border-green-200', text: 'text-green-600', bar: 'bg-green-500' }
    if (pctN >= 85) return { card: 'bg-yellow-50 border-yellow-200', text: 'text-yellow-600', bar: 'bg-yellow-500' }
    return { card: 'bg-red-50 border-red-200', text: 'text-red-600', bar: 'bg-red-500' }
  }
  const issueColors = (severity) => {
    if (severity === 'medium') return { card: 'bg-amber-50 border-amber-200', badge: 'bg-amber-500' }
    return { card: 'bg-slate-50 border-slate-200', badge: 'bg-slate-500' }
  }

  return (
    <div className="border-t border-gray-200 pt-6 mt-8">
      <div className="mb-5">
        <h2 className="text-xl font-bold text-gray-800 mb-1 flex items-center gap-2">
          <Database className="text-indigo-500" size={22} />
          ภาพรวมคุณภาพข้อมูล
        </h2>
        <p className="text-gray-500 text-sm">
          สถานะความสมบูรณ์ของข้อมูลทั้งหมด และปัญหาที่ทราบแล้วพร้อมสาเหตุ
        </p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
          <div className="text-indigo-600 text-2xl font-bold">{stats.total.toLocaleString()}</div>
          <div className="text-indigo-800 text-sm font-medium">รายการทั้งหมด</div>
          <div className="text-indigo-500 text-xs">
            {Object.entries(stats.byVoteType).map(([vt, items]) => 
              `${vt}: ${items.length}`
            ).join(' | ')}
          </div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className={`text-2xl font-bold ${pctColor}`}>{stats.plPct}%</div>
          <div className="text-gray-800 text-sm font-medium">บัญชีรายชื่อครบ 57 พรรค</div>
          <div className="text-gray-500 text-xs">{stats.pl57.toLocaleString()} / {stats.plTotal.toLocaleString()}</div>
          <div className="mt-2 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div className={`h-full ${pctBg} rounded-full transition-all`} style={{ width: `${stats.plPct}%` }} />
          </div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-gray-700 text-2xl font-bold">{stats.consWithCands.toLocaleString()}</div>
          <div className="text-gray-800 text-sm font-medium">แบ่งเขตมีผู้สมัคร</div>
          <div className="text-gray-500 text-xs">{stats.consWithCands} / {stats.consTotal} ({stats.consTotal > 0 ? (stats.consWithCands / stats.consTotal * 100).toFixed(1) : 0}%)</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-gray-700 text-2xl font-bold">{(stats.total - stats.noBallot).toLocaleString()}</div>
          <div className="text-gray-800 text-sm font-medium">มีข้อมูลสถิติบัตร</div>
          <div className="text-gray-500 text-xs">{stats.total - stats.noBallot} / {stats.total} ({stats.total > 0 ? ((stats.total - stats.noBallot) / stats.total * 100).toFixed(1) : 0}%)</div>
        </div>
      </div>

      {/* Party List by Province */}
      {Object.keys(stats.plByProvince).length > 0 && (
        <div className="mb-6">
          <button onClick={() => toggle('province')} className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-3 hover:text-indigo-600 transition-colors">
            <BarChart3 size={16} />
            บัญชีรายชื่อ n=57 แยกตามจังหวัด
            {expandedSection === 'province' ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
          {expandedSection === 'province' && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {Object.entries(stats.plByProvince).sort((a, b) => b[1].total - a[1].total).map(([prov, data]) => {
                const pct = data.total > 0 ? (data.n57 / data.total * 100).toFixed(1) : 0
                const pc = provColors(parseFloat(pct))
                return (
                  <div key={prov} className={`${pc.card} border rounded-lg p-3`}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-gray-800">{prov}</span>
                      <span className={`${pc.text} font-bold`}>{pct}%</span>
                    </div>
                    <div className="text-xs text-gray-500 mb-1">{data.n57} / {data.total}</div>
                    <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                      <div className={`h-full ${pc.bar} rounded-full`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* Known Remaining Issues */}
      {stats.issues.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <Info className="text-slate-400" size={18} />
            ปัญหาที่ทราบแล้ว — สาเหตุและสถานะ
          </h3>
          <div className="space-y-4">
            {stats.issues.map((issue, idx) => (
              <div key={idx} className="border border-gray-200 rounded-lg overflow-hidden">
                <button
                  onClick={() => toggle(`issue-${idx}`)}
                  className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-lg">{issue.icon}</span>
                    <div>
                      <span className="font-medium text-gray-800">{issue.title}</span>
                      <span className="text-gray-500 text-sm ml-2">({issue.total} รายการ, {issue.pctOfAll}%)</span>
                    </div>
                  </div>
                  {expandedSection === `issue-${idx}` ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
                </button>
                {expandedSection === `issue-${idx}` && (
                  <div className="p-4 space-y-3">
                    {issue.groups.map((g, gi) => {
                      const ic = issueColors(g.severity)
                      return (
                        <div key={gi} className={`${ic.card} border rounded-lg p-3`}>
                          <div className="flex items-start justify-between mb-2">
                            <span className="font-medium text-gray-800 text-sm">{g.label}</span>
                            <span className={`${ic.badge} text-white text-xs px-2 py-0.5 rounded font-medium`}>{g.count}</span>
                          </div>
                          <div className="space-y-1 text-xs">
                            <p className="text-gray-600"><span className="font-semibold text-gray-700">สาเหตุ:</span> {g.cause}</p>
                            <p className="text-gray-600"><span className="font-semibold text-gray-700">แก้ไขได้:</span> {g.fixable}</p>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default AnomalySummaryPanel
