'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Message from './message'
import styles from './chat.module.css'

interface MessageType {
  role: 'user' | 'assistant'
  content: string
  sources?: string[]
}

interface SessionType {
  session_id: string
  title: string
  created_at: string
}

const SUGGESTIONS = [
  'What courses are offered?',
  'How do I apply for admission?',
  'What are the hostel facilities?',
  'Tell me about the faculty',
  'What are the fee details?',
  'Campus facilities available?',
]

const WELCOME_MESSAGE = "Hi! I'm your Manavrachna University assistant. I can help you with admissions, courses, faculty, fees, events, and more. What would you like to know?"

export default function Chat() {
  const router = useRouter()

  // Authentication states
  const [token, setToken] = useState<string | null>(null)
  const [userEmail, setUserEmail] = useState<string | null>(null)
  const [checkingAuth, setCheckingAuth] = useState(true)

  // Chat sessions states
  const [sessions, setSessions] = useState<SessionType[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Core Chat states
  const [messages, setMessages] = useState<MessageType[]>([
    { role: 'assistant', content: WELCOME_MESSAGE }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const typingIntervalRef = useRef<NodeJS.Timeout | null>(null)

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  // Load auth state on mount
  useEffect(() => {
    const savedToken = localStorage.getItem('token')
    const savedEmail = localStorage.getItem('email')
    if (savedToken && savedEmail) {
      setToken(savedToken)
      setUserEmail(savedEmail)
      fetchSessions(savedToken)
    } else {
      // Guest mode setup
      setToken(null)
      setUserEmail(null)
      let guestSessionId = localStorage.getItem('guest_session_id')
      if (!guestSessionId) {
        guestSessionId = 'guest_' + Math.random().toString(36).slice(2)
        localStorage.setItem('guest_session_id', guestSessionId)
      }
      setActiveSessionId(guestSessionId)
      loadGuestSessionHistory(guestSessionId)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Auto-scroll when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: isStreaming ? 'auto' : 'smooth' })
  }, [messages, loading, isStreaming])

  // Cleanup timers
  useEffect(() => {
    return () => {
      if (typingIntervalRef.current) clearInterval(typingIntervalRef.current)
    }
  }, [])

  // Sessions management (Logged In Users)
  const fetchSessions = async (authToken: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/chats`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      })
      if (res.status === 401) {
        handleLogout()
        return
      }
      const data = await res.json()
      setSessions(data)

      if (data.length > 0) {
        const firstSession = data[0]
        setActiveSessionId(firstSession.session_id)
        loadSessionHistory(firstSession.session_id, authToken)
      } else {
        createSession(authToken)
      }
    } catch (err) {
      console.error('Failed to load chat sessions:', err)
    } finally {
      setCheckingAuth(false)
    }
  }

  const createSession = async (authToken: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/chats`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        }
      })
      const newSession = await res.json()
      setSessions(prev => [newSession, ...prev])
      setActiveSessionId(newSession.session_id)
      setMessages([{ role: 'assistant', content: WELCOME_MESSAGE }])
    } catch (err) {
      console.error('Failed to create new session:', err)
    }
  }

  const loadSessionHistory = async (sessionId: string, authToken: string) => {
    setLoading(true)
    setMessages([])
    try {
      const res = await fetch(`${API_BASE_URL}/api/chats/${sessionId}`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      })
      const history = await res.json()
      if (history.length === 0) {
        setMessages([{ role: 'assistant', content: WELCOME_MESSAGE }])
      } else {
        setMessages(history)
      }
    } catch (err) {
      console.error('Failed to load session history:', err)
      setMessages([{ role: 'assistant', content: WELCOME_MESSAGE }])
    } finally {
      setLoading(false)
    }
  }

  // Session history loading (Guest Mode)
  const loadGuestSessionHistory = async (sessionId: string) => {
    setLoading(true)
    setMessages([])
    try {
      const res = await fetch(`${API_BASE_URL}/api/chats/${sessionId}`)
      const history = await res.json()
      if (history.length === 0) {
        setMessages([{ role: 'assistant', content: WELCOME_MESSAGE }])
      } else {
        setMessages(history)
      }
    } catch (err) {
      console.error('Failed to load guest history:', err)
      setMessages([{ role: 'assistant', content: WELCOME_MESSAGE }])
    } finally {
      setLoading(false)
      setCheckingAuth(false)
    }
  }

  const deleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!token) return

    try {
      const res = await fetch(`${API_BASE_URL}/api/chats/${sessionId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (res.ok) {
        const updatedSessions = sessions.filter(s => s.session_id !== sessionId)
        setSessions(updatedSessions)

        if (activeSessionId === sessionId) {
          if (updatedSessions.length > 0) {
            setActiveSessionId(updatedSessions[0].session_id)
            loadSessionHistory(updatedSessions[0].session_id, token)
          } else {
            createSession(token)
          }
        }
      }
    } catch (err) {
      console.error('Failed to delete session:', err)
    }
  }

  const selectSession = (sessionId: string) => {
    if (sessionId === activeSessionId || !token) return
    setActiveSessionId(sessionId)
    loadSessionHistory(sessionId, token)
    setSidebarOpen(false) // Close drawer on mobile
  }

  const handleNewChatBtn = () => {
    if (token) {
      createSession(token)
    } else {
      // Guest mode fresh session
      const newSessionId = 'guest_' + Math.random().toString(36).slice(2)
      localStorage.setItem('guest_session_id', newSessionId)
      setActiveSessionId(newSessionId)
      setMessages([{ role: 'assistant', content: WELCOME_MESSAGE }])
    }
    setSidebarOpen(false)
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('email')
    setToken(null)
    setUserEmail(null)
    setSessions([])
    
    // Switch to fresh guest session
    const guestSessionId = 'guest_' + Math.random().toString(36).slice(2)
    localStorage.setItem('guest_session_id', guestSessionId)
    setActiveSessionId(guestSessionId)
    setMessages([{ role: 'assistant', content: WELCOME_MESSAGE }])
    
    router.push('/login')
  }

  // Send Message Logic
  const handleSend = async (text?: string) => {
    const question = text || input.trim()
    if (!question || loading || isStreaming) return

    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'

    setMessages(prev => [...prev, { role: 'user', content: question }])
    setLoading(true)

    // Optimistically update session title in sidebar (only if logged in and title is 'New Chat')
    const currentSession = sessions.find(s => s.session_id === activeSessionId)
    const isNewChat = currentSession && currentSession.title === 'New Chat'
    if (isNewChat && token) {
      setSessions(prev =>
        prev.map(s =>
          s.session_id === activeSessionId
            ? { ...s, title: question.length > 25 ? question.slice(0, 22) + '...' : question }
            : s
        )
      )
    }

    try {
      const headers: HeadersInit = { 'Content-Type': 'application/json' }
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }

      const res = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          message: question,
          session_id: activeSessionId
        })
      })

      if (res.status === 401) {
        handleLogout()
        return
      }

      const data = await res.json()
      setLoading(false)
      setIsStreaming(true)

      const fullAnswer = data.answer || ''
      const sources = data.sources || []

      if (token) {
        if (data.session_id && data.session_id !== activeSessionId) {
          setActiveSessionId(data.session_id)
          fetchSessions(token)
        } else if (isNewChat) {
          fetchSessions(token)
        }
      }

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '',
        sources: []
      }])

      if (typingIntervalRef.current) clearInterval(typingIntervalRef.current)

      const words = fullAnswer.split(/(\s+)/)
      let wordIndex = 0

      typingIntervalRef.current = setInterval(() => {
        if (wordIndex < words.length) {
          wordIndex = Math.min(wordIndex + 8, words.length)
          const nextChunk = words.slice(0, wordIndex).join('')
          setMessages(prev => {
            const updated = [...prev]
            if (updated.length > 0) {
              updated[updated.length - 1] = {
                ...updated[updated.length - 1],
                content: nextChunk
              }
            }
            return updated
          })
        } else {
          if (typingIntervalRef.current) clearInterval(typingIntervalRef.current)
          setIsStreaming(false)
          setMessages(prev => {
            const updated = [...prev]
            if (updated.length > 0) {
              updated[updated.length - 1] = {
                ...updated[updated.length - 1],
                sources: sources
              }
            }
            return updated
          })
        }
      }, 10)
    } catch {
      setLoading(false)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I could not connect to the server. Please try again.'
      }])
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleResize = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
  }

  if (checkingAuth) {
    return (
      <div className={styles.page}>
        <div style={{ color: '#888780', fontSize: '14px' }}>Loading assistant...</div>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        
        {sidebarOpen && (
          <div className={styles.sidebarBackdrop} onClick={() => setSidebarOpen(false)} />
        )}

        <aside className={`${styles.sidebar} ${sidebarOpen ? styles.sidebarOpen : ''}`}>
          <div className={styles.sidebarHeader}>
            <div className={styles.sidebarLogo}>MU</div>
            <div>
              <div className={styles.sidebarTitle}>Manavrachna</div>
              <div className={styles.sidebarUserEmail} title={userEmail || 'Anonymous Guest'}>
                {userEmail || 'Guest Mode 👤'}
              </div>
            </div>
          </div>

          <button className={styles.newChatBtn} onClick={handleNewChatBtn}>
            <span>+</span> New Chat
          </button>

          <div className={styles.sessionList}>
            <div className={styles.sessionListTitle}>Recent Chats</div>
            {token ? (
              <>
                {sessions.map(s => (
                  <div
                    key={s.session_id}
                    className={`${styles.sessionItem} ${s.session_id === activeSessionId ? styles.sessionItemActive : ''}`}
                    onClick={() => selectSession(s.session_id)}
                  >
                    <span className={styles.sessionItemIcon}>💬</span>
                    <span className={styles.sessionItemText}>{s.title}</span>
                    <button
                      className={styles.sessionDeleteBtn}
                      onClick={(e) => deleteSession(s.session_id, e)}
                      title="Delete Chat"
                    >
                      ✕
                    </button>
                  </div>
                ))}
                {sessions.length === 0 && (
                  <div className={styles.emptySessions}>No recent conversations.</div>
                )}
              </>
            ) : (
              <div className={styles.emptySessions} style={{ textAlign: 'left', lineHeight: '1.5', padding: '10px 8px' }}>
                💬 <strong>Active Guest Chat</strong>
                <p style={{ fontSize: '11px', color: '#b4b2a9', marginTop: '6px', margin: '4px 0 0 0' }}>
                  Sign in to save your history permanently and chat across devices!
                </p>
              </div>
            )}
          </div>

          <div className={styles.sidebarFooter}>
            {token ? (
              <button className={styles.logoutBtn} onClick={handleLogout}>
                Logout
              </button>
            ) : (
              <button className={styles.loginBtn} onClick={() => router.push('/login')}>
                Sign In / Register
              </button>
            )}
          </div>
        </aside>

        <main className={styles.chatArea}>
          
          <div className={styles.header}>
            <button
              className={styles.hamburgerBtn}
              onClick={() => setSidebarOpen(true)}
              aria-label="Open sidebar"
            >
              ☰
            </button>
            <div className={styles.headerLogo}>MU</div>
            <div>
              <div className={styles.headerTitle}>Manavrachna University</div>
              <div className={styles.headerSub}>College Assistant</div>
            </div>
            <div className={styles.status}>
              <span className={styles.statusDot}></span>
              Online
            </div>
          </div>

          <div className={styles.messages}>
            {messages.map((msg, i) => (
              <Message key={i} message={msg} />
            ))}

            {messages.length === 1 && messages[0].content === WELCOME_MESSAGE && (
              <div className={styles.suggestions}>
                {SUGGESTIONS.map((s, i) => (
                  <button
                    key={i}
                    className={styles.suggestionBtn}
                    onClick={() => handleSend(s)}
                    disabled={loading || isStreaming}
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}

            {loading && (
              <div className={styles.typingRow}>
                <div className={styles.botAvatar}>MU</div>
                <div className={styles.typing}>
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          <div className={styles.inputArea}>
            <div className={styles.inputBox}>
              <textarea
                ref={textareaRef}
                value={input}
                onChange={handleResize}
                onKeyDown={handleKeyDown}
                placeholder="Ask anything about Manavrachna University..."
                rows={1}
                disabled={loading || isStreaming}
                className={styles.textarea}
              />
              <button
                onClick={() => handleSend()}
                disabled={!input.trim() || loading || isStreaming}
                className={styles.sendBtn}
                aria-label="Send"
              >
                ↑
              </button>
            </div>
            <p className={styles.disclaimer}>
              Answers are based on the official Manavrachna University website.
            </p>
          </div>

        </main>

      </div>
    </div>
  )
}