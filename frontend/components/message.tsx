'use client'

import styles from './chat.module.css'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface MessageProps {
  message: {
    role: 'user' | 'assistant'
    content: string
    sources?: string[]
  }
}

export default function Message({ message }: MessageProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`${styles.msgRow} ${isUser ? styles.userRow : styles.botRow}`}>
      {!isUser && <div className={styles.botAvatar}>MU</div>}
      <div className={styles.msgContent}>
        <div className={`${styles.bubble} ${isUser ? styles.userBubble : styles.botBubble}`}>
          {isUser ? (
            message.content
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          )}
        </div>
        {message.sources && message.sources.length > 0 && (
          <div className={styles.sources}>
            {message.sources.map((src, i) => (
              <a key={i} href={src} target="_blank" rel="noopener noreferrer" className={styles.sourceChip}>
                🔗 {src.replace('https://', '').slice(0, 40)}
              </a>
            ))}
          </div>
        )}
      </div>
      {isUser && <div className={styles.userAvatar}>You</div>}
    </div>
  )
}