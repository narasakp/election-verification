import React, { useMemo } from 'react'
import { AlertTriangle, FileText, Wrench } from 'lucide-react'
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
    </div>
  )
}

export default AnomalySummaryPanel
