'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import styles from '../../components/chat.module.css'

export default function LoginPage() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<'login' | 'register'>('login')
  const [emailInput, setEmailInput] = useState('')
  const [passwordInput, setPasswordInput] = useState('')
  const [confirmPasswordInput, setConfirmPasswordInput] = useState('')
  const [authError, setAuthError] = useState<string | null>(null)
  const [authSuccess, setAuthSuccess] = useState<string | null>(null)
  const [authLoading, setAuthLoading] = useState(false)

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  // Redirect to home if already logged in
  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      router.push('/')
    }
  }, [router])

  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setAuthError(null)
    setAuthSuccess(null)

    if (!emailInput.trim() || !passwordInput) {
      setAuthError('Please fill in all fields.')
      return
    }

    if (activeTab === 'register') {
      if (passwordInput !== confirmPasswordInput) {
        setAuthError('Passwords do not match.')
        return
      }
      if (passwordInput.length < 6) {
        setAuthError('Password must be at least 6 characters.')
        return
      }
    }

    setAuthLoading(true)

    try {
      if (activeTab === 'login') {
        const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: emailInput, password: passwordInput })
        })

        const data = await res.json()
        if (!res.ok) {
          setAuthError(data.detail || 'Login failed. Please check your credentials.')
          setAuthLoading(false)
          return
        }

        localStorage.setItem('token', data.token)
        localStorage.setItem('email', data.email)
        
        // Redirect to chatbot home
        router.push('/')
      } else {
        const res = await fetch(`${API_BASE_URL}/api/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: emailInput, password: passwordInput })
        })

        const data = await res.json()
        if (!res.ok) {
          setAuthError(data.detail || 'Registration failed.')
          setAuthLoading(false)
          return
        }

        setAuthSuccess('Registration successful! Please login.')
        setActiveTab('login')
        setPasswordInput('')
        setConfirmPasswordInput('')
      }
    } catch {
      setAuthError('Could not connect to authentication server. Is the backend running?')
    } finally {
      setAuthLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.authContainer}>
        <div className={styles.authHeader}>
          <div className={styles.authLogo}>MU</div>
          <h1>Manavrachna Assistant</h1>
          <p>Welcome! Register or login to query the University Knowledge Base and save your chat history.</p>
        </div>

        <div className={styles.authTabs}>
          <button
            type="button"
            className={`${styles.authTabBtn} ${activeTab === 'login' ? styles.authTabBtnActive : ''}`}
            onClick={() => { setActiveTab('login'); setAuthError(null); setAuthSuccess(null); }}
          >
            Sign In
          </button>
          <button
            type="button"
            className={`${styles.authTabBtn} ${activeTab === 'register' ? styles.authTabBtnActive : ''}`}
            onClick={() => { setActiveTab('register'); setAuthError(null); setAuthSuccess(null); }}
          >
            Register
          </button>
        </div>

        <form onSubmit={handleAuthSubmit} className={styles.authForm}>
          {authError && <div className={styles.authErrorAlert}>{authError}</div>}
          {authSuccess && <div className={styles.authSuccessAlert}>{authSuccess}</div>}

          <div className={styles.authField}>
            <label htmlFor="email">Email Address</label>
            <input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={emailInput}
              onChange={e => setEmailInput(e.target.value)}
              required
            />
          </div>

          <div className={styles.authField}>
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              placeholder="••••••••"
              value={passwordInput}
              onChange={e => setPasswordInput(e.target.value)}
              required
            />
          </div>

          {activeTab === 'register' && (
            <div className={styles.authField}>
              <label htmlFor="confirm-password">Confirm Password</label>
              <input
                id="confirm-password"
                type="password"
                placeholder="••••••••"
                value={confirmPasswordInput}
                onChange={e => setConfirmPasswordInput(e.target.value)}
                required
              />
            </div>
          )}

          <button type="submit" className={styles.authSubmitBtn} disabled={authLoading}>
            {authLoading ? 'Please wait...' : activeTab === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>
      </div>
    </div>
  )
}
