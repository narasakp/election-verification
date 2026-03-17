import React, { useState, useEffect, useCallback, useMemo } from 'react'
import ReviewCard from './components/ReviewCard'
import FilterBar from './components/FilterBar'
import StatsBar from './components/StatsBar'
import DataStatsPanel from './components/DataStatsPanel'
import UploadPanel from './components/UploadPanel'
import AdminPanel from './components/AdminPanel'
import AuthGate from './components/AuthGate'
import useAuth from './hooks/useAuth'
import { submitToGoogleForm, submitLoginEvent, submitLogoutEvent } from './utils/submitReview'
import { getReviewLog, appendReviewLog, getAllSummaries, getUserReviewKey, checkRateLimit, recordReviewTiming, validateEditValue, getAllAnomalyScores, mergeReviewLogs, verifyLogIntegrity } from './utils/reviewLog'
import { validateItem, getWorstSeverity } from './utils/validation'
import { ChevronLeft, ChevronRight, Download, Upload, FolderUp, LogOut, ShieldCheck, ChevronDown } from 'lucide-react'

const DATA_URL = './data/review_data.json'
const ANOMALY_FLAGS_URL = './data/anomaly_flags.json'

function App() {
  const { user, loading: authLoading, signOut, renderButton } = useAuth()
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
  const [rateLimitWarning, setRateLimitWarning] = useState(null)
  const [showAdminPanel, setShowAdminPanel] = useState(false)
  const [anomalyFlags, setAnomalyFlags] = useState({})
  const exportMenuRef = React.useRef(null)

  // Close export menu on outside click
  useEffect(() => {
    if (!showExportMenu) return
    const handler = (e) => {
      if (exportMenuRef.current && !exportMenuRef.current.contains(e.target)) setShowExportMenu(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [showExportMenu])

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
      .then(d => { if (d?.flags_by_prov_con) setAnomalyFlags(d.flags_by_prov_con) })
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
  }, [allItems, review, filterStatus, filterProvince, filterConstituency, filterVoteType, searchText])

  // Reset index when filter changes
  useEffect(() => { setCurrentIndex(0) }, [filterStatus, filterProvince, filterConstituency, filterVoteType, searchText])

  const currentItem = filteredItems[currentIndex] || null

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
    setCurrentIndex(i => Math.min(i + 1, filteredItems.length - 1))
  }, [filteredItems.length])

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
      setTimeout(() => setCurrentIndex(i => Math.min(i + 1, filteredItems.length - 1)), 150)
    }
  }, [allItems, review, user, filteredItems.length])

  // Keyboard navigation
  useEffect(() => {
    const handler = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return
      if (e.key === 'ArrowRight' || e.key === 'j') goNext()
      if (e.key === 'ArrowLeft' || e.key === 'k') goPrev()
      // Review shortcuts: 1=confirm, 2=flag, 3=reject, r=reset
      if (currentItem) {
        if (e.key === '1') setItemStatus(currentItem.id, 'confirmed')
        if (e.key === '2') {
          if (window.confirm('🔄 ตรวจอีกรอบ\n\nหน้านี้จะถูกส่งให้อาสาคนอื่นตรวจซ้ำ\nยืนยันหรือไม่?')) {
            setItemStatus(currentItem.id, 'flagged')
          }
        }
        if (e.key === '3') {
          if (window.confirm('🚫 ใช้ไม่ได้\n\nหน้านี้จะถูกตัดออกจากชุดข้อมูลสุดท้าย\n(ถ้าข้อมูลแค่ผิด → แก้ตัวเลขแล้วกด 1 ยืนยัน แทน)\n\nยืนยันหรือไม่?')) {
            setItemStatus(currentItem.id, 'rejected')
          }
        }
        if (e.key === 'r') setItemStatus(currentItem.id, 'pending')
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [goNext, goPrev, currentItem, setItemStatus])

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

  const handleExportJSON = () => {
    setShowExportMenu(false)
    const summaries = getAllSummaries(reviewLog)
    const merged = allItems.map(item => {
      const rev = review[item.id]
      const constKey = `${item.province || ''}__${item.constituency || ''}`
      const shared = sharedEdits[constKey] || {}
      const summary = summaries[item.id]
      const base = !rev
        ? { ...item, ...shared, _review_status: 'pending' }
        : { ...item, ...shared, ...(rev.edits || {}), _review_status: rev.status, _review_note: rev.note }
      // F5: Attach audit trail
      if (summary) {
        base._consensus_status = summary.majorityStatus || (summary.isTie ? 'disputed' : null)
        base._consensus_ratio = summary.consensusRatio
        base._is_tie = summary.isTie
        if (summary.isTie) base._tied_statuses = summary.tiedStatuses
        base._reviewer_count = summary.reviewerCount
        base._total_reviews = summary.totalReviews
        base._has_conflict = summary.hasConflict
        if (Object.keys(summary.consensusEdits).length > 0) base._consensus_edits = summary.consensusEdits
        if (Object.keys(summary.editConflicts).length > 0) base._edit_conflicts = summary.editConflicts
        if (summary.outliers.length > 0) base._outliers = summary.outliers
      }
      return base
    })
    const blob = new Blob([JSON.stringify(merged, null, 2)], { type: 'application/json' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `ocr_reviewed_${new Date().toISOString().slice(0, 10)}.json`
    a.click()
  }

  // F5: Export full audit log
  const handleExportAuditLog = () => {
    setShowExportMenu(false)
    const log = getReviewLog()
    const anomalyScores = getAllAnomalyScores(log)
    const corrupted = verifyLogIntegrity(log)
    const exportData = {
      exportedAt: new Date().toISOString(),
      exportedBy: user?.email || 'anonymous',
      logEntries: log.length,
      corruptedEntries: corrupted,
      anomalyScores,
      log,
    }
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `audit_log_${new Date().toISOString().slice(0, 10)}.json`
    a.click()
  }

  const csvEsc = (v) => {
    const s = String(v == null ? '' : v)
    return s.includes(',') || s.includes('"') || s.includes('\n') ? '"' + s.replace(/"/g, '""') + '"' : s
  }

  const handleExportCSV = () => {
    setShowExportMenu(false)
    const headers = ['file','page','province','constituency','station_no','sub_district','district','vote_type',
      'registered_voters','turnout','ballots_received','valid_ballots','invalid_ballots','no_vote_ballots','remaining_ballots','total_votes',
      'candidates_count','candidate_votes_sum','review_status','review_note']
    const rows = [headers.join(',')]
    allItems.forEach(d => {
      const rev = review[d.id] || {}
      const constKey = `${d.province || ''}__${d.constituency || ''}`
      const shared = sharedEdits[constKey] || {}
      const edits = rev.edits || {}
      // Merge: item ← shared ← per-page edits (edits win over shared)
      const merged = { ...d, ...shared, ...edits }
      const cands = d.candidates || []
      const candSum = cands.reduce((s, c) => s + (Number(c.votes) || 0), 0)
      rows.push([
        csvEsc(merged.file), merged.page, csvEsc(merged.province), merged.constituency, merged.ocr_station_no,
        csvEsc(merged.sub_district), csvEsc(merged.district), csvEsc(merged.vote_type),
        merged.registered_voters, merged.turnout, merged.ballots_received, merged.valid_ballots,
        merged.invalid_ballots, merged.no_vote_ballots, merged.remaining_ballots, merged.total_votes,
        cands.length, candSum, rev.status || 'pending', csvEsc(rev.note || '')
      ].join(','))
    })
    const bom = '\uFEFF'
    const blob = new Blob([bom + rows.join('\n')], { type: 'text/csv;charset=utf-8' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `election_data_${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
  }

  const handleExportFullCSV = () => {
    setShowExportMenu(false)
    const constItems = allItems.filter(d => d.vote_type === 'แบ่งเขต')
    let maxCands = 0
    constItems.forEach(d => { const c = (d.candidates || []).length; if (c > maxCands) maxCands = c })
    const headers = ['file','page','province','constituency','station_no','sub_district','district','vote_type',
      'registered_voters','turnout','ballots_received','valid_ballots','invalid_ballots','no_vote_ballots','remaining_ballots','total_votes']
    for (let i = 1; i <= maxCands; i++) { headers.push(`cand${i}_no`, `cand${i}_name`, `cand${i}_party`, `cand${i}_votes`) }
    const rows = [headers.join(',')]
    constItems.forEach(d => {
      const row = [
        csvEsc(d.file), d.page, csvEsc(d.province), d.constituency, d.ocr_station_no,
        csvEsc(d.sub_district), csvEsc(d.district), csvEsc(d.vote_type),
        d.registered_voters, d.turnout, d.ballots_received, d.valid_ballots,
        d.invalid_ballots, d.no_vote_ballots, d.remaining_ballots, d.total_votes
      ]
      const cands = d.candidates || []
      for (let i = 0; i < maxCands; i++) {
        const c = cands[i]
        row.push(c ? c.number : '', c ? csvEsc(c.name) : '', c ? csvEsc(c.party) : '', c ? c.votes : '')
      }
      rows.push(row.join(','))
    })
    const bom = '\uFEFF'
    const blob = new Blob([bom + rows.join('\n')], { type: 'text/csv;charset=utf-8' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `election_constituency_${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
  }

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
                  alert('ไม่พบข้อมูลในไฟล์')
                }
              } catch { alert('ไฟล์ JSON ไม่ถูกต้อง') }
            }
            reader.readAsText(file)
          }} />
        </label>
      </div>
      {user && (
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <img src={user.picture} alt="" className="w-5 h-5 rounded-full" />
          <span>{user.name}</span>
          <button onClick={signOut} className="text-indigo-500 hover:underline ml-2">ออกจากระบบ</button>
        </div>
      )}
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-50 pb-10">
      {/* Header */}
      <header className="bg-gradient-to-r from-indigo-900 to-indigo-800 text-white sticky top-0 z-50 shadow-lg">
        <div className="max-w-[1400px] mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold flex items-center gap-2">🔍 OCR Review — สส.5/16</h1>
            <p className="text-xs opacity-75">{stats.total} หน้า | {stats.confirmed + stats.flagged + stats.rejected} ตรวจแล้ว</p>
          </div>
          <StatsBar stats={stats} />
          <div className="flex items-center gap-2">
            {user && (
              <div className="flex items-center gap-2 mr-2">
                {user.picture && <img src={user.picture} alt="" className="w-7 h-7 rounded-full border-2 border-white/50" />}
                <span className="text-xs opacity-90 hidden sm:inline">{user.name}</span>
                <span className="flex items-center gap-1 bg-emerald-400/20 text-emerald-200 px-2 py-0.5 rounded-full text-xs font-medium">
                  <ShieldCheck size={12} /> ยืนยันแล้ว
                </span>
                <button onClick={signOut} className="flex items-center gap-1 px-2 py-1 bg-white/10 rounded text-xs hover:bg-white/20 transition" title="ออกจากระบบ">
                  <LogOut size={12} />
                </button>
              </div>
            )}
            <button onClick={() => setShowAdminPanel(v => !v)} className="flex items-center gap-1 px-3 py-1.5 bg-amber-500/90 rounded text-sm hover:bg-amber-500 transition font-medium" title="Admin Panel">
              🛡️ Admin
            </button>
            <button onClick={() => setShowUpload(true)} className="flex items-center gap-1 px-3 py-1.5 bg-emerald-500/90 rounded text-sm hover:bg-emerald-500 transition font-medium">
              <FolderUp size={14} /> อัปโหลด
            </button>
            <div className="relative" ref={exportMenuRef}>
              <button onClick={() => setShowExportMenu(v => !v)} className="flex items-center gap-1 px-3 py-1.5 bg-white/20 rounded text-sm hover:bg-white/30 transition">
                <Download size={14} /> Export <ChevronDown size={12} />
              </button>
              {showExportMenu && (
                <div className="absolute right-0 top-full mt-1 bg-white rounded-lg shadow-xl border z-50 min-w-[220px] overflow-hidden">
                  <button onClick={handleExportJSON} className="w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-indigo-50 hover:text-indigo-700 transition border-b border-gray-100">
                    📄 JSON (ข้อมูล + review)
                  </button>
                  <button onClick={handleExportCSV} className="w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-indigo-50 hover:text-indigo-700 transition border-b border-gray-100">
                    📊 CSV สรุปทั้งหมด
                  </button>
                  <button onClick={handleExportFullCSV} className="w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-indigo-50 hover:text-indigo-700 transition border-b border-gray-100">
                    📋 CSV แบ่งเขต + ผู้สมัคร
                  </button>
                  <button onClick={handleExportAuditLog} className="w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-amber-50 hover:text-amber-700 transition">
                    🔒 Audit Log (ประวัติการตรวจ)
                  </button>
                </div>
              )}
            </div>
            <label className="flex items-center gap-1 px-3 py-1.5 bg-white/10 rounded text-sm hover:bg-white/20 transition cursor-pointer">
              <Upload size={14} /> Import
              <input type="file" accept=".json" className="hidden" onChange={handleImport} />
            </label>
          </div>
        </div>
      </header>

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

      {/* Data Stats */}
      <DataStatsPanel allItems={allItems} review={review} anomalyFlags={anomalyFlags} />

      {/* Navigation */}
      <div className="max-w-[1400px] mx-auto px-4 py-2 flex items-center justify-between">
        <button onClick={goPrev} disabled={currentIndex === 0}
          className="flex items-center gap-1 px-3 py-1.5 bg-white border rounded text-sm hover:bg-gray-50 disabled:opacity-30">
          <ChevronLeft size={16} /> ก่อนหน้า
        </button>
        <span className="text-sm text-gray-500">
          {filteredItems.length > 0 ? `${currentIndex + 1} / ${filteredItems.length}` : 'ไม่พบข้อมูล'}
        </span>
        <button onClick={goNext} disabled={currentIndex >= filteredItems.length - 1}
          className="flex items-center gap-1 px-3 py-1.5 bg-white border rounded text-sm hover:bg-gray-50 disabled:opacity-30">
          ถัดไป <ChevronRight size={16} />
        </button>
      </div>

      {/* Main content */}
      <main className="max-w-[1400px] mx-auto px-4">
        {currentItem ? (
          <ReviewCard
            item={currentItem}
            review={getReview(currentItem.id)}
            reviewSummary={reviewSummaries[currentItem.id] || null}
            isFirstPage={isFirstPage}
            sharedEdits={sharedEdits[currentConstKey] || {}}
            anomalyFlags={anomalyFlags[`${currentItem.province}_${currentItem.constituency}`] || null}
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
      <footer className="fixed bottom-0 left-0 right-0 bg-white border-t py-1 text-center text-xs text-gray-400">
        ←→ / j k เลื่อน | <b>1</b> ยืนยัน | <b>2</b> ตรวจอีกรอบ | <b>3</b> ใช้ไม่ได้ | <b>r</b> รีเซ็ต | อัตโนมัติข้ามหน้าหลังกดตรวจ
      </footer>

      {/* Rate limit warning toast (F2) */}
      {rateLimitWarning && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 z-[100] bg-amber-500 text-white px-6 py-3 rounded-lg shadow-xl text-sm font-medium animate-pulse">
          ⚡ {rateLimitWarning}
        </div>
      )}

      {/* Admin Panel (F6) */}
      {showAdminPanel && (
        <AdminPanel
          reviewLog={reviewLog}
          allItems={allItems}
          review={review}
          onClose={() => setShowAdminPanel(false)}
          onImportLog={(extLog) => {
            const result = mergeReviewLogs(extLog)
            setReviewLog(result.merged)
            alert(`นำเข้าสำเร็จ: เพิ่ม ${result.added} รายการใหม่`)
          }}
        />
      )}

      {/* Upload panel */}
      {showUpload && (
        <UploadPanel
          onClose={() => setShowUpload(false)}
          onDataRefresh={loadData}
        />
      )}
    </div>
  )
}

export default App
