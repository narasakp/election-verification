import React from 'react'

function fv(val) {
  if (val === null || val === undefined) return <span className="text-gray-300">—</span>
  return String(val)
}

export default function CandidateTable({ candidates, allParties, edits, onEdit, isFirstPage, sharedEdits, onSharedEdit }) {
  if (!candidates || candidates.length === 0) return null

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="bg-gray-50 text-left">
            <th className="px-2 py-1.5 text-xs font-semibold text-gray-500 w-8">#</th>
            <th className="px-2 py-1.5 text-xs font-semibold text-gray-500">ชื่อผู้สมัคร</th>
            <th className="px-2 py-1.5 text-xs font-semibold text-gray-500">พรรค</th>
            <th className="px-2 py-1.5 text-xs font-semibold text-gray-500 text-right">คะแนน OCR</th>
            <th className="px-2 py-1.5 text-xs font-semibold text-gray-500 text-right">✏️ แก้ไข</th>
          </tr>
        </thead>
        <tbody>
          {candidates.map((c, ci) => {
            const nameKey = `cand_${ci}_name`
            const partyKey = `cand_${ci}_party`
            const votesKey = `cand_${ci}_votes`
            // Shared edits for name/party (constituency-level)
            const sharedName = sharedEdits?.[nameKey]
            const sharedParty = sharedEdits?.[partyKey]
            const hasSharedName = sharedName !== undefined
            const hasSharedParty = sharedParty !== undefined
            // Per-page edits for votes
            const votesEdited = edits?.[votesKey]

            // Display values: shared edit > original
            const displayName = hasSharedName ? sharedName : (c.name || '')
            const displayParty = hasSharedParty ? sharedParty : (c.party || '')

            return (
              <tr key={ci} className="border-t hover:bg-blue-50/50 transition">
                <td className="px-2 py-1 text-gray-400">{fv(c.number)}</td>
                <td className="px-2 py-1">
                  <input
                    className={`w-full px-1 py-0.5 border rounded text-sm ${
                      !isFirstPage
                        ? 'border-gray-100 bg-gray-50 text-gray-400 cursor-not-allowed'
                        : hasSharedName ? 'border-indigo-400 bg-indigo-50 font-semibold' : 'border-gray-200'
                    }`}
                    value={displayName}
                    onChange={isFirstPage ? (e => onSharedEdit(nameKey, e.target.value, c.name)) : undefined}
                    disabled={!isFirstPage}
                    title={!isFirstPage ? 'แก้ได้ที่หน้าแรกของเขตเท่านั้น' : undefined}
                  />
                </td>
                <td className="px-2 py-1">
                  <select
                    className={`w-full px-1 py-0.5 border rounded text-sm ${
                      !isFirstPage
                        ? 'border-gray-100 bg-gray-50 text-gray-400 cursor-not-allowed'
                        : hasSharedParty ? 'border-indigo-400 bg-indigo-50 font-semibold' : 'border-gray-200'
                    }`}
                    value={displayParty}
                    onChange={isFirstPage ? (e => onSharedEdit(partyKey, e.target.value, c.party)) : undefined}
                    disabled={!isFirstPage}
                    title={!isFirstPage ? 'แก้ได้ที่หน้าแรกของเขตเท่านั้น' : undefined}
                  >
                    <option value="">— ไม่ทราบ —</option>
                    {allParties.map(p => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                </td>
                <td className="px-2 py-1 text-right font-medium">{fv(c.votes)}</td>
                <td className="px-2 py-1 text-right">
                  <input
                    className={`w-[90px] px-1.5 py-0.5 border rounded text-sm text-right ${votesEdited !== undefined ? 'border-amber-400 bg-amber-50 font-semibold' : 'border-gray-200'}`}
                    value={votesEdited !== undefined ? votesEdited : (c.votes == null ? '' : String(c.votes))}
                    onChange={e => onEdit(votesKey, e.target.value, c.votes)}
                    placeholder="ที่ถูกต้อง"
                  />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
