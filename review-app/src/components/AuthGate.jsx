import React, { useEffect, useRef, useState } from 'react'

function isInAppBrowser() {
  const ua = navigator.userAgent || ''
  return /FBAN|FBAV|Instagram|Line\/|Twitter|Snapchat|TikTok/i.test(ua)
}

function openInSystemBrowser() {
  const url = window.location.href
  // Android: intent scheme opens in default browser
  if (/android/i.test(navigator.userAgent)) {
    window.location.href = 'intent://' + url.replace(/^https?:\/\//, '') + '#Intent;scheme=https;end'
    return
  }
  // iOS: window.open sometimes escapes WebView
  window.open(url, '_system')
}

export default React.memo(function AuthGate({ renderButton }) {
  const btnRef = useRef(null)
  const [inApp, setInApp] = useState(false)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    setInApp(isInAppBrowser())
  }, [])

  useEffect(() => {
    if (btnRef.current && !inApp) {
      renderButton(btnRef.current)
    }
  }, [renderButton, inApp])

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }).catch(() => {})
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-indigo-800 to-purple-900 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl p-8 sm:p-12 max-w-2xl w-full text-center">
        <div className="text-7xl sm:text-8xl mb-6">🗳️</div>
        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-3 leading-tight">ตรวจสอบคะแนน<br />หน่วยเลือกตั้ง 2569</h1>
        <p className="text-gray-500 mb-3 text-base sm:text-lg">ระบบตรวจสอบผล OCR จากแบบ สส.5/18</p>
        <p className="text-gray-400 mb-10 text-sm sm:text-base">กรุณาเข้าสู่ระบบด้วย Google เพื่อเริ่มตรวจสอบ</p>

        {inApp ? (
          <div className="mb-8 space-y-4">
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
              <p className="font-semibold mb-2">⚠️ เปิดอยู่ในแอป Facebook/LINE</p>
              <p>Google Sign-In ไม่รองรับเบราว์เซอร์ในแอป กรุณาเปิดใน Chrome หรือ Safari</p>
            </div>
            <button
              onClick={openInSystemBrowser}
              className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3.5 px-6 rounded-xl text-base transition-colors"
            >
              🌐 เปิดในเบราว์เซอร์
            </button>
            <button
              onClick={handleCopyLink}
              className="w-full bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-3 px-6 rounded-xl text-sm transition-colors"
            >
              {copied ? '✅ คัดลอกแล้ว!' : '📋 คัดลอกลิงก์ แล้วเปิดเอง'}
            </button>
          </div>
        ) : (
          <div className="flex justify-center mb-8">
            <div ref={btnRef}></div>
          </div>
        )}

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
