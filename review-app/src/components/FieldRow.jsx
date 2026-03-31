import React, { useState } from 'react'
import { Pencil, Check, X } from 'lucide-react'

function getConfidenceStyle(confidence) {
  if (!confidence) return { bg: 'bg-gray-50', border: 'border-gray-200', badge: 'bg-gray-200 text-gray-600', label: '-' }
  if (confidence.startsWith('high')) return { bg: 'bg-green-50', border: 'border-green-200', badge: 'bg-green-100 text-green-700', label: 'HIGH' }
  if (confidence.startsWith('medium')) return { bg: 'bg-yellow-50', border: 'border-yellow-200', badge: 'bg-yellow-100 text-yellow-700', label: 'MED' }
  if (confidence.startsWith('low')) return { bg: 'bg-red-50', border: 'border-red-200', badge: 'bg-red-100 text-red-700', label: 'LOW' }
  if (confidence === 'none') return { bg: 'bg-gray-50', border: 'border-gray-200', badge: 'bg-gray-200 text-gray-500', label: 'NONE' }
  return { bg: 'bg-gray-50', border: 'border-gray-200', badge: 'bg-gray-200 text-gray-600', label: '?' }
}

export default React.memo(function FieldRow({ label, unit, value, confidence, correctedValue, onCorrect }) {
  const [editing, setEditing] = useState(false)
  const [editVal, setEditVal] = useState('')
  const style = getConfidenceStyle(confidence)
  const displayValue = correctedValue !== undefined ? correctedValue : value
  const isCorrected = correctedValue !== undefined && correctedValue !== value

  const startEdit = () => {
    setEditVal(displayValue ?? '')
    setEditing(true)
  }

  const confirmEdit = () => {
    const num = editVal === '' ? null : parseInt(editVal, 10)
    onCorrect(isNaN(num) ? editVal : num)
    setEditing(false)
  }

  const cancelEdit = () => {
    setEditing(false)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') confirmEdit()
    if (e.key === 'Escape') cancelEdit()
  }

  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded border ${style.bg} ${style.border}`}>
      {/* Label */}
      <span className="text-sm text-gray-600 w-40 shrink-0">{label}</span>

      {/* Value */}
      <div className="flex-1 flex items-center gap-2">
        {editing ? (
          <div className="flex items-center gap-1">
            <input
              type="text"
              value={editVal}
              onChange={e => setEditVal(e.target.value)}
              onKeyDown={handleKeyDown}
              className="w-24 px-2 py-0.5 border rounded text-sm focus:ring-2 focus:ring-blue-400 outline-none"
              autoFocus
            />
            <button onClick={confirmEdit} className="text-green-600 hover:text-green-800">
              <Check size={14} />
            </button>
            <button onClick={cancelEdit} className="text-gray-400 hover:text-gray-600">
              <X size={14} />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-1">
            <span className={`font-semibold text-sm ${value === null ? 'text-gray-400 italic' : ''} ${isCorrected ? 'line-through text-gray-400' : ''}`}>
              {value ?? 'N/A'}
            </span>
            {isCorrected && (
              <span className="font-semibold text-sm text-blue-600">
                → {correctedValue}
              </span>
            )}
            {unit && <span className="text-xs text-gray-400">{unit}</span>}
            <button onClick={startEdit} className="ml-1 text-gray-300 hover:text-blue-500 transition">
              <Pencil size={12} />
            </button>
          </div>
        )}
      </div>

      {/* Confidence badge */}
      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${style.badge}`} title={confidence || ''}>
        {style.label}
      </span>

      {/* Confidence detail */}
      {confidence && confidence !== 'none' && !confidence.startsWith('high') && (
        <span className="text-[10px] text-gray-400 max-w-32 truncate" title={confidence}>
          {confidence.replace(/^(low|medium):/, '')}
        </span>
      )}
    </div>
  )
})
