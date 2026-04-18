import React, { useState, useMemo, useCallback } from 'react'
import CandidateTable from './CandidateTable'
import ErrorBoundary from './ErrorBoundary'
import { Eye, EyeOff, RotateCw, ExternalLink, AlertTriangle, AlertCircle, Info, Loader2 } from 'lucide-react'
import { validateItem, getWorstSeverity } from '../utils/validation'
import { validateEditValue } from '../utils/reviewLog'
import { getSeverityColor, getSeverityLabel, getScoreColor } from '../utils/anomalyScore'

const LOCATION_META = [
  { key: 'province', label: 'จังหวัด', text: true, shared: true },
  { key: 'constituency', label: 'เขตเลือกตั้ง', shared: true, intOnly: true },
  { key: 'district', label: 'อำเภอ', text: true },
  { key: 'sub_district', label: 'ตำบล', text: true },
  { key: 'station_range', label: 'ช่วงหน่วย', text: true },
  { key: 'ocr_station_no', label: 'หน่วยที่' },
]

const STAT_FIELDS = [
  { key: 'registered_voters', label: 'ผู้มีสิทธิ' },
  { key: 'turnout', label: 'มาแสดงตน' },
  { key: 'ballots_received', label: 'บัตรที่ได้รับ' },
  { key: 'valid_ballots', label: 'บัตรดี' },
  { key: 'invalid_ballots', label: 'บัตรเสีย' },
  { key: 'no_vote_ballots', label: 'ไม่เลือกใคร' },
  { key: 'remaining_ballots', label: 'บัตรเหลือ' },
  { key: 'total_votes', label: 'รวมคะแนน' },
]

function fv(val) {
  if (val === null || val === undefined) return <span className="text-gray-300 italic">—</span>
  return String(val)
}

function confidenceBadge(level) {
  if (!level) return null
  const cls = {
    'high': 'bg-green-100 text-green-700',
    'medium': 'bg-yellow-100 text-yellow-700',
    'low_digit_only': 'bg-orange-100 text-orange-700',
    'low_thai_only': 'bg-orange-100 text-orange-700',
    'low_disagree': 'bg-red-100 text-red-700',
    'none': 'bg-gray-100 text-gray-500',
  }[level] || 'bg-gray-100 text-gray-500'
  const txt = level.replace('low_', '').replace('_', ' ')
  return <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${cls}`}>{txt}</span>
}

function voteTypeBadge(voteType) {
  const config = {
    'แบ่งเขต': { label: '🗳️ แบ่งเขต (สส.)', cls: 'bg-blue-600 text-white border-blue-700' },
    'บัญชีรายชื่อ': { label: '📝 บัญชีรายชื่อ (บช.)', cls: 'bg-purple-100 text-purple-700 border-purple-300' },
    'ประชามติ': { label: '🗳️ ประชามติ (อ.ส.)', cls: 'bg-teal-100 text-teal-700 border-teal-300' },
    'นอกเขต': { label: '📮 นอกเขต', cls: 'bg-gray-100 text-gray-600 border-gray-300' },
  }
  const c = config[voteType] || { label: voteType || 'ไม่ระบุ', cls: 'bg-gray-100 text-gray-500 border-gray-300' }
  return <span className={`px-2.5 py-1 rounded-full text-xs font-bold border ${c.cls}`}>{c.label}</span>
}

function EditInput({ field, value, isText, intOnly, edits, onEdit, shared, sharedEdits, onSharedEdit, isFirstPage }) {
  // Shared field logic
  if (shared) {
    const sharedVal = sharedEdits?.[field]
    const hasShared = sharedVal !== undefined
    const displayVal = hasShared ? sharedVal : (value == null ? '' : String(value))
    if (!isFirstPage) {
      return (
        <input
          className={`w-[90px] px-1.5 py-0.5 border rounded text-sm text-right ${isText ? 'text-left w-[130px]' : ''} border-gray-100 bg-gray-50 text-gray-400 cursor-not-allowed`}
          value={displayVal}
          disabled
          title="แก้ได้ที่หน้าแรกของเขตเท่านั้น"
        />
      )
    }
    return (
      <input
        className={`w-[90px] px-1.5 py-0.5 border rounded text-sm text-right ${isText ? 'text-left w-[130px]' : ''} ${hasShared ? 'border-indigo-400 bg-indigo-50 font-semibold' : 'border-gray-200'}`}
        value={displayVal}
        onChange={e => {
          const v = e.target.value
          if (intOnly && v !== '' && !/^[1-9]\d*$/.test(v)) return
          onSharedEdit(field, v, value)
        }}
        type={intOnly ? 'text' : undefined}
        inputMode={intOnly ? 'numeric' : undefined}
        pattern={intOnly ? '[0-9]*' : undefined}
        placeholder="ที่ถูกต้อง"
      />
    )
  }
  // Normal (per-page) field
  const edited = edits?.[field]
  const hasEdit = edited !== undefined
  const displayVal = hasEdit ? edited : (value == null ? '' : String(value))
  const validation = hasEdit ? validateEditValue(field, edited) : { valid: true }
  const isInvalid = !validation.valid
  return (
    <input
      className={`w-[90px] px-1.5 py-0.5 border rounded text-sm text-right ${isText ? 'text-left w-[130px]' : ''} ${
        isInvalid ? 'border-red-500 bg-red-50 ring-1 ring-red-300' :
        hasEdit ? 'border-amber-400 bg-amber-50 font-semibold' : 'border-gray-200'
      }`}
      value={displayVal}
      onChange={e => onEdit(field, e.target.value, value)}
      placeholder="ที่ถูกต้อง"
      title={isInvalid ? validation.reason : undefined}
    />
  )
}

function ReviewCardInner({ item, review, reviewSummary, isFirstPage, sharedEdits, anomalyFlags, anomalyScore, onSetStatus, onSetNote, onEdit, onSharedEdit }) {
  const [showOcrText, setShowOcrText] = useState(false)
  const [zoomed, setZoomed] = useState(false)
  const [rotation, setRotation] = useState(0)
  const [confirmAction, setConfirmAction] = useState(null)
  const [pdfLoading, setPdfLoading] = useState(true)
  const status = review.status || 'pending'
  const edits = review.edits || {}

  // Data validation
  const warnings = useMemo(() => validateItem(item), [item])
  const worstSeverity = useMemo(() => getWorstSeverity(warnings), [warnings])

  // Map stat fields to their worst warning severity for inline highlighting
  const fieldWarningMap = useMemo(() => {
    const map = {}
    const fieldMapping = {
      'turnout_exceeds_voters': ['registered_voters', 'turnout'],
      'votes_ne_valid': ['total_votes', 'valid_ballots'],
      'ballot_sum_ne_turnout': ['valid_ballots', 'invalid_ballots', 'no_vote_ballots', 'turnout'],
      'negative_remaining': ['remaining_ballots'],
      'received_ne_used_plus_remain': ['ballots_received', 'turnout', 'remaining_ballots'],
      'cand_sum_ne_total': ['total_votes'],
      'voters_too_high': ['registered_voters'],
      'cand_exceeds_valid': ['valid_ballots'],
    }
    warnings.forEach(w => {
      const fields = fieldMapping[w.id] || []
      fields.forEach(f => {
        if (!map[f] || w.severity === 'error') map[f] = w.severity
      })
    })
    return map
  }, [warnings])

  const borderColor = {
    confirmed: 'border-l-green-500',
    flagged: 'border-l-amber-500',
    rejected: 'border-l-red-500',
  }[status] || ''

  const statusBadge = {
    pending: <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-500 border border-dashed border-gray-300">📋 รอคุณตรวจ</span>,
    confirmed: <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-green-100 text-green-700">✅ ยืนยันแล้ว</span>,
    flagged: <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-700">🔄 ตรวจอีกรอบ</span>,
    rejected: <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-700">🚫 ใช้ไม่ได้</span>,
  }[status] || null

  // Candidate badge
  const cands = item.candidates || []
  const ectCount = item.ect_candidate_count
  const hasMismatch = item._candidate_mismatch
  const wasAutoFixed = item._candidates_auto_fixed
  const candBadge = cands.length > 0
    ? <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${hasMismatch ? 'bg-amber-100 text-amber-700 border border-amber-300' : 'bg-blue-100 text-blue-700'}`}>
        {cands.length} ผู้สมัคร{ectCount != null ? ` / ECT ${ectCount}` : ''}
        {hasMismatch ? ' ⚠' : ''}{wasAutoFixed ? ' 🔧' : ''}
      </span>
    : <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-500">ไม่พบผู้สมัคร{ectCount != null ? ` (ECT ${ectCount})` : ''}</span>

  // Collect all parties for dropdown
  const allParties = useMemo(() => {
    const s = new Set()
    cands.forEach(c => { if (c.party) s.add(c.party) })
    return [...s].sort()
  }, [cands])

  return (
    <div className={`bg-white rounded-lg shadow-md overflow-hidden border-l-4 ${borderColor}`}>
      {/* Card Header */}
      <div className="px-4 py-3 border-b bg-gray-50 flex items-center flex-wrap gap-2">
        <h3 className="text-sm font-semibold text-gray-800 lg:w-[45%] flex-shrink-0 flex items-center gap-2 flex-wrap">
          {voteTypeBadge(item.vote_type)}
          <span>📄 {item.file} — หน้า {item.page}/{item.total_pages || '?'}</span>
        </h3>
        <div className="flex-1 flex items-center justify-center">
          <div className={`px-3 py-1 rounded border text-sm ${
            reviewSummary
              ? reviewSummary.hasConflict
                ? 'border-amber-400 bg-amber-50 text-amber-700'
                : 'border-blue-300 bg-blue-50 text-blue-700'
              : 'border-gray-200 bg-gray-50 text-gray-400'
          }`}>
            {reviewSummary ? (
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-semibold">ตรวจแล้ว {reviewSummary.reviewerCount} คน {reviewSummary.totalReviews} ครั้ง</span>
                  {reviewSummary.majorityStatus ? (
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                      reviewSummary.majorityStatus === 'confirmed' ? 'bg-green-200 text-green-800' :
                      reviewSummary.majorityStatus === 'flagged' ? 'bg-amber-200 text-amber-800' :
                      reviewSummary.majorityStatus === 'rejected' ? 'bg-red-200 text-red-800' : 'bg-gray-200'
                    }`}>
                      Consensus: {reviewSummary.majorityStatus}
                      {reviewSummary.consensusRatio < 1 && ` (${Math.round(reviewSummary.consensusRatio * 100)}%)`}
                    </span>
                  ) : reviewSummary.isTie ? (
                    <span className="text-[10px] px-1.5 py-0.5 rounded font-bold bg-purple-200 text-purple-800">
                      ⚖️ เสมอ: {reviewSummary.tiedStatuses?.join(' vs ')}
                    </span>
                  ) : null}
                  {reviewSummary.hasConflict && !reviewSummary.isTie && (
                    <span className="text-xs text-amber-600 font-medium">⚠ ไม่ตรงกัน</span>
                  )}
                </div>
                {reviewSummary.outliers?.length > 0 && (
                  <div className="text-[10px] mt-0.5 text-red-600">
                    Outlier: {reviewSummary.outliers.map(o => `${o.name || o.email} (${o.status})`).join(', ')}
                  </div>
                )}
                {reviewSummary.editConflicts && Object.keys(reviewSummary.editConflicts).length > 0 && (
                  <div className="text-[10px] mt-0.5 text-amber-700">
                    ค่าแก้ไขขัดแย้ง: {Object.entries(reviewSummary.editConflicts).map(([f, vals]) =>
                      `${f}: ${vals.map(v => v.value).join(' vs ')}`
                    ).join(', ')}
                  </div>
                )}
              </div>
            ) : (
              <span>ตรวจแล้ว 0 คน 0 ครั้ง</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {item._source_type === 'vision' && (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-orange-100 text-orange-700 border border-orange-200" title="ใช้ Vision OCR (คุณภาพต่ำกว่า Gemini)">👁 Vision OCR</span>
          )}
          {statusBadge}
        </div>
      </div>

      {/* Validation Warnings */}
      {warnings.length > 0 && (
        <div className={`px-4 py-2 border-b text-sm ${
          worstSeverity === 'error' ? 'bg-red-50 border-red-200' :
          worstSeverity === 'warning' ? 'bg-amber-50 border-amber-200' :
          'bg-blue-50 border-blue-200'
        }`}>
          <div className="flex items-center gap-1.5 mb-1 font-semibold text-xs uppercase tracking-wider">
            {worstSeverity === 'error' ? <AlertCircle size={14} className="text-red-500" /> :
             worstSeverity === 'warning' ? <AlertTriangle size={14} className="text-amber-500" /> :
             <Info size={14} className="text-blue-500" />}
            <span className={worstSeverity === 'error' ? 'text-red-700' : worstSeverity === 'warning' ? 'text-amber-700' : 'text-blue-700'}>
              พบปัญหา {warnings.length} รายการ
            </span>
          </div>
          <ul className="space-y-0.5">
            {warnings.map(w => (
              <li key={w.id} className="flex items-start gap-1.5">
                <span className={`mt-0.5 flex-shrink-0 w-1.5 h-1.5 rounded-full ${
                  w.severity === 'error' ? 'bg-red-500' : w.severity === 'warning' ? 'bg-amber-500' : 'bg-blue-400'
                }`} />
                <span className={
                  w.severity === 'error' ? 'text-red-700' : w.severity === 'warning' ? 'text-amber-700' : 'text-blue-600'
                }>{w.message}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Anomaly Score Panel */}
      {anomalyScore && anomalyScore.score > 0 && (() => {
        // ECT constituency-level reason only shown on first page of each constituency
        const visibleReasons = isFirstPage
          ? anomalyScore.reasons
          : anomalyScore.reasons.filter(r => r.label !== 'เทียบคะแนน กกต.')
        const visibleScore = visibleReasons.reduce((s, r) => s + (r.points || 0), 0)
        if (visibleReasons.length === 0) return null
        return (
        <div className="px-4 py-2.5 border-b bg-gradient-to-r from-red-50 to-orange-50 border-red-200">
          <div className="flex items-center gap-2 mb-1.5">
            <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${getScoreColor(visibleScore)}`}>
              🚨 {visibleScore} คะแนน
            </span>
            <span className="text-xs font-semibold text-red-800 uppercase tracking-wider">ข้อมูลผิดปกติ</span>
            <span className="text-[10px] text-gray-500">— เรียงจากรุนแรงมากไปน้อย</span>
          </div>
          <div className="space-y-1">
            {visibleReasons.map((r, i) => {
              const color = getSeverityColor(r.severity)
              return (
                <div key={i} className={`flex items-start gap-2 px-2.5 py-1.5 rounded-lg border ${color.bg} ${color.border}`}>
                  <span className={`mt-0.5 flex-shrink-0 px-1.5 py-0 rounded text-[9px] font-bold text-white ${color.badge}`}>
                    {getSeverityLabel(r.severity)}
                  </span>
                  <div className="min-w-0">
                    <span className={`text-xs font-semibold ${color.text}`}>{r.label}</span>
                    <span className="text-[11px] text-gray-600 ml-1.5">{r.detail}</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
        )
      })()}

      {/* ECT Anomaly Flags (cross-reference from constituency-level analysis) — first page only */}
      {isFirstPage && anomalyFlags && anomalyFlags.length > 0 && (
        <div className="px-4 py-2 border-b bg-purple-50 border-purple-200">
          <div className="flex items-center gap-1.5 mb-1">
            <span className="text-sm">🔬</span>
            <span className="text-xs font-semibold text-purple-800 uppercase tracking-wider">ข้อมูล กกต. ระดับเขต — {item.province} เขต {item.constituency}</span>
            {anomalyFlags.some(f => f.incomplete) && (
              <span className="text-[9px] text-amber-600 italic">(ข้อมูลยังนับไม่ครบ 100%)</span>
            )}
            <a href="./anomaly.html" target="_blank" rel="noopener noreferrer"
               className="text-[10px] text-purple-600 hover:text-purple-800 underline flex items-center gap-0.5">
              <ExternalLink size={10} /> ดูวิเคราะห์ฉบับเต็ม
            </a>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {anomalyFlags.map((f, i) => (
              <span key={i} className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                f.severity === 'high' ? 'bg-red-100 text-red-800 border border-red-200' : 'bg-amber-100 text-amber-800 border border-amber-200'
              }`}>
                {f.severity === 'high' ? '🚨' : '⚠️'} {f.detail}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Body: image + data */}
      <div className="flex flex-col lg:flex-row">
        {/* Left: Image or PDF */}
        <div className="lg:w-[45%] flex-shrink-0 relative">
          {/* Tool buttons — covers browser's PDF pop-out icon */}
          <div className="absolute top-0 right-0 z-10 flex flex-col">
            <button
              onClick={() => setRotation(r => (r + 90) % 360)}
              className="w-14 h-14 flex items-center justify-center bg-white hover:bg-gray-100 shadow-lg border border-gray-300 text-gray-700 hover:text-gray-900 transition"
              title="หมุน 90°"
            >
              <RotateCw size={26} />
            </button>
            {item.drive_view_url && (
              <a href={item.drive_view_url} target="_blank" rel="noopener noreferrer"
                 className="w-14 h-14 flex items-center justify-center bg-white hover:bg-blue-50 shadow-lg border border-gray-300 border-t-0 text-gray-700 hover:text-blue-600 transition"
                 title="เปิดใน Drive" onClick={e => e.stopPropagation()}>
                <ExternalLink size={26} />
              </a>
            )}
          </div>
          <div
            className={`overflow-auto bg-gray-800 ${item.pdf_url ? '' : 'cursor-zoom-in max-h-[700px]'} ${zoomed ? 'cursor-zoom-out' : ''}`}
            onClick={() => !item.pdf_url && setZoomed(!zoomed)}
          >
            {item.pdf_url ? (
              <div className="relative">
                {pdfLoading && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-100 z-[5] animate-pulse">
                    <Loader2 size={32} className="text-gray-400 animate-spin mb-2" />
                    <span className="text-sm text-gray-400">กำลังโหลด PDF...</span>
                  </div>
                )}
                <iframe
                  src={`${item.pdf_url}#toolbar=0&navpanes=0&scrollbar=1`}
                  title="PDF preview"
                  className="w-full border-0"
                  style={{ height: '700px', transform: `rotate(${rotation}deg)`, transformOrigin: 'center center' }}
                  allow="autoplay"
                  onLoad={() => setPdfLoading(false)}
                />
              </div>
            ) : item.image_url ? (
              <img
                src={item.image_url}
                alt="scan"
                className={`block ${zoomed ? 'w-[200%]' : 'w-full'}`}
                style={{ transform: `rotate(${rotation}deg)`, transformOrigin: 'center center' }}
                loading="lazy"
              />
            ) : (
              <div className="flex flex-col items-center justify-center h-[400px] text-gray-400 text-sm gap-3 px-4">
                <span className="text-4xl">📄</span>
                <span>ไม่มีภาพตัวอย่างออนไลน์</span>
                <span className="text-xs text-gray-500 text-center">รายการนี้ใช้ Vision OCR จากไฟล์ local<br/>สามารถตรวจสอบข้อมูลจากตารางด้านขวาได้</span>
                {item.drive_view_url && (
                  <a href={item.drive_view_url} target="_blank" rel="noopener noreferrer"
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition">
                    เปิด PDF ใน Google Drive
                  </a>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right: Data */}
        <div className="flex-1 p-4 max-h-[700px] scroll-visible">
          {/* Section: ข้อมูลเขต/หน่วย */}
          <div className="mb-4">
            <div className="flex items-center gap-2 mb-1 border-b pb-1">
              <span className="w-[140px] flex-shrink-0 text-xs text-gray-400 uppercase tracking-wider font-semibold">📍 ข้อมูลเขต/หน่วย</span>
              <span className="flex-1 text-xs text-gray-400 font-semibold min-w-[120px]">ค่า OCR</span>
              <span className="w-[120px] flex-shrink-0 text-xs text-gray-400 font-semibold text-right">✏️ แก้ไข</span>
            </div>
            {LOCATION_META.map(f => (
              <div key={f.key} className="flex items-center gap-2 py-0.5 text-sm">
                <span className="w-[140px] text-gray-500 flex-shrink-0">{f.label}</span>
                <span className="flex-1 font-medium min-w-[120px]">{fv(f.shared && sharedEdits?.[f.key] != null ? sharedEdits[f.key] : item[f.key])}</span>
                <EditInput field={f.key} value={item[f.key]} isText={f.text} intOnly={f.intOnly} edits={edits} onEdit={onEdit}
                  shared={f.shared} sharedEdits={sharedEdits} onSharedEdit={onSharedEdit} isFirstPage={isFirstPage} />
              </div>
            ))}
          </div>

          {/* Section: สถิติ */}
          <div className="mb-4">
            <div className="flex items-center gap-2 mb-1 border-b pb-1">
              <span className="w-[140px] flex-shrink-0 text-xs text-gray-400 uppercase tracking-wider font-semibold">📊 สถิติการลงคะแนน</span>
              <span className="flex-1 text-xs text-gray-400 font-semibold min-w-[120px]">ค่า OCR</span>
              <span className="w-[120px] flex-shrink-0 text-xs text-gray-400 font-semibold text-right">✏️ แก้ไข</span>
            </div>
            {STAT_FIELDS.map(f => {
              const fw = fieldWarningMap[f.key]
              return (
              <div key={f.key} className={`flex items-center gap-2 py-0.5 text-sm ${f.key === 'total_votes' ? 'font-bold text-indigo-900 text-base mt-1' : ''} ${fw === 'error' ? 'bg-red-50 -mx-2 px-2 rounded' : fw === 'warning' ? 'bg-amber-50 -mx-2 px-2 rounded' : ''}`}>
                <span className="w-[140px] text-gray-500 flex-shrink-0">{f.label}{fw && <span className="ml-1">{fw === 'error' ? '🔴' : '🟡'}</span>}</span>
                <span className={`flex-1 font-medium min-w-[120px] ${fw === 'error' ? 'text-red-700' : fw === 'warning' ? 'text-amber-700' : ''}`}>{fv(item[f.key])}</span>
                {confidenceBadge(item.confidence?.[f.key])}
                <EditInput field={f.key} value={item[f.key]} edits={edits} onEdit={onEdit} />
              </div>
              )
            })}
          </div>

          {/* Section: ผู้สมัคร */}
          {cands.length > 0 && (
            <div className="mb-4">
              <h4 className="text-xs text-gray-400 uppercase tracking-wider font-semibold mb-1 border-b pb-1">
                👤 ผู้สมัคร (OCR {cands.length} คน{ectCount != null ? ` / กกต. ${ectCount} คน` : ''})
                {hasMismatch && <span className="ml-2 text-amber-600 normal-case">⚠ ไม่ตรง ({item._candidate_mismatch_detail})</span>}
                {wasAutoFixed && <span className="ml-2 text-green-600 normal-case">🔧 ตัด {item._candidates_removed} แถวผี</span>}
              </h4>
              <CandidateTable
                candidates={cands}
                allParties={allParties}
                edits={edits}
                onEdit={onEdit}
                isFirstPage={isFirstPage}
                sharedEdits={sharedEdits}
                onSharedEdit={onSharedEdit}
              />
            </div>
          )}

          {/* Section: ECT Reference */}
          {item.ect_candidates && item.ect_candidates.length > 0 && (
            <details className="mb-4">
              <summary className="text-xs text-gray-400 uppercase tracking-wider font-semibold mb-1 border-b pb-1 cursor-pointer hover:text-gray-600">
                🏛️ ข้อมูล กกต. ({item.ect_candidates.length} คน)
              </summary>
              <table className="w-full text-xs mt-1">
                <thead>
                  <tr className="text-gray-400">
                    <th className="text-left w-8">#</th>
                    <th className="text-left">ชื่อ</th>
                    <th className="text-left">พรรค</th>
                  </tr>
                </thead>
                <tbody>
                  {item.ect_candidates.map((ec, i) => (
                    <tr key={i} className="border-t border-gray-100">
                      <td className="py-0.5 text-gray-400">{ec.no}</td>
                      <td className="py-0.5">{ec.name}</td>
                      <td className="py-0.5 text-gray-500">{ec.party}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
          )}

          {/* OCR Text toggle */}
          <button
            onClick={() => setShowOcrText(!showOcrText)}
            className="flex items-center gap-1 px-2 py-1 text-xs bg-gray-100 rounded hover:bg-gray-200 transition mb-2"
          >
            {showOcrText ? <EyeOff size={12} /> : <Eye size={12} />}
            {showOcrText ? 'ซ่อน OCR Text' : 'ดู OCR Text'}
          </button>
          {showOcrText && item.ocr_text && (
            <pre className="text-[11px] text-gray-600 whitespace-pre-wrap font-mono bg-gray-50 p-2 rounded border max-h-48 overflow-auto">
              {item.ocr_text}
            </pre>
          )}
        </div>
      </div>

      {/* Confirmation dialog */}
      {confirmAction && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" onClick={() => setConfirmAction(null)}>
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4 overflow-hidden" onClick={e => e.stopPropagation()}>
            <div className={`px-5 py-3 border-b ${
              confirmAction === 'confirmed' ? 'bg-green-50 border-green-200' :
              confirmAction === 'flagged' ? 'bg-amber-50 border-amber-200' :
              confirmAction === 'rejected' ? 'bg-red-50 border-red-200' :
              'bg-gray-50 border-gray-200'
            }`}>
              <h3 className={`text-base font-bold ${
                confirmAction === 'confirmed' ? 'text-green-800' :
                confirmAction === 'flagged' ? 'text-amber-800' :
                confirmAction === 'rejected' ? 'text-red-800' :
                'text-gray-800'
              }`}>
                {confirmAction === 'confirmed' ? '✅ ยืนยัน' :
                 confirmAction === 'flagged' ? '🔄 ตรวจอีกรอบ' :
                 confirmAction === 'rejected' ? '🚫 ใช้ไม่ได้' :
                 '↩ รีเซ็ต'}
              </h3>
            </div>
            <div className="px-5 py-4 text-sm text-gray-700 space-y-2">
              {confirmAction === 'confirmed' ? (
                <>
                  <p className="font-semibold">ใช้เมื่อ:</p>
                  <ul className="list-disc ml-5 space-y-1 text-gray-600">
                    <li>ตรวจสอบตัวเลขกับภาพต้นฉบับแล้ว ถูกต้อง</li>
                    <li>แก้ไขค่าที่ผิดในช่อง "แก้ไข" เรียบร้อยแล้ว</li>
                    <li>ผู้สมัครและพรรคตรงกับข้อมูล กกต.</li>
                  </ul>
                  <p className="text-xs text-green-600 mt-2">หมายเหตุ: หน้านี้จะถูกนับเป็นข้อมูลที่ผ่านการตรวจสอบแล้ว</p>
                  <p className="text-xs text-gray-500">ถ้าไม่แน่ใจ → กด "ตรวจอีกรอบ" เพื่อส่งให้คนอื่นช่วยตรวจ</p>
                </>
              ) : confirmAction === 'flagged' ? (
                <>
                  <p className="font-semibold">ใช้เมื่อ:</p>
                  <ul className="list-disc ml-5 space-y-1 text-gray-600">
                    <li>ตัวเลขอ่านไม่ชัด ไม่มั่นใจว่าถูก</li>
                    <li>ภาพเบลอ/เอียง ต้องให้คนอื่นช่วยดู</li>
                    <li>ข้อมูลน่าสงสัย แต่ยังไม่แน่ใจพอจะแก้เอง</li>
                  </ul>
                  <p className="text-xs text-amber-600 mt-2">หมายเหตุ: หน้านี้จะถูกส่งให้อาสาคนอื่นตรวจซ้ำ</p>
                </>
              ) : confirmAction === 'rejected' ? (
                <>
                  <p className="font-semibold">ใช้เมื่อ:</p>
                  <ul className="list-disc ml-5 space-y-1 text-gray-600">
                    <li>ภาพเสียหาย/ว่างเปล่า ไม่สามารถอ่านได้</li>
                    <li>เอกสารไม่ใช่แบบ สส.5/16 (ผิดประเภท)</li>
                    <li>หน้าซ้ำ หรือสแกนผิดหน้า</li>
                  </ul>
                  <p className="text-xs text-red-600 mt-2">หมายเหตุ: หน้านี้จะถูกตัดออกจากชุดข้อมูลสุดท้าย</p>
                  <p className="text-xs text-gray-500">ถ้าข้อมูลแค่ผิด → แก้ตัวเลขแล้วกด "ยืนยัน" แทน</p>
                </>
              ) : (
                <>
                  <p className="font-semibold">ใช้เมื่อ:</p>
                  <ul className="list-disc ml-5 space-y-1 text-gray-600">
                    <li>กดสถานะผิดพลาด ต้องการเปลี่ยนใหม่</li>
                    <li>ต้องการยกเลิกการตรวจสอบที่ทำไปแล้ว</li>
                    <li>ต้องการให้หน้านี้กลับเป็นสถานะ "รอตรวจ"</li>
                  </ul>
                  <p className="text-xs text-gray-500 mt-2">หมายเหตุ: สถานะจะกลับเป็น "รอตรวจ" แต่ค่าแก้ไขและหมายเหตุจะยังอยู่</p>
                </>
              )}
            </div>
            <div className="px-5 py-3 bg-gray-50 border-t flex gap-2 justify-end">
              <button onClick={() => setConfirmAction(null)} className="px-4 py-1.5 text-sm rounded border border-gray-300 text-gray-600 hover:bg-gray-100 transition">
                ยกเลิก
              </button>
              <button
                onClick={() => { onSetStatus(confirmAction); setConfirmAction(null) }}
                className={`px-4 py-1.5 text-sm font-medium rounded text-white transition ${
                  confirmAction === 'confirmed' ? 'bg-green-600 hover:bg-green-700' :
                  confirmAction === 'flagged' ? 'bg-amber-500 hover:bg-amber-600' :
                  confirmAction === 'rejected' ? 'bg-red-600 hover:bg-red-700' :
                  'bg-gray-600 hover:bg-gray-700'
                }`}
              >
                {confirmAction === 'confirmed' ? '✅ ยืนยัน ข้อมูลถูกต้อง' :
                 confirmAction === 'flagged' ? '🔄 ยืนยัน ตรวจอีกรอบ' :
                 confirmAction === 'rejected' ? '🚫 ยืนยัน ใช้ไม่ได้' :
                 '↩ ยืนยัน รีเซ็ต'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Review section */}
      <div className="border-t bg-gray-50 px-4 py-3">
        <textarea
          className="w-full px-3 py-2 border rounded text-sm resize-y min-h-[32px] mb-2"
          placeholder="บันทึกหมายเหตุ..."
          value={review.note || ''}
          onBlur={e => onSetNote(e.target.value)}
          onChange={e => onSetNote(e.target.value)}
        />
        <div className="flex gap-2 justify-end">
          <button onClick={() => setConfirmAction('confirmed')} className="px-3 py-1.5 text-sm font-medium rounded bg-green-600 text-white hover:bg-green-700 transition">
            ✅ ยืนยัน
          </button>
          <button onClick={() => setConfirmAction('flagged')} className="px-3 py-1.5 text-sm font-medium rounded bg-amber-500 text-white hover:bg-amber-600 transition">
            🔄 ตรวจอีกรอบ
          </button>
          <button onClick={() => setConfirmAction('rejected')} className="px-3 py-1.5 text-sm font-medium rounded bg-red-600 text-white hover:bg-red-700 transition">
            🚫 ใช้ไม่ได้
          </button>
          <button onClick={() => setConfirmAction('pending')} className="px-3 py-1.5 text-sm font-medium rounded bg-gray-200 text-gray-700 hover:bg-gray-300 transition">
            ↩ รีเซ็ต
          </button>
        </div>
      </div>
    </div>
  )
}

export default function ReviewCard(props) {
  return (
    <ErrorBoundary compact>
      <ReviewCardInner {...props} />
    </ErrorBoundary>
  )
}
