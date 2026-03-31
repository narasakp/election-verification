import React, { useEffect, useRef } from 'react'

export default React.memo(function AuthGate({ renderButton }) {
  const btnRef = useRef(null)

  useEffect(() => {
    if (btnRef.current) {
      renderButton(btnRef.current)
    }
  }, [renderButton])

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-indigo-800 to-purple-900 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl p-8 sm:p-12 max-w-2xl w-full text-center">
        <div className="text-7xl sm:text-8xl mb-6">🗳️</div>
        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-3 leading-tight">ตรวจสอบคะแนน<br />หน่วยเลือกตั้ง 2569</h1>
        <p className="text-gray-500 mb-3 text-base sm:text-lg">ระบบตรวจสอบผล OCR จากแบบ สส.5/18</p>
        <p className="text-gray-400 mb-10 text-sm sm:text-base">กรุณาเข้าสู่ระบบด้วย Google เพื่อเริ่มตรวจสอบ</p>

        <div className="flex justify-center mb-8">
          <div ref={btnRef}></div>
        </div>

        <div className="text-left bg-indigo-50 rounded-xl p-5 sm:p-6 text-sm sm:text-base text-gray-600 space-y-3">
          <p className="font-semibold text-indigo-900 text-base sm:text-lg">ขั้นตอนการตรวจสอบ:</p>
          <div className="flex gap-3"><span className="bg-indigo-200 text-indigo-800 rounded-full w-7 h-7 flex items-center justify-center text-sm font-bold shrink-0">1</span> เข้าสู่ระบบด้วย Google</div>
          <div className="flex gap-3"><span className="bg-indigo-200 text-indigo-800 rounded-full w-7 h-7 flex items-center justify-center text-sm font-bold shrink-0">2</span> ดูเอกสารต้นฉบับ (PDF จาก กกต.)</div>
          <div className="flex gap-3"><span className="bg-indigo-200 text-indigo-800 rounded-full w-7 h-7 flex items-center justify-center text-sm font-bold shrink-0">3</span> เทียบกับตัวเลขที่ระบบอ่านได้</div>
          <div className="flex gap-3"><span className="bg-indigo-200 text-indigo-800 rounded-full w-7 h-7 flex items-center justify-center text-sm font-bold shrink-0">4</span> กด ยืนยัน / ตรวจอีกรอบ / ใช้ไม่ได้</div>
        </div>

        <p className="text-sm text-gray-400 mt-5">ยิ่งมีคนตรวจซ้ำมากคน ผลยิ่งน่าเชื่อถือ (Consensus-based)</p>
      </div>
    </div>
  )
})
