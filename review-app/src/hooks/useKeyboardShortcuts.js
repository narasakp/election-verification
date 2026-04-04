import { useEffect } from 'react'
import { toast } from '../components/Toast'

export default function useKeyboardShortcuts({
  goNext, goPrev, currentItem, setItemStatus,
  autoApproveEnabled, setAutoApproveEnabled,
  bulkAutoApprove, bulkConfirmAll,
  priorityQueueEnabled, setPriorityQueueEnabled,
}) {
  useEffect(() => {
    const handler = (e) => {
      // Escape: blur active input so shortcuts work again
      if (e.key === 'Escape') {
        if (document.activeElement) document.activeElement.blur()
        return
      }
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return
      if (e.key === 'ArrowRight' || e.key === 'j') goNext()
      if (e.key === 'ArrowLeft' || e.key === 'k') goPrev()
      // Review shortcuts: 1=confirm, 2=flag, 3=reject, r=reset
      if (currentItem) {
        if (e.key === '1') {
          if (window.confirm('✅ ยืนยัน\n\nตรวจสอบตัวเลขกับภาพต้นฉบับแล้ว ถูกต้อง\nหน้านี้จะถูกนับเป็นข้อมูลที่ผ่านการตรวจสอบแล้ว\n\nยืนยันหรือไม่?')) {
            setItemStatus(currentItem.id, 'confirmed')
          }
        }
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
        if (e.key === 'r') {
          if (window.confirm('↩ รีเซ็ต\n\nสถานะจะกลับเป็น "รอตรวจ"\nค่าแก้ไขและหมายเหตุจะยังอยู่\n\nยืนยันหรือไม่?')) {
            setItemStatus(currentItem.id, 'pending')
          }
        }
      }
      
      // Bulk shortcuts (Ctrl key required for safety)
      if (e.ctrlKey) {
        if (e.key === 'a') {
          e.preventDefault()
          if (autoApproveEnabled) {
            bulkAutoApprove()
          } else {
            toast('⚠️ Auto-approve is disabled. Enable it first with Ctrl+A (hold Ctrl, press A twice)', 'warning', 4000)
          }
        }
        if (e.key === 'b') {
          e.preventDefault()
          bulkConfirmAll()
        }
        if (e.key === 'p') {
          e.preventDefault()
          setPriorityQueueEnabled(v => !v)
          toast(`🔄 Priority queue ${!priorityQueueEnabled ? 'enabled' : 'disabled'}`, 'info')
        }
      }
      
      // Toggle shortcuts (no Ctrl required)
      if (e.key === 'A' && e.shiftKey) {
        setAutoApproveEnabled(v => !v)
        toast(`🤖 Auto-approve ${!autoApproveEnabled ? 'enabled' : 'disabled'}`, 'info')
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [goNext, goPrev, currentItem, setItemStatus, autoApproveEnabled, bulkAutoApprove, bulkConfirmAll, priorityQueueEnabled, setAutoApproveEnabled, setPriorityQueueEnabled])
}
