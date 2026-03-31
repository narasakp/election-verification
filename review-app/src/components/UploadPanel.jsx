import React, { useState, useRef, useCallback, useEffect } from 'react'
import { Upload, FolderUp, FileArchive, X, CheckCircle, AlertCircle, Loader2, RefreshCw, Play, Link2, ExternalLink } from 'lucide-react'
import ErrorBoundary from './ErrorBoundary'

const ACCEPTED_TYPES = '.pdf,.zip,.rar,.7z,.tar,.tar.gz,.tgz'

function UploadPanelInner({ onClose, onDataRefresh }) {
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState(null)
  const [provinces, setProvinces] = useState([])
  const [loadingProvinces, setLoadingProvinces] = useState(true)
  const [selectedProvince, setSelectedProvince] = useState('')
  const [selectedConstituency, setSelectedConstituency] = useState('')
  const [ocrJobs, setOcrJobs] = useState({})
  const [preparing, setPreparing] = useState(false)
  const [driveUrl, setDriveUrl] = useState('')
  const [driveImporting, setDriveImporting] = useState(false)
  const [driveJobs, setDriveJobs] = useState({})
  const [drivePreview, setDrivePreview] = useState(null)
  const [drivePreviewing, setDrivePreviewing] = useState(false)
  const fileInputRef = useRef(null)
  const folderInputRef = useRef(null)

  // Load provinces list
  const fetchProvinces = useCallback(() => {
    setLoadingProvinces(true)
    fetch('/api/provinces')
      .then(r => r.json())
      .then(data => { setProvinces(data.provinces || []); setLoadingProvinces(false) })
      .catch(() => setLoadingProvinces(false))
  }, [])

  useEffect(() => { fetchProvinces() }, [fetchProvinces])

  // Upload files
  const doUpload = useCallback(async (files) => {
    if (!files || files.length === 0) return
    setUploading(true)
    setUploadResult(null)

    const formData = new FormData()
    for (const f of files) {
      formData.append('files[]', f, f.webkitRelativePath || f.name)
    }
    if (selectedProvince) formData.append('province', selectedProvince)
    if (selectedConstituency) formData.append('constituency', selectedConstituency)

    try {
      const res = await fetch('/api/upload', { method: 'POST', body: formData })
      const data = await res.json()
      if (res.ok) {
        setUploadResult({ type: 'success', data })
        fetchProvinces()
      } else {
        setUploadResult({ type: 'error', message: data.error || 'Upload failed' })
      }
    } catch (err) {
      setUploadResult({ type: 'error', message: err.message })
    } finally {
      setUploading(false)
    }
  }, [selectedProvince, selectedConstituency, fetchProvinces])

  // Drag & drop handlers
  const handleDragOver = (e) => { e.preventDefault(); setDragging(true) }
  const handleDragLeave = () => setDragging(false)
  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    const files = e.dataTransfer.files
    if (files.length > 0) doUpload(files)
  }

  // File input handlers
  const handleFileSelect = (e) => {
    if (e.target.files.length > 0) doUpload(e.target.files)
    e.target.value = ''
  }

  // Google Drive preview
  const previewDriveFolder = async () => {
    if (!driveUrl.trim()) return
    setDrivePreviewing(true)
    setDrivePreview(null)
    try {
      const res = await fetch('/api/drive-preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: driveUrl }),
      })
      const data = await res.json()
      if (!res.ok) {
        setUploadResult({ type: 'error', message: data.error || 'Preview failed' })
      } else {
        setDrivePreview(data)
      }
    } catch (err) {
      setUploadResult({ type: 'error', message: err.message })
    } finally {
      setDrivePreviewing(false)
    }
  }

  // Google Drive import
  const triggerDriveImport = async () => {
    if (!driveUrl.trim()) return
    setDriveImporting(true)
    try {
      const res = await fetch('/api/import-drive', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: driveUrl, province: selectedProvince }),
      })
      const data = await res.json()
      if (!res.ok) {
        setUploadResult({ type: 'error', message: data.error || 'Drive import failed' })
      } else if (data.job_id) {
        setDriveJobs(prev => ({ ...prev, [data.job_id]: { status: 'running', folder_id: data.folder_id } }))
        pollJob(data.job_id, true)
        setDrivePreview(null)
        setDriveUrl('')
        setUploadResult({ type: 'success', data: { summary: {}, message: 'เริ่มนำเข้าจาก Google Drive แล้ว — ดูสถานะด้านล่าง' } })
      }
    } catch (err) {
      setUploadResult({ type: 'error', message: err.message })
    } finally {
      setDriveImporting(false)
    }
  }

  // OCR trigger
  const triggerOcr = async (province) => {
    try {
      const res = await fetch('/api/ocr', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          province,
          options: { all: true, debug: true, resume: true, ss518_only: true },
        }),
      })
      const data = await res.json()
      if (data.job_id) {
        setOcrJobs(prev => ({ ...prev, [data.job_id]: { status: 'running', province } }))
        pollJob(data.job_id)
      }
    } catch (err) {
      alert(`OCR error: ${err.message}`)
    }
  }

  // Poll job status (works for both OCR and Drive import jobs)
  const pollJob = (jobId, isDrive = false) => {
    const pollMs = isDrive ? 1500 : 3000
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/jobs/${jobId}`)
        const data = await res.json()
        if (isDrive) {
          setDriveJobs(prev => ({ ...prev, [jobId]: data }))
        } else {
          setOcrJobs(prev => ({ ...prev, [jobId]: data }))
        }
        if (data.status !== 'running') {
          clearInterval(interval)
          fetchProvinces()
        }
      } catch {
        clearInterval(interval)
      }
    }, pollMs)
  }

  // Prepare review data
  const triggerPrepare = async () => {
    setPreparing(true)
    try {
      const res = await fetch('/api/prepare', { method: 'POST' })
      const data = await res.json()
      if (data.success) {
        onDataRefresh?.()
        alert('สร้างข้อมูล review สำเร็จ! กดปุ่มรีเฟรชหน้าเพื่อดูข้อมูลใหม่')
      } else {
        alert(`Error: ${data.error || data.output}`)
      }
    } catch (err) {
      alert(`Error: ${err.message}`)
    } finally {
      setPreparing(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-[100] flex items-start justify-center pt-10 overflow-auto">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl mx-4 mb-10">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b bg-gradient-to-r from-emerald-50 to-teal-50">
          <div>
            <h2 className="text-lg font-bold text-gray-800 flex items-center gap-2">📤 อัปโหลดข้อมูลจังหวัด</h2>
            <p className="text-xs text-gray-500 mt-0.5">นำเข้าไฟล์ PDF แบบ สส.5/16 เพื่อให้ระบบ OCR อ่านและสร้างข้อมูล Review</p>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-gray-200 rounded-full transition">
            <X size={20} />
          </button>
        </div>

        {/* Guide */}
        <div className="px-6 pt-4 pb-0">
          <details className="group">
            <summary className="flex items-center gap-2 text-xs font-semibold text-indigo-600 cursor-pointer hover:text-indigo-800 select-none">
              <span className="w-5 h-5 bg-indigo-100 rounded flex items-center justify-center text-[10px]">❓</span>
              วิธีใช้งาน — คลิกเพื่อดูคำอธิบาย
            </summary>
            <div className="mt-2 bg-indigo-50 border border-indigo-100 rounded-lg p-4 text-sm text-gray-700 space-y-3">
              <div>
                <p className="font-semibold text-indigo-800 mb-1">📌 หน้าที่:</p>
                <p className="text-gray-600">อัปโหลดไฟล์ PDF แบบ สส.5/16 (ผลคะแนนเลือกตั้งรายหน่วย) เข้าสู่ระบบ เพื่อให้ OCR อ่านค่าอัตโนมัติ แล้วส่งเข้าหน้า Review ให้อาสาตรวจสอบ</p>
              </div>
              <div>
                <p className="font-semibold text-indigo-800 mb-1">📋 ขั้นตอน:</p>
                <ol className="list-decimal ml-5 space-y-1 text-gray-600">
                  <li><strong>เลือกจังหวัด/เขต</strong> (ถ้าต้องการบังคับ) หรือปล่อยว่างให้ตรวจอัตโนมัติจากชื่อโฟลเดอร์</li>
                  <li><strong>อัปโหลดไฟล์</strong> — ลากวาง, เลือกไฟล์ PDF, เลือกโฟลเดอร์, หรือวาง URL Google Drive</li>
                  <li><strong>รอระบบประมวลผล</strong> — ระบบจะจัดเรียงไฟล์ตามจังหวัด/เขตอัตโนมัติ</li>
                  <li><strong>กดปุ่ม OCR</strong> — ในตารางจังหวัด เพื่อเริ่มอ่านค่าจาก PDF</li>
                  <li><strong>กด "สร้างข้อมูล Review"</strong> — เพื่อสร้างข้อมูลให้หน้า Review ใช้งาน</li>
                </ol>
              </div>
              <div>
                <p className="font-semibold text-indigo-800 mb-1">📁 รูปแบบไฟล์ที่รองรับ:</p>
                <ul className="list-disc ml-5 space-y-0.5 text-gray-600">
                  <li><strong>.pdf</strong> — ไฟล์ PDF เดี่ยว หรือหลายไฟล์พร้อมกัน</li>
                  <li><strong>.zip / .rar / .7z / .tar.gz</strong> — ไฟล์บีบอัดที่มี PDF อยู่ข้างใน</li>
                  <li><strong>Google Drive URL</strong> — วาง URL โฟลเดอร์ที่แชร์สาธารณะ</li>
                </ul>
              </div>
            </div>
          </details>
        </div>

        <div className="p-6 pt-4 space-y-6">
          {/* Province/Constituency override */}
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-600 mb-1">จังหวัด (ถ้าระบุ จะบังคับใช้)</label>
              <input
                type="text"
                list="province-list"
                value={selectedProvince}
                onChange={e => setSelectedProvince(e.target.value)}
                placeholder="ปล่อยว่างเพื่อตรวจจากชื่อโฟลเดอร์อัตโนมัติ"
                className="w-full px-3 py-2 border rounded text-sm"
              />
              <datalist id="province-list">
                {Object.keys(PROVINCE_NAMES).map(p => (
                  <option key={p} value={p} />
                ))}
              </datalist>
            </div>
            <div className="w-32">
              <label className="block text-sm font-medium text-gray-600 mb-1">เขต</label>
              <input
                type="number"
                min="1"
                value={selectedConstituency}
                onChange={e => setSelectedConstituency(e.target.value)}
                placeholder="อัตโนมัติ"
                className="w-full px-3 py-2 border rounded text-sm"
              />
            </div>
          </div>

          {/* Drop zone */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
              dragging ? 'border-indigo-500 bg-indigo-50' : 'border-gray-300 hover:border-gray-400'
            }`}
          >
            {uploading ? (
              <div className="flex flex-col items-center gap-3">
                <Loader2 size={40} className="animate-spin text-indigo-500" />
                <p className="text-sm text-gray-600">กำลังอัปโหลด...</p>
              </div>
            ) : (
              <>
                <Upload size={40} className="mx-auto mb-3 text-gray-400" />
                <p className="text-gray-600 mb-1">ลากไฟล์มาวางที่นี่</p>
                <p className="text-xs text-gray-400 mb-4">รองรับ: .pdf .zip .rar .7z .tar.gz</p>
                <div className="flex gap-3 justify-center">
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700 transition"
                  >
                    <FileArchive size={16} /> เลือกไฟล์
                  </button>
                  <button
                    onClick={() => folderInputRef.current?.click()}
                    className="flex items-center gap-2 px-4 py-2 bg-white border border-indigo-600 text-indigo-600 rounded-lg text-sm hover:bg-indigo-50 transition"
                  >
                    <FolderUp size={16} /> เลือกโฟลเดอร์
                  </button>
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept={ACCEPTED_TYPES}
                  className="hidden"
                  onChange={handleFileSelect}
                />
                <input
                  ref={folderInputRef}
                  type="file"
                  webkitdirectory=""
                  directory=""
                  multiple
                  className="hidden"
                  onChange={handleFileSelect}
                />
              </>
            )}
          </div>

          {/* Google Drive import */}
          <div className="border rounded-xl p-4 bg-blue-50/50">
            <h3 className="text-sm font-bold text-gray-700 mb-2 flex items-center gap-1.5">
              <ExternalLink size={14} className="text-blue-600" />
              นำเข้าจาก Google Drive (กกต.)
            </h3>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Link2 size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="url"
                  value={driveUrl}
                  onChange={e => { setDriveUrl(e.target.value); setDrivePreview(null) }}
                  placeholder="วาง URL โฟลเดอร์ Google Drive ที่นี่..."
                  className="w-full pl-8 pr-3 py-2 border rounded text-sm bg-white"
                  onKeyDown={e => { if (e.key === 'Enter') previewDriveFolder() }}
                />
              </div>
              <button
                onClick={previewDriveFolder}
                disabled={drivePreviewing || !driveUrl.trim()}
                className="flex items-center gap-1.5 px-3 py-2 bg-white border border-blue-400 text-blue-600 rounded text-sm hover:bg-blue-50 transition disabled:opacity-50 whitespace-nowrap"
              >
                {drivePreviewing ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                สแกน
              </button>
              <button
                onClick={triggerDriveImport}
                disabled={driveImporting || !driveUrl.trim()}
                className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition disabled:opacity-50 whitespace-nowrap"
              >
                {driveImporting ? <Loader2 size={14} className="animate-spin" /> : <ExternalLink size={14} />}
                นำเข้า
              </button>
            </div>
            <p className="text-[11px] text-gray-400 mt-1.5">
              วาง URL โฟลเดอร์ที่แชร์สาธารณะ เช่น https://drive.google.com/drive/folders/... — ไม่ต้องตั้งค่าอะไรเพิ่ม
            </p>

            {/* Drive folder preview */}
            {drivePreview && (
              <div className="mt-3 border rounded-lg bg-white overflow-hidden">
                <div className="px-3 py-2 bg-gray-50 text-xs font-semibold text-gray-600 flex justify-between">
                  <span>📂 เนื้อหาในโฟลเดอร์ {drivePreview.method === 'public' ? '(public)' : '(API)'}</span>
                  <span className="text-gray-400">
                    {drivePreview.total_subfolders} โฟลเดอร์, {drivePreview.top_level_pdfs} PDF (root)
                  </span>
                </div>
                {drivePreview.subfolders.length > 0 ? (
                  <div className="max-h-[200px] overflow-y-auto">
                    <table className="w-full text-xs">
                      <tbody>
                        {drivePreview.subfolders.map((sf, i) => (
                          <tr key={i} className="border-t hover:bg-gray-50">
                            <td className="px-3 py-1.5 font-medium">📁 {sf.name}</td>
                            <td className="px-3 py-1.5 text-right text-gray-500">
                              {sf.pdf_count} PDF{sf.subfolder_count > 0 ? `, ${sf.subfolder_count} subfolder` : ''}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="px-3 py-2 text-xs text-gray-400">ไม่พบโฟลเดอร์ย่อย</div>
                )}
              </div>
            )}
          </div>

          {/* Upload result */}
          {uploadResult && (
            <div className={`rounded-lg p-4 ${uploadResult.type === 'success' ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
              <div className="flex items-start gap-2">
                {uploadResult.type === 'success' ? (
                  <CheckCircle size={18} className="text-green-600 mt-0.5" />
                ) : (
                  <AlertCircle size={18} className="text-red-600 mt-0.5" />
                )}
                <div className="flex-1 text-sm">
                  {uploadResult.type === 'success' ? (
                    <>
                      <p className="font-semibold text-green-800">
                        {uploadResult.data.message || 'อัปโหลดสำเร็จ!'}
                      </p>
                      {uploadResult.data.summary && Object.entries(uploadResult.data.summary).map(([prov, info]) => (
                        info.pdfs != null && (
                          <p key={prov} className="text-green-700 mt-1">
                            📍 {prov}: {info.pdfs} ไฟล์ PDF, {info.constituencies} เขต
                          </p>
                        )
                      ))}
                    </>
                  ) : (
                    <p className="text-red-800">{uploadResult.message}</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Province table */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-bold text-gray-700">📊 จังหวัดในระบบ</h3>
              <div className="flex gap-2">
                <button onClick={fetchProvinces} className="flex items-center gap-1 px-2 py-1 text-xs bg-gray-100 rounded hover:bg-gray-200">
                  <RefreshCw size={12} /> รีเฟรช
                </button>
                <button
                  onClick={triggerPrepare}
                  disabled={preparing}
                  className="flex items-center gap-1 px-3 py-1 text-xs bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
                >
                  {preparing ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
                  สร้างข้อมูล Review
                </button>
              </div>
            </div>

            {loadingProvinces ? (
              <div className="text-center py-4 text-gray-400 text-sm">กำลังโหลด...</div>
            ) : provinces.length === 0 ? (
              <div className="text-center py-4 text-gray-400 text-sm">ยังไม่มีข้อมูลจังหวัด</div>
            ) : (
              <div className="border rounded-lg overflow-hidden max-h-[300px] overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="text-left px-3 py-2 font-semibold text-gray-600">จังหวัด</th>
                      <th className="text-center px-3 py-2 font-semibold text-gray-600">เขต</th>
                      <th className="text-center px-3 py-2 font-semibold text-gray-600">PDF</th>
                      <th className="text-center px-3 py-2 font-semibold text-gray-600">OCR</th>
                      <th className="text-center px-3 py-2 font-semibold text-gray-600">สถานะ</th>
                      <th className="text-center px-3 py-2 font-semibold text-gray-600"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {provinces.map(p => {
                      const jobForProv = Object.values(ocrJobs).find(j => j.province === p.name && j.status === 'running')
                      return (
                        <tr key={p.slug} className="border-t hover:bg-gray-50">
                          <td className="px-3 py-2 font-medium">{p.name}</td>
                          <td className="px-3 py-2 text-center">{p.constituency_count}</td>
                          <td className="px-3 py-2 text-center">{p.pdf_count}</td>
                          <td className="px-3 py-2 text-center">{p.ocr_count || '—'}</td>
                          <td className="px-3 py-2 text-center">
                            {jobForProv ? (
                              <span className="inline-flex items-center gap-1 text-xs text-amber-600">
                                <Loader2 size={12} className="animate-spin" /> OCR...
                              </span>
                            ) : p.has_ocr ? (
                              <span className="text-xs text-green-600 font-semibold">✅ พร้อม</span>
                            ) : p.pdf_count > 0 ? (
                              <span className="text-xs text-gray-400">รอ OCR</span>
                            ) : (
                              <span className="text-xs text-gray-300">ว่าง</span>
                            )}
                          </td>
                          <td className="px-3 py-2 text-center">
                            {p.pdf_count > 0 && !jobForProv && (
                              <button
                                onClick={() => triggerOcr(p.name)}
                                className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-amber-100 text-amber-700 rounded hover:bg-amber-200"
                                title="เริ่ม OCR"
                              >
                                <Play size={10} /> OCR
                              </button>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Running jobs (Drive import + OCR) */}
          {(Object.entries(driveJobs).filter(([, j]) => j.status === 'running').length > 0 ||
            Object.entries(ocrJobs).filter(([, j]) => j.status === 'running').length > 0) && (
            <div className="space-y-2">
              <h3 className="text-sm font-bold text-gray-700">⚙️ กำลังประมวลผล</h3>
              {Object.entries(driveJobs).filter(([, j]) => j.status === 'running').map(([id, job]) => (
                <div key={id} className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm font-medium text-blue-800">
                      <Loader2 size={14} className="animate-spin" />
                      Google Drive Import
                    </div>
                    <button
                      onClick={async () => {
                        await fetch(`/api/jobs/${id}`, { method: 'DELETE' })
                        setDriveJobs(prev => { const n = { ...prev }; delete n[id]; return n })
                      }}
                      className="px-2 py-0.5 text-[10px] bg-red-100 text-red-600 rounded hover:bg-red-200"
                      title="ยกเลิก"
                    >✕ ยกเลิก</button>
                  </div>

                  {/* Progress bar */}
                  {job.total_count > 0 && (
                    <div className="mt-2">
                      <div className="flex items-center justify-between text-xs text-blue-700 mb-1">
                        <span>
                          ⬇️ {job.downloaded_count || 0}/{job.total_count} ไฟล์
                          {job.error_count > 0 && <span className="text-red-500 ml-1">({job.error_count} ผิดพลาด)</span>}
                        </span>
                        <span className="font-bold">{job.percent || 0}%</span>
                      </div>
                      <div className="w-full bg-blue-200 rounded-full h-2.5 overflow-hidden">
                        <div
                          className="bg-blue-600 h-full rounded-full transition-all duration-500 ease-out"
                          style={{ width: `${job.percent || 0}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Current action */}
                  {job.progress && !job.total_count && (
                    <p className="mt-1.5 text-xs text-blue-600">{job.progress}</p>
                  )}

                  {job.log && (
                    <pre className="mt-2 text-[10px] text-gray-600 bg-white rounded p-2 max-h-32 overflow-auto font-mono">
                      {job.log.split('\n').slice(-15).join('\n')}
                    </pre>
                  )}
                </div>
              ))}
              {Object.entries(ocrJobs).filter(([, j]) => j.status === 'running').map(([id, job]) => (
                <div key={id} className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                  <div className="flex items-center gap-2 text-sm font-medium text-amber-800">
                    <Loader2 size={14} className="animate-spin" />
                    OCR: {job.province}
                  </div>
                  {job.log && (
                    <pre className="mt-2 text-[10px] text-gray-600 bg-white rounded p-2 max-h-24 overflow-auto font-mono">
                      {job.log.split('\n').slice(-10).join('\n')}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function UploadPanel(props) {
  return (
    <ErrorBoundary compact>
      <UploadPanelInner {...props} />
    </ErrorBoundary>
  )
}

// Province list for autocomplete
const PROVINCE_NAMES = {
  'กรุงเทพมหานคร': true, 'กระบี่': true, 'กาญจนบุรี': true, 'กาฬสินธุ์': true,
  'กำแพงเพชร': true, 'ขอนแก่น': true, 'จันทบุรี': true, 'ฉะเชิงเทรา': true,
  'ชลบุรี': true, 'ชัยนาท': true, 'ชัยภูมิ': true, 'ชุมพร': true,
  'เชียงราย': true, 'เชียงใหม่': true, 'ตรัง': true, 'ตราด': true, 'ตาก': true,
  'นครนายก': true, 'นครปฐม': true, 'นครพนม': true, 'นครราชสีมา': true,
  'นครศรีธรรมราช': true, 'นครสวรรค์': true, 'นนทบุรี': true, 'นราธิวาส': true,
  'น่าน': true, 'บึงกาฬ': true, 'บุรีรัมย์': true, 'ปทุมธานี': true,
  'ประจวบคีรีขันธ์': true, 'ปราจีนบุรี': true, 'ปัตตานี': true, 'พระนครศรีอยุธยา': true,
  'พะเยา': true, 'พังงา': true, 'พัทลุง': true, 'พิจิตร': true, 'พิษณุโลก': true,
  'เพชรบุรี': true, 'เพชรบูรณ์': true, 'แพร่': true, 'ภูเก็ต': true,
  'มหาสารคาม': true, 'มุกดาหาร': true, 'แม่ฮ่องสอน': true, 'ยโสธร': true,
  'ยะลา': true, 'ร้อยเอ็ด': true, 'ระนอง': true, 'ระยอง': true, 'ราชบุรี': true,
  'ลพบุรี': true, 'ลำปาง': true, 'ลำพูน': true, 'เลย': true, 'ศรีสะเกษ': true,
  'สกลนคร': true, 'สงขลา': true, 'สตูล': true, 'สมุทรปราการ': true,
  'สมุทรสงคราม': true, 'สมุทรสาคร': true, 'สระแก้ว': true, 'สระบุรี': true,
  'สิงห์บุรี': true, 'สุโขทัย': true, 'สุพรรณบุรี': true, 'สุราษฎร์ธานี': true,
  'สุรินทร์': true, 'หนองคาย': true, 'หนองบัวลำภู': true, 'อ่างทอง': true,
  'อำนาจเจริญ': true, 'อุดรธานี': true, 'อุตรดิตถ์': true, 'อุทัยธานี': true,
  'อุบลราชธานี': true,
}
