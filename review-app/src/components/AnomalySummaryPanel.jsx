import React, { useMemo } from 'react'
import { AlertTriangle, FileText, Eye, EyeOff, TrendingUp, Users, MapPin } from 'lucide-react'
import { getSeverityColor, getSeverityLabel } from '../utils/anomalyScore'

function AnomalySummaryPanel({ allItems, anomalyScoreMap, anomalyFlags, filterProvince, filterConstituency }) {
  // Group anomalies by type and severity
  const anomalyGroups = useMemo(() => {
    const groups = {
      critical: {},
      high: {},
      medium: {},
      low: {}
    }

    allItems.forEach(item => {
      const scoreData = anomalyScoreMap[item.id]
      if (!scoreData || scoreData.score === 0) return

      // Filter by province/constituency if specified
      if (filterProvince !== 'all' && item.province !== filterProvince) return
      if (filterConstituency !== 'all' && String(item.constituency) !== filterConstituency) return

      scoreData.reasons.forEach(reason => {
        const severity = reason.severity
        const label = reason.label

        if (!groups[severity][label]) {
          groups[severity][label] = {
            count: 0,
            items: [],
            totalScore: 0,
            example: reason.detail
          }
        }

        groups[severity][label].count++
        groups[severity][label].items.push({
          id: item.id,
          province: item.province,
          constituency: item.constituency,
          file: item.file,
          score: scoreData.score,
          detail: reason.detail
        })
        groups[severity][label].totalScore += scoreData.score
      })
    })

    return groups
  }, [allItems, anomalyScoreMap, filterProvince, filterConstituency])

  // Calculate totals
  const totals = useMemo(() => {
    const result = { critical: 0, high: 0, medium: 0, low: 0, totalItems: 0, totalScore: 0 }
    
    Object.entries(anomalyGroups).forEach(([severity, types]) => {
      Object.values(types).forEach(type => {
        result[severity] += type.count
        result.totalItems += type.count
        result.totalScore += type.totalScore
      })
    })
    
    return result
  }, [anomalyGroups])

  const severityOrder = ['critical', 'high', 'medium', 'low']

  return (
    <div className="max-w-[1440px] mx-auto px-4 py-6">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-gray-800 mb-2 flex items-center gap-2">
          <AlertTriangle className="text-orange-500" size={24} />
          ภาพรวมข้อมูลผิดปกติ
        </h2>
        <p className="text-gray-600 text-sm">
          หน้าลายเซ็น, หน้าว่าง, PDF คุณภาพต่ำ และความผิดปกติอื่นๆ ที่ต้องการการตรวจสอบจากมนุษย์
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
          <div className="text-gray-600 text-2xl font-bold">{totals.totalItems}</div>
          <div className="text-gray-800 text-sm font-medium">รวม</div>
          <div className="text-gray-600 text-xs">รายการทั้งหมด</div>
        </div>
      </div>

      {/* Anomaly Types by Severity */}
      {severityOrder.map(severity => {
        const types = anomalyGroups[severity]
        const typeKeys = Object.keys(types)
        
        if (typeKeys.length === 0) return null

        const colors = getSeverityColor(severity)
        
        return (
          <div key={severity} className="mb-6">
            <h3 className={`text-lg font-semibold mb-3 flex items-center gap-2 ${colors.text}`}>
              <div className={`w-3 h-3 rounded-full ${colors.badge}`}></div>
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
                      <p className="text-sm text-gray-600 mb-3 italic">
                        ตัวอย่าง: {typeData.example}
                      </p>
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

      {totals.totalItems === 0 && (
        <div className="text-center py-12 text-gray-500">
          <FileText size={48} className="mx-auto mb-4 opacity-50" />
          <p>ไม่พบข้อมูลผิดปกติในช่วงที่กรอง</p>
        </div>
      )}
    </div>
  )
}

export default AnomalySummaryPanel