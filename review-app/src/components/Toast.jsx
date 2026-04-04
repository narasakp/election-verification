import React, { useState, useEffect, useCallback, useRef } from 'react'
import { X, CheckCircle, AlertTriangle, Info } from 'lucide-react'

const ICONS = {
  success: <CheckCircle size={16} className="text-green-500 flex-shrink-0" />,
  warning: <AlertTriangle size={16} className="text-amber-500 flex-shrink-0" />,
  error: <AlertTriangle size={16} className="text-red-500 flex-shrink-0" />,
  info: <Info size={16} className="text-blue-500 flex-shrink-0" />,
}

const BG = {
  success: 'bg-green-50 border-green-200 text-green-800',
  warning: 'bg-amber-50 border-amber-200 text-amber-800',
  error: 'bg-red-50 border-red-200 text-red-800',
  info: 'bg-blue-50 border-blue-200 text-blue-800',
}

function ToastItem({ toast, onDismiss }) {
  const [exiting, setExiting] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => {
      setExiting(true)
      setTimeout(() => onDismiss(toast.id), 300)
    }, toast.duration || 3000)
    return () => clearTimeout(timer)
  }, [toast, onDismiss])

  return (
    <div
      className={`flex items-start gap-2 px-4 py-3 rounded-lg border shadow-lg max-w-sm transition-all duration-300 ${BG[toast.type] || BG.info} ${
        exiting ? 'opacity-0 translate-x-8' : 'opacity-100 translate-x-0'
      }`}
      role="alert"
    >
      {ICONS[toast.type] || ICONS.info}
      <span className="text-sm font-medium flex-1">{toast.message}</span>
      <button onClick={() => { setExiting(true); setTimeout(() => onDismiss(toast.id), 300) }} className="text-current opacity-50 hover:opacity-100 flex-shrink-0" aria-label="ปิด">
        <X size={14} />
      </button>
    </div>
  )
}

let _addToast = null

export function toast(message, type = 'info', duration = 3000) {
  if (_addToast) _addToast({ message, type, duration })
}

export default function ToastContainer() {
  const [toasts, setToasts] = useState([])
  const idRef = useRef(0)

  const addToast = useCallback((t) => {
    const id = ++idRef.current
    setToasts(prev => [...prev, { ...t, id }])
  }, [])

  const dismiss = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  useEffect(() => {
    _addToast = addToast
    return () => { _addToast = null }
  }, [addToast])

  if (toasts.length === 0) return null

  return (
    <div className="fixed top-16 right-4 z-[200] flex flex-col gap-2" aria-live="polite">
      {toasts.map(t => (
        <ToastItem key={t.id} toast={t} onDismiss={dismiss} />
      ))}
    </div>
  )
}
