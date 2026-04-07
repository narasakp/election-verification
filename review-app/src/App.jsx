import React, { useState, useEffect, useCallback, useMemo, Suspense, lazy } from 'react'
import ReviewCard from './components/ReviewCard'
import FilterBar from './components/FilterBar'
import StatsBar from './components/StatsBar'
import AuthGate from './components/AuthGate'
import ToastContainer, { toast } from './components/Toast'

// Lazy-loaded heavy components (code splitting)
const DataStatsPanel = lazy(() => import('./components/DataStatsPanel'))
const BackupDashboard = lazy(() => import('./components/BackupDashboard'))
const AnalyticsDashboard = lazy(() => import('./components/AnalyticsDashboard'))
const ProvinceHeatmap = lazy(() => import('./components/ProvinceHeatmap'))
const ReviewerLeaderboard = lazy(() => import('./components/ReviewerLeaderboard'))
const CrossReferencePanel = lazy(() => import('./components/CrossReferencePanel'))
const UploadPanel = lazy(() => import('./components/UploadPanel'))
const AdminPanel = lazy(() => import('./components/AdminPanel'))
const AnomalySummaryPanel = lazy(() => import('./components/AnomalySummaryPanel'))
import useAuth from './hooks/useAuth'
import useDarkMode from './hooks/useDarkMode'
import useExport from './hooks/useExport'
import useKeyboardShortcuts from './hooks/useKeyboardShortcuts'
import { submitToGoogleForm, submitLoginEvent, submitLogoutEvent } from './utils/submitReview'
import { getReviewLog, appendReviewLog, getAllSummaries, getUserReviewKey, checkRateLimit, recordReviewTiming, validateEditValue, getAllAnomalyScores, mergeReviewLogs, verifyLogIntegrity } from './utils/reviewLog'
import { validateItem, getWorstSeverity, isLowRiskItem } from './utils/validation'
import { computeItemAnomalyScore } from './utils/anomalyScore'
import { ChevronLeft, ChevronRight, Download, Upload, FolderUp, LogOut, ShieldCheck, ChevronDown, Filter, Moon, Sun, Menu, X } from 'lucide-react'

const DATA_URL = './data/review_data.json'
const ANOMALY_FLAGS_URL = './data/anomaly_flags.json'


function App() {
  const { user, loading: authLoading, signOut, renderButton } = useAuth()
  const { dark, toggle: toggleDark } = useDarkMode()
  const [prevUser, setPrevUser] = useState(null)
  const [allItems, setAllItems] = useState([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [review, setReview] = useState({}) // keyed by item.id → { status, note, edits }
  const [reviewLog, setReviewLog] = useState([])
  const [sharedEdits, setSharedEdits] = useState({}) // keyed by "province__constituency" → { field: value }
  const [filterStatus, setFilterStatus] = useState('all')
  const [filterProvince, setFilterProvince] = useState('ชัยภูมิ')
  const [filterConstituency, setFilterConstituency] = useState('1')
  const [searchText, setSearchText] = useState('')
  const [filterVoteType, setFilterVoteType] = useState('แบ่งเขต')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showUpload, setShowUpload] = useState(false)
  const [showExportMenu, setShowExportMenu] = useState(false)
  const [showImportInfo, setShowImportInfo] = useState(false)
  const [rateLimitWarning, setRateLimitWarning] = useState(null)
  const [showAdminPanel, setShowAdminPanel] = useState(false)
  const [anomalyFlags, setAnomalyFlags] = useState({})
  const [anomalyMeta, setAnomalyMeta] = useState(null)
  const [autoApproveEnabled, setAutoApproveEnabled] = useState(false)
  const [bulkOperationInProgress, setBulkOperationInProgress] = useState(false)
  const [priorityQueueEnabled, setPriorityQueueEnabled] = useState(false)
  const [activeDashboard, setActiveDashboard] = useState(null)
  const [showMobileMenu, setShowMobileMenu] = useState(false)
  const [fbOpen, setFbOpen] = useState(false)
  const [fbMsg, setFbMsg] = useState('')
  const exportMenuRef = React.useRef(null)
  const mobileMenuRef = React.useRef(null)

  // Close export menu on outside click
  useEffect(() => {
    if (!showExportMenu) return
    const handler = (e) => {
      if (exportMenuRef.current && !exportMenuRef.current.contains(e.target)) setShowExportMenu(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [showExportMenu])

  // Close mobile menu on outside click
  useEffect(() => {
    if (!showMobileMenu) return
    const handler = (e) => {
      if (mobileMenuRef.current && !mobileMenuRef.current.contains(e.target)) setShowMobileMenu(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [showMobileMenu])

  // Load data
  const loadData = useCallback(() => {
    setLoading(true)
    fetch(DATA_URL)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then(data => { setAllItems(data); setLoading(false); setError(null) })
      .catch(err => { setError(err.message); setLoading(false) })
  }, [])

  useEffect(() => { loadData() }, [loadData])

  // Load anomaly flags (constituency-level ECT anomalies)
  useEffect(() => {
    fetch(ANOMALY_FLAGS_URL)
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (d?.flags_by_prov_con) setAnomalyFlags(d.flags_by_prov_con)
        if (d?.metadata) setAnomalyMeta(d.metadata)
      })
      .catch(() => {}) // silently ignore if not available
  }, [])

  // Load saved review from per-user localStorage + global review log
  useEffect(() => {
    if (!user) return
    const key = getUserReviewKey(user.email)
    const saved = localStorage.getItem(key)
    if (saved) { try { setReview(JSON.parse(saved)) } catch {} }
    // Also try migrating from old key if per-user is empty
    if (!saved) {
      const old = localStorage.getItem('ocr_review_v2')
      if (old) { try { setReview(JSON.parse(old)) } catch {} }
    }
    // Load shared edits
    const shKey = `ocr_shared_edits_${user.email || 'anon'}`
    const shSaved = localStorage.getItem(shKey)
    if (shSaved) { try { setSharedEdits(JSON.parse(shSaved)) } catch {} }
    setReviewLog(getReviewLog())
  }, [user])

  // Persist review (per-user)
  useEffect(() => {
    if (!user) return
    if (Object.keys(review).length > 0) {
      localStorage.setItem(getUserReviewKey(user.email), JSON.stringify(review))
    }
  }, [review, user])

  // Persist shared edits
  useEffect(() => {
    if (!user) return
    if (Object.keys(sharedEdits).length > 0) {
      localStorage.setItem(`ocr_shared_edits_${user.email || 'anon'}`, JSON.stringify(sharedEdits))
    }
  }, [sharedEdits, user])

  // Unique provinces for filter
  const provinces = useMemo(() => {
    const set = new Set()
    allItems.forEach(d => { if (d.province) set.add(d.province) })
    return [...set].sort()
  }, [allItems])

  // Unique constituencies for filter — dynamic based on selected province
  const constituencies = useMemo(() => {
    const set = new Set()
    allItems.forEach(d => {
      if (d.constituency && (filterProvince === 'all' || d.province === filterProvince))
        set.add(d.constituency)
    })
    return [...set].sort((a, b) => a - b)
  }, [allItems, filterProvince])

  // Reset constituency when province actually changes (preserves default on mount)
  const prevProvinceRef = React.useRef(filterProvince)
  useEffect(() => {
    if (prevProvinceRef.current !== filterProvince) {
      setFilterConstituency('all')
      prevProvinceRef.current = filterProvince
    }
  }, [filterProvince])

  // Filtered items
  const filteredItems = useMemo(() => {
    return allItems.filter(item => {
      const rev = review[item.id] || {}
      const status = rev.status || 'pending'
      // Status filter
      if (filterStatus === 'pending' && status !== 'pending') return false
      if (filterStatus === 'confirmed' && status !== 'confirmed') return false
      if (filterStatus === 'flagged' && status !== 'flagged') return false
      if (filterStatus === 'rejected' && status !== 'rejected') return false
      if (filterStatus === 'low') {
        if (!item.confidence || !Object.values(item.confidence).some(c => c && c.startsWith('low'))) return false
      }
      if (filterStatus === 'no_data') {
        const hasData = ['registered_voters', 'turnout', 'ballots_received', 'valid_ballots']
          .some(f => item[f] != null)
        if (hasData) return false
      }
      if (filterStatus === 'with_candidates') {
        if (!item.candidates || item.candidates.length === 0) return false
      }
      if (filterStatus === 'vision_ocr') {
        if (item._source_type !== 'vision') return false
      }
      if (filterStatus === 'no_station') {
        if (item.ocr_station_no || item.station_no) return false
      }
      if (filterStatus === 'cand_mismatch') {
        if (!item._candidate_mismatch) return false
      }
      if (filterStatus === 'anomaly') {
        const flags = anomalyFlags[`${item.province}_${item.constituency}`] || null
        const { score } = computeItemAnomalyScore(item, flags)
        if (score === 0) return false
      }
      if (filterStatus === 'has_errors') {
        const w = validateItem(item)
        if (!w.some(v => v.severity === 'error')) return false
      }
      if (filterStatus === 'has_warnings') {
        const w = validateItem(item)
        if (w.length === 0) return false
      }
      // Province filter
      if (filterProvince !== 'all' && item.province !== filterProvince) return false
      // Constituency filter
      if (filterConstituency !== 'all' && String(item.constituency) !== filterConstituency) return false
      // Vote type filter
      if (filterVoteType !== 'all') {
        const vt = item.vote_type || 'ไม่ระบุ'
        if (vt !== filterVoteType) return false
      }
      // Search
      if (searchText) {
        const hay = `${item.file || ''} ${item.sub_district || ''} ${item.district || ''} ${item.province || ''}`.toLowerCase()
        if (!hay.includes(searchText.toLowerCase())) return false
      }
      return true
    })
  }, [allItems, review, filterStatus, filterProvince, filterConstituency, filterVoteType, searchText, anomalyFlags])

  // Anomaly score map — computed for filtered items, sorted when anomaly filter is active or priority queue enabled
  const { sortedFilteredItems, anomalyScoreMap } = useMemo(() => {
    const scoreMap = {}
    filteredItems.forEach(item => {
      const flags = anomalyFlags[`${item.province}_${item.constituency}`] || null
      scoreMap[item.id] = computeItemAnomalyScore(item, flags)
    })
    
    let sorted = [...filteredItems]
    if (filterStatus === 'anomaly') {
      // Sort by anomaly score (high to low)
      sorted.sort((a, b) => (scoreMap[b.id]?.score || 0) - (scoreMap[a.id]?.score || 0))
    } else if (priorityQueueEnabled && filterStatus === 'pending') {
      // Priority queue: sort pending items by anomaly score (high anomaly first)
      sorted.sort((a, b) => (scoreMap[b.id]?.score || 0) - (scoreMap[a.id]?.score || 0))
    } else {
      // Default: items with online image (pdf_url) first, no-image items last
      sorted.sort((a, b) => {
        if (a.pdf_url && !b.pdf_url) return -1
        if (!a.pdf_url && b.pdf_url) return 1
        return 0
      })
    }

    return { sortedFilteredItems: sorted, anomalyScoreMap: scoreMap }
  }, [filteredItems, anomalyFlags, filterStatus, priorityQueueEnabled])

  // Reset index when filter changes
  useEffect(() => { setCurrentIndex(0) }, [filterStatus, filterProvince, filterConstituency, filterVoteType, searchText])

  const currentItem = sortedFilteredItems[currentIndex] || null

  // Detect first page of each constituency (for shared edits)
  const constituencyFirstPages = useMemo(() => {
    const first = {}
    filteredItems.forEach(item => {
      const key = `${item.province || ''}__${item.constituency || ''}`
      if (!first[key]) first[key] = item.id
    })
    return first
  }, [filteredItems])

  const currentConstKey = currentItem ? `${currentItem.province || ''}__${currentItem.constituency || ''}` : ''
  const isFirstPage = currentItem ? constituencyFirstPages[currentConstKey] === currentItem.id : false

  const goNext = useCallback(() => {
    setCurrentIndex(i => Math.min(i + 1, sortedFilteredItems.length - 1))
  }, [sortedFilteredItems.length])

  const goPrev = useCallback(() => {
    setCurrentIndex(i => Math.max(i - 1, 0))
  }, [])

  // Review actions
  const getReview = useCallback((itemId) => review[itemId] || { status: 'pending', note: '', edits: {} }, [review])

  const setItemStatus = useCallback((itemId, status) => {
    const email = user?.email || 'anonymous'

    // Rate limiting (F2) — block if reviewing too fast (except reset)
    if (status !== 'pending') {
      const rateCheck = checkRateLimit(email)
      if (!rateCheck.allowed) {
        setRateLimitWarning(`กรุณารอ ${Math.ceil(rateCheck.waitMs / 1000)} วินาที ก่อนตรวจหน้าถัดไป`)
        setTimeout(() => setRateLimitWarning(null), 3000)
        if (rateCheck.flagged) {
          console.warn(`[ANOMALY] User ${email} flagged for rapid reviews: ${rateCheck.rapidCount} consecutive rapid reviews`)
        }
        return // Block the review
      }
      recordReviewTiming(email)
    }

    // Edit bounds validation (F3) — check all edits before saving
    const currentEdits = review[itemId]?.edits || {}
    if (status !== 'pending' && Object.keys(currentEdits).length > 0) {
      for (const [field, value] of Object.entries(currentEdits)) {
        const check = validateEditValue(field, value)
        if (!check.valid) {
          setRateLimitWarning(`⚠️ ${check.reason}`)
          setTimeout(() => setRateLimitWarning(null), 4000)
          return // Block the review
        }
      }
    }

    setReview(prev => ({
      ...prev,
      [itemId]: status === 'pending'
        ? { status: 'pending', note: '', edits: {} }
        : { ...prev[itemId], status, edits: prev[itemId]?.edits || {} }
    }))
    // Append to review log — ALL actions including reset (C1: prevents ghost votes)
    const updatedLog = appendReviewLog({
      itemId,
      email,
      name: user?.name || 'anonymous',
      status,
      note: status === 'pending' ? '(reset)' : (review[itemId]?.note || ''),
      edits: status === 'pending' ? {} : currentEdits,
    })
    setReviewLog(updatedLog)
    // Submit to Google Forms (including edits for audit trail)
    const item = allItems.find(i => i.id === itemId)
    if (item) {
      const note = review[itemId]?.note || ''
      submitToGoogleForm(item, status, note, email, status === 'pending' ? {} : currentEdits)
    }
    // Auto-advance to next item after review action
    if (status !== 'pending') {
      setTimeout(() => setCurrentIndex(i => Math.min(i + 1, sortedFilteredItems.length - 1)), 150)
    }
  }, [allItems, review, user, sortedFilteredItems.length])

  // Bulk operations
  const bulkAutoApprove = useCallback(async () => {
    if (!autoApproveEnabled) return
    
    setBulkOperationInProgress(true)
    const email = user?.email || 'anonymous'
    let approvedCount = 0
    
    for (const item of sortedFilteredItems) {
      const rev = review[item.id] || {}
      if (rev.status === 'pending' && isLowRiskItem(item)) {
        // Auto-approve low-risk pending items
        setItemStatus(item.id, 'confirmed')
        approvedCount++
        
        // Small delay to avoid overwhelming the system
        await new Promise(resolve => setTimeout(resolve, 50))
      }
    }
    
    setBulkOperationInProgress(false)
    toast(`✅ Auto-approved ${approvedCount} low-risk items`, 'success')
  }, [sortedFilteredItems, review, user, autoApproveEnabled, setItemStatus])

  const bulkConfirmAll = useCallback(async () => {
    if (!window.confirm(`⚠️ Bulk Confirm All\n\nยืนยันทั้งหมด ${sortedFilteredItems.length} รายการในหน้าจอนี้?\n\nคำเตือน: การกระทำนี้ไม่สามารถยกเลิกได้`)) return
    
    setBulkOperationInProgress(true)
    let confirmedCount = 0
    
    for (const item of sortedFilteredItems) {
      const rev = review[item.id] || {}
      if (rev.status === 'pending') {
        setItemStatus(item.id, 'confirmed')
        confirmedCount++
        await new Promise(resolve => setTimeout(resolve, 100))
      }
    }
    
    setBulkOperationInProgress(false)
    toast(`✅ Confirmed ${confirmedCount} items`, 'success')
  }, [sortedFilteredItems, review, setItemStatus])

  // Keyboard navigation (extracted to custom hook)
  useKeyboardShortcuts({
    goNext, goPrev, currentItem, setItemStatus,
    autoApproveEnabled, setAutoApproveEnabled,
    bulkAutoApprove, bulkConfirmAll,
    priorityQueueEnabled, setPriorityQueueEnabled,
  })

  const setItemNote = useCallback((itemId, note) => {
    setReview(prev => ({
      ...prev,
      [itemId]: { ...prev[itemId], note, edits: prev[itemId]?.edits || {} }
    }))
  }, [])

  const setItemEdit = useCallback((itemId, field, value, originalValue) => {
    setReview(prev => {
      const prevItem = prev[itemId] || { status: 'pending', note: '', edits: {} }
      const edits = { ...prevItem.edits }
      const origStr = String(originalValue == null ? '' : originalValue)
      if (value === origStr || (value === '' && originalValue == null)) {
        delete edits[field]
      } else {
        edits[field] = value
      }
      return { ...prev, [itemId]: { ...prevItem, edits } }
    })
  }, [])

  // Shared edit handler (constituency-level)
  const setSharedEdit = useCallback((constKey, field, value, originalValue) => {
    setSharedEdits(prev => {
      const prevConst = { ...(prev[constKey] || {}) }
      const origStr = String(originalValue == null ? '' : originalValue)
      if (value === origStr || (value === '' && originalValue == null)) {
        delete prevConst[field]
      } else {
        prevConst[field] = value
      }
      return { ...prev, [constKey]: prevConst }
    })
  }, [])

  // Export handlers (extracted to custom hook)
  const {
    handleExportJSON, handleExportCSV, handleExportFullCSV,
    handleExportFilteredJSON, handleExportFilteredCSV, handleExportAuditLog,
  } = useExport({ allItems, review, sharedEdits, filteredItems, reviewLog, user })

  const handleImport = (e) => {
    const file = e.target.files[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      try {
        const data = JSON.parse(ev.target.result)
        if (typeof data === 'object' && !Array.isArray(data)) setReview(data)
      } catch {}
    }
    reader.readAsText(file)
    e.target.value = ''
  }

  // Stats
  const stats = useMemo(() => {
    const s = { total: allItems.length, pending: 0, confirmed: 0, flagged: 0, rejected: 0 }
    allItems.forEach(item => {
      const st = (review[item.id] || {}).status || 'pending'
      s[st] = (s[st] || 0) + 1
    })
    return s
  }, [allItems, review])

  // Review summaries from log (multi-reviewer aggregation)
  const reviewSummaries = useMemo(() => getAllSummaries(reviewLog), [reviewLog])

  // Vote type counts (for FilterBar tabs) — pages + unique stations
  const { voteTypeCounts, voteTypeStations } = useMemo(() => {
    const counts = {}
    const stationSets = {}
    allItems.forEach(item => {
      if (filterProvince !== 'all' && item.province !== filterProvince) return
      const vt = item.vote_type || 'ไม่ระบุ'
      counts[vt] = (counts[vt] || 0) + 1
      // Track unique stations per vote_type
      const stn = item.ocr_station_no || item.station_no
      if (stn) {
        if (!stationSets[vt]) stationSets[vt] = new Set()
        stationSets[vt].add(`${item.constituency || '?'}_${stn}`)
      }
    })
    const stationCounts = {}
    for (const [vt, s] of Object.entries(stationSets)) stationCounts[vt] = s.size
    return { voteTypeCounts: counts, voteTypeStations: stationCounts }
  }, [allItems, filterProvince])

  // Log every sign-in / sign-out
  useEffect(() => {
    if (user && !prevUser) {
      submitLoginEvent(user)
    } else if (!user && prevUser) {
      submitLogoutEvent(prevUser)
    }
    setPrevUser(user)
  }, [user])

  // Auth gate
  if (!user) return <AuthGate renderButton={renderButton} />

  if (loading) return <div className="flex items-center justify-center h-screen"><div className="text-xl text-gray-500 animate-pulse">Loading...</div></div>
  if (error && allItems.length === 0) return (
    <div className="flex flex-col items-center justify-center h-screen gap-6 px-4">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-indigo-900 mb-2">🔍 OCR Review — สส.5/16</h1>
        <p className="text-gray-500">ระบบตรวจสอบผลการนับคะแนนเลือกตั้ง สส. 2569</p>
      </div>
      <div className="bg-white rounded-xl shadow-lg p-8 max-w-md w-full text-center">
        <FolderUp size={48} className="mx-auto text-indigo-400 mb-4" />
        <h2 className="text-lg font-semibold text-gray-800 mb-2">อัปโหลดข้อมูลเพื่อเริ่มตรวจสอบ</h2>
        <p className="text-sm text-gray-500 mb-4">เลือกไฟล์ JSON ที่สร้างจาก <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs">prepare_review_data.py</code></p>
        <label className="inline-flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg cursor-pointer hover:bg-indigo-700 transition font-medium">
          <Upload size={18} /> เลือกไฟล์ JSON
          <input type="file" accept=".json" className="hidden" onChange={(e) => {
            const file = e.target.files?.[0]
            if (!file) return
            const reader = new FileReader()
            reader.onload = (ev) => {
              try {
                const data = JSON.parse(ev.target.result)
                const items = Array.isArray(data) ? data : (data.items || data.data || [])
                if (items.length > 0) {
                  setAllItems(items)
                  setError(null)
                } else {
                  toast('ไม่พบข้อมูลในไฟล์', 'warning')
                }
              } catch { toast('ไฟล์ JSON ไม่ถูกต้อง', 'error') }
            }
            reader.readAsText(file)
          }} />
        </label>
      </div>
      {user && (
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <img src={user.picture} alt="" className="w-5 h-5 rounded-full object-cover" referrerPolicy="no-referrer" crossOrigin="anonymous"
            onError={e => { e.target.style.display = 'none' }} />
          <span>{user.name}</span>
          <button onClick={signOut} className="text-indigo-500 hover:underline ml-2">ออกจากระบบ</button>
        </div>
      )}
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-50 pb-10">
      {/* Header */}
      <header className="bg-gradient-to-r from-indigo-950 via-indigo-900 to-indigo-800 text-white sticky top-0 z-50 shadow-lg">
        <div className="max-w-[1440px] mx-auto px-4 py-2.5 flex items-center gap-4">
          {/* Logo + title */}
          <div className="flex items-center gap-3 mr-auto">
            <div className="w-9 h-9 bg-white/15 rounded-lg flex items-center justify-center text-lg">🔍</div>
            <div>
              <h1 className="text-base font-bold leading-tight">OCR Review — สส.5/16</h1>
              <p className="text-[11px] text-indigo-300">{stats.total.toLocaleString()} หน้า | {(stats.confirmed + stats.flagged + stats.rejected).toLocaleString()} ตรวจแล้ว</p>
            </div>
          </div>

          {/* Progress */}
          <StatsBar stats={stats} />

          {/* User info */}
          {user && (
            <div className="flex items-center gap-2 pl-3 border-l border-white/20">
              {user.picture ? (
                <img src={user.picture} alt={`${user.name} avatar`} className="w-7 h-7 shrink-0 aspect-square rounded-full ring-2 ring-white/30 object-cover" referrerPolicy="no-referrer" crossOrigin="anonymous"
                  onError={e => { e.target.style.display = 'none'; e.target.nextElementSibling && (e.target.nextElementSibling.style.display = 'flex') }} />
              ) : null}
              <div className="w-7 h-7 shrink-0 rounded-full ring-2 ring-white/30 bg-indigo-500 items-center justify-center text-[11px] font-bold text-white" style={{ display: user.picture ? 'none' : 'flex' }}>
                {(user.name || '?').charAt(0).toUpperCase()}
              </div>
              <div className="hidden sm:block">
                <span className="text-xs font-medium block leading-tight">{user.name}</span>
                <span className="text-[10px] text-emerald-300 flex items-center gap-0.5"><ShieldCheck size={10} /> ยืนยันแล้ว</span>
              </div>
            </div>
          )}

          {/* Action buttons — Desktop: all visible, Mobile: overflow menu */}
          <div className="flex items-center gap-1.5 pl-3 border-l border-white/20">
            <button onClick={toggleDark} className="flex items-center gap-1 p-1.5 bg-white/10 hover:bg-white/20 rounded-lg text-xs transition" title={dark ? 'Light mode' : 'Dark mode'} aria-label={dark ? 'เปลี่ยนเป็นโหมดสว่าง' : 'เปลี่ยนเป็นโหมดมืด'}>
              {dark ? <Sun size={14} /> : <Moon size={14} />}
            </button>

            {/* Desktop buttons (hidden on mobile) */}
            <div className="hidden md:flex items-center gap-1.5">
              <button onClick={() => setShowAdminPanel(v => !v)} className="flex items-center gap-1.5 px-2.5 py-1.5 bg-amber-500/80 hover:bg-amber-500 rounded-lg text-xs font-medium transition" title="Admin Panel" aria-label="เปิดแผงผู้ดูแลระบบ">
                🛡️ Admin
              </button>
              
              {/* Phase 34: Review Throughput Controls */}
              <button 
                onClick={() => setAutoApproveEnabled(v => !v)} 
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition ${
                  autoApproveEnabled ? 'bg-green-500/80 hover:bg-green-500 text-white' : 'bg-white/15 hover:bg-white/25 text-white'
                }`} 
                title="Auto-approve low-risk items (Shift+A to toggle)"
                aria-label="เปิด/ปิด auto-approve"
                disabled={bulkOperationInProgress}
              >
                🤖 Auto-approve {autoApproveEnabled ? 'ON' : 'OFF'}
              </button>
              
              <button 
                onClick={() => setPriorityQueueEnabled(v => !v)} 
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition ${
                  priorityQueueEnabled ? 'bg-orange-500/80 hover:bg-orange-500 text-white' : 'bg-white/15 hover:bg-white/25 text-white'
                }`} 
                title="Priority queue for high-anomaly items (Ctrl+P to toggle)"
                aria-label="เปิด/ปิด priority queue"
              >
                🔄 Priority {priorityQueueEnabled ? 'ON' : 'OFF'}
              </button>
              
              <button onClick={() => setShowUpload(true)} className="flex items-center gap-1.5 px-2.5 py-1.5 bg-emerald-500/80 hover:bg-emerald-500 rounded-lg text-xs font-medium transition" aria-label="อัปโหลดไฟล์">
                <FolderUp size={13} /> อัปโหลด
              </button>
              <div className="relative" ref={exportMenuRef}>
                <button onClick={() => setShowExportMenu(v => !v)} className="flex items-center gap-1.5 px-2.5 py-1.5 bg-white/15 hover:bg-white/25 rounded-lg text-xs font-medium transition" aria-expanded={showExportMenu} aria-haspopup="true" aria-label="เมนูส่งออกข้อมูล">
                  <Download size={13} /> Export <ChevronDown size={11} />
                </button>
                {showExportMenu && (
                  <div className="absolute right-0 top-full mt-1.5 bg-white rounded-xl shadow-2xl border border-gray-200 z-50 min-w-[300px] overflow-hidden">
                    <div className="px-4 py-2.5 bg-indigo-50 border-b border-indigo-100">
                      <p className="text-xs font-bold text-indigo-800">📤 Export — ส่งออกข้อมูล</p>
                      <p className="text-[10px] text-indigo-600 mt-0.5">ดาวน์โหลดข้อมูล OCR + ผลการตรวจสอบ เพื่อนำไปวิเคราะห์ต่อ หรือสำรองข้อมูล</p>
                    </div>
                    <div className="px-4 py-1.5 text-[10px] text-gray-400 uppercase bg-gray-50 font-semibold">ข้อมูลทั้งหมด ({allItems.length} รายการ)</div>
                    <button onClick={() => { setShowExportMenu(false); handleExportJSON() }} className="w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-indigo-50 hover:text-indigo-700 transition border-b border-gray-100">
                      <div className="font-medium">📄 JSON (ข้อมูล + review)</div>
                      <div className="text-[10px] text-gray-400 mt-0.5">ข้อมูล OCR ทุกหน้า + สถานะ/ค่าแก้ไข/consensus — ใช้ Import กลับเข้าระบบได้</div>
                    </button>
                    <button onClick={() => { setShowExportMenu(false); handleExportCSV() }} className="w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-indigo-50 hover:text-indigo-700 transition border-b border-gray-100">
                      <div className="font-medium">📊 CSV สรุปทั้งหมด</div>
                      <div className="text-[10px] text-gray-400 mt-0.5">ตารางสรุปสถิติ 1 แถว = 1 หน้า — เปิดใน Excel/Google Sheets ได้ทันที</div>
                    </button>
                    <button onClick={() => { setShowExportMenu(false); handleExportFullCSV() }} className="w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-indigo-50 hover:text-indigo-700 transition border-b border-gray-100">
                      <div className="font-medium">📋 CSV แบ่งเขต + ผู้สมัคร</div>
                      <div className="text-[10px] text-gray-400 mt-0.5">CSV เฉพาะแบ่งเขต มีคอลัมน์ผู้สมัครแต่ละคน — สำหรับวิเคราะห์เชิงลึก</div>
                    </button>
                    <button onClick={() => { setShowExportMenu(false); handleExportAuditLog() }} className="w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-amber-50 hover:text-amber-700 transition border-b border-gray-100">
                      <div className="font-medium">🔒 Audit Log (ประวัติการตรวจ)</div>
                      <div className="text-[10px] text-gray-400 mt-0.5">ประวัติการตรวจทุกครั้ง ทุกคน + ค่า anomaly — สำหรับ Admin ตรวจสอบย้อนหลัง</div>
                    </button>
                    <div className="px-4 py-1.5 text-[10px] text-gray-400 uppercase bg-gray-50 font-semibold">เฉพาะที่กรอง ({filteredItems.length} รายการ)</div>
                    <button onClick={() => { setShowExportMenu(false); handleExportFilteredJSON() }} className="w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-purple-50 hover:text-purple-700 transition border-b border-gray-100">
                      <div className="font-medium"><Filter size={12} className="inline mr-1" /> JSON (เฉพาะที่กรอง)</div>
                      <div className="text-[10px] text-gray-400 mt-0.5">เหมือน JSON ด้านบน แต่เฉพาะรายการที่ตรงกับ filter ที่เลือกอยู่</div>
                    </button>
                    <button onClick={() => { setShowExportMenu(false); handleExportFilteredCSV() }} className="w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-purple-50 hover:text-purple-700 transition">
                      <div className="font-medium"><Filter size={12} className="inline mr-1" /> CSV (เฉพาะที่กรอง)</div>
                      <div className="text-[10px] text-gray-400 mt-0.5">เหมือน CSV ด้านบน แต่เฉพาะรายการที่ตรงกับ filter ที่เลือกอยู่</div>
                    </button>
                    
                    {/* Phase 34: Bulk Operations */}
                    <div className="px-4 py-1.5 text-[10px] text-gray-400 uppercase bg-amber-50 font-semibold border-t border-gray-200">⚡ Bulk Operations</div>
                    <button 
                      onClick={bulkAutoApprove} 
                      disabled={!autoApproveEnabled || bulkOperationInProgress} 
                      className="w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-green-50 hover:text-green-700 transition border-b border-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <div className="font-medium">🤖 Auto-approve Low-risk ({sortedFilteredItems.filter(item => (review[item.id]?.status || 'pending') === 'pending' && isLowRiskItem(item)).length} รายการ)</div>
                      <div className="text-[10px] text-gray-400 mt-0.5">ยืนยันอัตโนมัติสำหรับรายการที่ไม่มี error/warning — ใช้ Ctrl+A</div>
                    </button>
                    <button 
                      onClick={bulkConfirmAll} 
                      disabled={bulkOperationInProgress} 
                      className="w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <div className="font-medium">✅ Bulk Confirm All ({sortedFilteredItems.filter(item => (review[item.id]?.status || 'pending') === 'pending').length} รายการ)</div>
                      <div className="text-[10px] text-gray-400 mt-0.5">ยืนยันทั้งหมดในหน้าจอนี้ — ใช้ Ctrl+B</div>
                    </button>
                  </div>
                )}
              </div>
              <button onClick={() => setShowImportInfo(true)} className="flex items-center gap-1.5 px-2.5 py-1.5 bg-white/10 hover:bg-white/20 rounded-lg text-xs font-medium transition">
                <Upload size={13} /> Import
              </button>
              {user && (
                <button onClick={signOut} className="flex items-center gap-1 p-1.5 bg-white/10 hover:bg-white/20 rounded-lg text-xs transition" title="ออกจากระบบ">
                  <LogOut size={13} />
                </button>
              )}
            </div>

            {/* Mobile hamburger menu (visible only on mobile) */}
            <div className="relative md:hidden" ref={mobileMenuRef}>
              <button onClick={() => setShowMobileMenu(v => !v)} className="flex items-center gap-1 p-1.5 bg-white/10 hover:bg-white/20 rounded-lg text-xs transition" aria-label="เมนูเพิ่มเติม" aria-expanded={showMobileMenu}>
                {showMobileMenu ? <X size={16} /> : <Menu size={16} />}
              </button>
              {showMobileMenu && (
                <div className="absolute right-0 top-full mt-1.5 bg-white rounded-xl shadow-2xl border border-gray-200 z-50 min-w-[220px] overflow-hidden text-gray-800">
                  <div className="px-3 py-2 bg-indigo-50 border-b border-indigo-100 text-xs font-bold text-indigo-800">⚙️ เมนู</div>
                  <button onClick={() => { setShowAdminPanel(v => !v); setShowMobileMenu(false) }} className="w-full text-left px-3 py-2.5 text-sm hover:bg-gray-50 transition border-b border-gray-100 flex items-center gap-2">
                    🛡️ Admin Panel
                  </button>
                  <button onClick={() => { setAutoApproveEnabled(v => !v); setShowMobileMenu(false) }} className="w-full text-left px-3 py-2.5 text-sm hover:bg-gray-50 transition border-b border-gray-100 flex items-center gap-2">
                    🤖 Auto-approve {autoApproveEnabled ? <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-100 text-green-700 font-bold">ON</span> : <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 font-bold">OFF</span>}
                  </button>
                  <button onClick={() => { setPriorityQueueEnabled(v => !v); setShowMobileMenu(false) }} className="w-full text-left px-3 py-2.5 text-sm hover:bg-gray-50 transition border-b border-gray-100 flex items-center gap-2">
                    🔄 Priority Queue {priorityQueueEnabled ? <span className="text-[10px] px-1.5 py-0.5 rounded bg-orange-100 text-orange-700 font-bold">ON</span> : <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 font-bold">OFF</span>}
                  </button>
                  <button onClick={() => { setShowUpload(true); setShowMobileMenu(false) }} className="w-full text-left px-3 py-2.5 text-sm hover:bg-gray-50 transition border-b border-gray-100 flex items-center gap-2">
                    <FolderUp size={14} /> อัปโหลด
                  </button>
                  <button onClick={() => { setShowExportMenu(v => !v); setShowMobileMenu(false) }} className="w-full text-left px-3 py-2.5 text-sm hover:bg-gray-50 transition border-b border-gray-100 flex items-center gap-2">
                    <Download size={14} /> Export
                  </button>
                  <button onClick={() => { setShowImportInfo(true); setShowMobileMenu(false) }} className="w-full text-left px-3 py-2.5 text-sm hover:bg-gray-50 transition border-b border-gray-100 flex items-center gap-2">
                    <Upload size={14} /> Import
                  </button>
                  {user && (
                    <button onClick={() => { signOut(); setShowMobileMenu(false) }} className="w-full text-left px-3 py-2.5 text-sm hover:bg-red-50 text-red-600 transition flex items-center gap-2">
                      <LogOut size={14} /> ออกจากระบบ
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Dashboard Tab Bar */}
      {(() => {
        const tabs = [
          { key: 'stats',       label: '📊 สถิติ' },
          { key: 'anomaly',     label: '🚨 ผิดปกติ', filterShortcut: 'anomaly_summary' },
          { key: 'backup',      label: '💾 Backup' },
          { key: 'analytics',   label: '📈 Analytics' },
          { key: 'heatmap',     label: '🗺️ แผนที่' },
          { key: 'leaderboard', label: '🏆 ผู้ตรวจ' },
          { key: 'crossref',    label: '🔗 Cross-Ref' },
        ]
        return (
          <div className="max-w-[1440px] mx-auto px-4 py-1.5">
            <div className="flex items-center gap-1 bg-white border border-gray-200 rounded-xl px-3 py-1.5 shadow-sm overflow-x-auto">
              {tabs.map(t => {
                const isActive = t.filterShortcut
                  ? filterStatus === t.filterShortcut
                  : activeDashboard === t.key
                return (
                  <button
                    key={t.key}
                    onClick={() => {
                      if (t.filterShortcut) {
                        setFilterStatus(prev => prev === t.filterShortcut ? 'all' : t.filterShortcut)
                        setActiveDashboard(null)
                      } else {
                        setActiveDashboard(prev => prev === t.key ? null : t.key)
                        if (filterStatus === 'anomaly_summary') setFilterStatus('all')
                      }
                    }}
                    className={`whitespace-nowrap px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? t.filterShortcut
                          ? 'bg-red-600 text-white shadow-sm'
                          : 'bg-indigo-600 text-white shadow-sm'
                        : 'text-gray-600 hover:bg-gray-100'
                    }`}
                  >
                    {t.label}
                  </button>
                )
              })}
            </div>

            {activeDashboard && (
              <Suspense fallback={<div className="mt-2 bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400 animate-pulse">กำลังโหลด…</div>}>
                <div className="mt-2 bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                  {activeDashboard === 'stats'       && <DataStatsPanel allItems={allItems} review={review} anomalyFlags={anomalyFlags} anomalyMeta={anomalyMeta} />}
                  {activeDashboard === 'backup'      && <BackupDashboard />}
                  {activeDashboard === 'analytics'   && <AnalyticsDashboard allItems={allItems} review={review} reviewLog={reviewLog} anomalyFlags={anomalyFlags} />}
                  {activeDashboard === 'heatmap'     && <ProvinceHeatmap allItems={allItems} review={review} />}
                  {activeDashboard === 'leaderboard' && <ReviewerLeaderboard reviewLog={reviewLog} allItems={allItems} review={review} />}
                  {activeDashboard === 'crossref'    && <CrossReferencePanel allItems={allItems} review={review} anomalyFlags={anomalyFlags} anomalyMeta={anomalyMeta} />}
                </div>
              </Suspense>
            )}
          </div>
        )
      })()}

      {/* Filter bar */}
      <FilterBar
        filterStatus={filterStatus}
        setFilterStatus={setFilterStatus}
        filterProvince={filterProvince}
        setFilterProvince={setFilterProvince}
        provinces={provinces}
        filterConstituency={filterConstituency}
        setFilterConstituency={setFilterConstituency}
        constituencies={constituencies}
        filterVoteType={filterVoteType}
        setFilterVoteType={setFilterVoteType}
        voteTypeCounts={voteTypeCounts}
        voteTypeStations={voteTypeStations}
        searchText={searchText}
        setSearchText={setSearchText}
      />

      {/* Navigation */}
      {filterStatus !== 'anomaly_summary' && (
        <div className="max-w-[1440px] mx-auto px-4 py-3">
          <div className="flex items-center justify-between bg-white rounded-xl shadow-sm border border-gray-200 px-4 py-2.5">
            <button onClick={goPrev} disabled={currentIndex === 0}
              aria-label="หน้าก่อนหน้า"
              className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-50 border border-gray-200 rounded-lg text-sm font-medium hover:bg-gray-100 disabled:opacity-30 transition">
              <ChevronLeft size={16} /> ก่อนหน้า
            </button>
            <span className="text-sm text-gray-600 font-medium flex items-center gap-2" aria-live="polite" aria-atomic="true">
              {sortedFilteredItems.length > 0 ? `${currentIndex + 1} / ${sortedFilteredItems.length}` : 'ไม่พบข้อมูล'}
              {filterStatus === 'anomaly' && currentItem && anomalyScoreMap[currentItem.id] && (
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                  anomalyScoreMap[currentItem.id].score >= 50 ? 'bg-red-600 text-white' :
                  anomalyScoreMap[currentItem.id].score >= 30 ? 'bg-orange-500 text-white' :
                  anomalyScoreMap[currentItem.id].score >= 15 ? 'bg-yellow-500 text-white' :
                  'bg-blue-500 text-white'
                }`}>
                  🚨 {anomalyScoreMap[currentItem.id].score}
                </span>
              )}
            </span>
            <button onClick={goNext} disabled={currentIndex >= sortedFilteredItems.length - 1}
              aria-label="หน้าถัดไป"
              className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-50 border border-gray-200 rounded-lg text-sm font-medium hover:bg-gray-100 disabled:opacity-30 transition">
              ถัดไป <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Main content */}
      <main className="max-w-[1440px] mx-auto px-4">
        {filterStatus === 'anomaly_summary' ? (
          <Suspense fallback={<div className="text-center py-20 text-gray-400 animate-pulse">กำลังโหลดภาพรวมผิดปกติ…</div>}>
            <AnomalySummaryPanel 
              allItems={allItems}
              anomalyScoreMap={anomalyScoreMap}
              anomalyFlags={anomalyFlags}
              filterProvince={filterProvince}
              filterConstituency={filterConstituency}
            />
          </Suspense>
        ) : currentItem ? (
          <ReviewCard
            item={currentItem}
            review={getReview(currentItem.id)}
            reviewSummary={reviewSummaries[currentItem.id] || null}
            isFirstPage={isFirstPage}
            sharedEdits={sharedEdits[currentConstKey] || {}}
            anomalyFlags={anomalyFlags[`${currentItem.province}_${currentItem.constituency}`] || null}
            anomalyScore={anomalyScoreMap[currentItem.id] || null}
            onSetStatus={(status) => setItemStatus(currentItem.id, status)}
            onSetNote={(note) => setItemNote(currentItem.id, note)}
            onEdit={(field, value, orig) => setItemEdit(currentItem.id, field, value, orig)}
            onSharedEdit={(field, value, orig) => setSharedEdit(currentConstKey, field, value, orig)}
          />
        ) : (
          <div className="text-center py-20 text-gray-400">ไม่พบข้อมูลตามตัวกรอง</div>
        )}
      </main>

      {/* Footer */}
      {filterStatus !== 'anomaly_summary' && (
        <footer className="fixed bottom-0 left-0 right-0 bg-white/95 backdrop-blur-sm border-t border-gray-200 py-1.5 text-center text-[11px] text-gray-500 z-40">
          <span className="inline-flex items-center gap-3 flex-wrap justify-center">
            <span>←→ / <kbd className="px-1 py-0.5 bg-gray-100 rounded text-[10px] font-mono">j</kbd> <kbd className="px-1 py-0.5 bg-gray-100 rounded text-[10px] font-mono">k</kbd> เลื่อน</span>
            <span><kbd className="px-1 py-0.5 bg-gray-100 rounded text-[10px] font-mono">1</kbd> ยืนยัน</span>
            <span><kbd className="px-1 py-0.5 bg-gray-100 rounded text-[10px] font-mono">2</kbd> ตรวจอีกรอบ</span>
            <span><kbd className="px-1 py-0.5 bg-gray-100 rounded text-[10px] font-mono">3</kbd> ใช้ไม่ได้</span>
            <span><kbd className="px-1 py-0.5 bg-gray-100 rounded text-[10px] font-mono">r</kbd> รีเซ็ต</span>
            <span><kbd className="px-1 py-0.5 bg-gray-100 rounded text-[10px] font-mono">Esc</kbd> ออกจากช่อง</span>
          </span>
        </footer>
      )}

      {/* Rate limit warning toast (F2) */}
      {rateLimitWarning && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 z-[100] bg-amber-500 text-white px-6 py-3 rounded-lg shadow-xl text-sm font-medium animate-pulse">
          ⚡ {rateLimitWarning}
        </div>
      )}

      {/* Admin Panel (F6) */}
      {showAdminPanel && (
        <Suspense fallback={<div className="fixed inset-0 bg-black/40 z-[100] flex items-center justify-center"><div className="bg-white rounded-xl p-8 text-gray-400 animate-pulse">กำลังโหลด Admin Panel…</div></div>}>
          <AdminPanel
            reviewLog={reviewLog}
            allItems={allItems}
            review={review}
            onClose={() => setShowAdminPanel(false)}
            onImportLog={(extLog) => {
              const result = mergeReviewLogs(extLog)
              setReviewLog(result.merged)
              toast(`นำเข้าสำเร็จ: เพิ่ม ${result.added} รายการใหม่`, 'success')
            }}
          />
        </Suspense>
      )}

      {/* Import info modal */}
      {showImportInfo && (
        <div className="fixed inset-0 bg-black/40 z-[100] flex items-center justify-center" onClick={() => setShowImportInfo(false)}>
          <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full mx-4 overflow-hidden" onClick={e => e.stopPropagation()}>
            <div className="px-5 py-3 border-b bg-teal-50 border-teal-200">
              <h3 className="text-base font-bold text-teal-800">📥 Import — นำเข้าผล Review</h3>
            </div>
            <div className="px-5 py-4 text-sm text-gray-700 space-y-3">
              <div>
                <p className="font-semibold text-teal-800 mb-1">📌 หน้าที่:</p>
                <p className="text-gray-600">นำเข้าไฟล์ JSON ที่ส่งออก (Export) ไว้ก่อนหน้า เพื่อกู้คืนสถานะการตรวจสอบ (ยืนยัน/ตรวจอีกรอบ/ใช้ไม่ได้) กลับเข้าสู่ระบบ</p>
              </div>
              <div>
                <p className="font-semibold text-teal-800 mb-1">📋 ขั้นตอน:</p>
                <ol className="list-decimal ml-5 space-y-1 text-gray-600">
                  <li><strong>กด "เลือกไฟล์ JSON"</strong> ด้านล่าง</li>
                  <li><strong>เลือกไฟล์</strong> ที่ Export ไว้ (รูปแบบ <code className="bg-gray-100 px-1 rounded text-xs">ocr_reviewed_*.json</code>)</li>
                  <li><strong>ระบบจะโหลด</strong> สถานะ review ทั้งหมดจากไฟล์ทับลงในระบบปัจจุบัน</li>
                </ol>
              </div>
              <div>
                <p className="font-semibold text-teal-800 mb-1">⚠️ ข้อควรระวัง:</p>
                <ul className="list-disc ml-5 space-y-0.5 text-gray-600">
                  <li>ไฟล์ต้องเป็น <strong>JSON</strong> เท่านั้น (.json)</li>
                  <li>สถานะ review ปัจจุบันจะถูก <strong>แทนที่</strong> ด้วยข้อมูลจากไฟล์</li>
                  <li>ใช้สำหรับ <strong>กู้คืนข้อมูล</strong> หรือ <strong>ย้ายผลงาน</strong> ระหว่างเครื่อง</li>
                  <li>แนะนำ <strong>Export ไว้ก่อน</strong> เพื่อสำรองข้อมูลเดิม</li>
                </ul>
              </div>
            </div>
            <div className="px-5 py-3 bg-gray-50 border-t flex gap-2 justify-end">
              <button onClick={() => setShowImportInfo(false)} className="px-4 py-1.5 text-sm rounded border border-gray-300 text-gray-600 hover:bg-gray-100 transition">
                ยกเลิก
              </button>
              <label className="px-4 py-1.5 text-sm font-medium rounded bg-teal-600 text-white hover:bg-teal-700 transition cursor-pointer inline-flex items-center gap-1.5">
                <Upload size={14} /> เลือกไฟล์ JSON
                <input type="file" accept=".json" className="hidden" onChange={(e) => { handleImport(e); setShowImportInfo(false) }} />
              </label>
            </div>
          </div>
        </div>
      )}

      {/* Upload panel */}
      {showUpload && (
        <Suspense fallback={<div className="fixed inset-0 bg-black/40 z-[100] flex items-center justify-center"><div className="bg-white rounded-xl p-8 text-gray-400 animate-pulse">กำลังโหลด…</div></div>}>
          <UploadPanel
            onClose={() => setShowUpload(false)}
            onDataRefresh={loadData}
          />
        </Suspense>
      )}
      {/* Floating feedback button + popup */}
      <button
        type="button"
        onClick={() => setFbOpen(v => !v)}
        className="fixed bottom-5 left-5 z-50 flex flex-col items-center justify-center bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-2xl shadow-lg hover:shadow-xl transition-all cursor-pointer"
        title="ส่งคำถามหรือข้อเสนอแนะ"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        <span className="text-[11px] font-medium leading-tight text-center mt-0.5">คำถาม<br/>ข้อเสนอแนะ</span>
      </button>
      {fbOpen && (
        <div className="fixed bottom-20 left-5 z-50 w-80 bg-white rounded-xl shadow-2xl border border-gray-200 overflow-hidden">
          <div className="bg-indigo-600 text-white px-4 py-2.5 flex items-center justify-between">
            <span className="text-sm font-medium">📩 ส่งคำถาม / ข้อเสนอแนะ</span>
            <button onClick={() => setFbOpen(false)} className="text-white/70 hover:text-white text-lg leading-none">&times;</button>
          </div>
          <div className="p-3 space-y-2">
            <div className="text-xs text-gray-500">ถึง: narasakp@gmail.com</div>
            <textarea
              value={fbMsg}
              onChange={e => setFbMsg(e.target.value)}
              placeholder="พิมพ์ข้อความที่นี่..."
              className="w-full h-24 text-sm border border-gray-200 rounded-lg p-2 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-400"
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <button onClick={() => setFbOpen(false)} className="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-700">ยกเลิก</button>
              <button onClick={() => {
                const subj = encodeURIComponent('คำถาม / ข้อเสนอแนะ – Election Verification')
                const body = encodeURIComponent(fbMsg || '')
                window.open(`https://mail.google.com/mail/?view=cm&fs=1&to=narasakp@gmail.com&su=${subj}&body=${body}&tf=cm`, 'feedback_email', 'width=680,height=600,left=200,top=100')
                setFbOpen(false); setFbMsg('')
              }} className="px-4 py-1.5 text-xs bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium">ส่งผ่าน Gmail</button>
            </div>
          </div>
        </div>
      )}
      <ToastContainer />
    </div>
  )
}

export default App
