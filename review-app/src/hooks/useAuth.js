import { useState, useEffect, useCallback, useRef } from 'react'

const GOOGLE_CLIENT_ID = '736775121629-tvgr9qd9eoceb2o14faunlc8upfton2o.apps.googleusercontent.com'

export default function useAuth() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const btnRef = useRef(null)
  const initialized = useRef(false)

  const handleCredential = useCallback((response) => {
    try {
      const payload = JSON.parse(atob(response.credential.split('.')[1]))
      // Normalize picture URL: remove size restriction for better quality
      let pic = payload.picture || ''
      if (pic && pic.includes('=s')) {
        pic = pic.replace(/=s\d+-c/, '=s200-c')
      }
      const u = {
        email: payload.email,
        name: payload.name || payload.email.split('@')[0],
        picture: pic,
        sub: payload.sub,
      }
      setUser(u)
      localStorage.setItem('auth_user', JSON.stringify(u))
    } catch (e) {
      console.error('Sign-in decode error', e)
    }
  }, [])

  const initGsi = useCallback(() => {
    if (typeof google === 'undefined' || !google.accounts) {
      setTimeout(initGsi, 300)
      return
    }
    if (initialized.current) return
    initialized.current = true

    google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: handleCredential,
      auto_select: true,
    })
    // Try auto sign-in
    google.accounts.id.prompt()
    setLoading(false)
  }, [handleCredential])

  useEffect(() => {
    // Restore from localStorage
    const saved = localStorage.getItem('auth_user')
    if (saved) {
      try { setUser(JSON.parse(saved)) } catch {}
    }
    initGsi()
  }, [initGsi])

  const renderButton = useCallback((el) => {
    if (!el || !initialized.current) return
    try {
      google.accounts.id.renderButton(el, {
        type: 'standard',
        theme: 'outline',
        size: 'large',
        text: 'signin_with',
        locale: 'th',
        width: 300,
      })
    } catch {}
  }, [])

  const signOut = useCallback(() => {
    setUser(null)
    localStorage.removeItem('auth_user')
    if (typeof google !== 'undefined' && google.accounts) {
      google.accounts.id.disableAutoSelect()
    }
  }, [])

  return { user, loading, signOut, renderButton }
}
