'use client';

// frontend/src/components/CopilotDrawer.tsx — Slide-out Copilot Side Panel
// Notion / Vercel AI-style slide-out assistant panel accessible globally across all pages.

import React, { useState, useEffect, useRef } from 'react';
import { Sparkles, X, Send, Bot, User, Loader2, RefreshCw, MessageSquare } from 'lucide-react';
import { useDashboard } from '../lib/DashboardContext';
import { sendChatQuery } from '../lib/api';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
}

const STARTER_QUERIES = [
  'Which zone has the highest water waste right now?',
  'How many active leaks are there in the hospital?',
  'Summarize the ICU scrub area status',
];

export const CopilotDrawer: React.FC = () => {
  const { isCopilotOpen, closeCopilot } = useDashboard();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text: 'Hello. I am the Kohler Facility Copilot. I can answer questions grounded in real-time hospital hydraulic telemetry, learned baselines, and active operational dispatch tickets. How can I assist you?',
      timestamp: '',
    },
  ]);
  const [inputValue, setInputValue] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [mounted, setMounted] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Auto-scroll to bottom of message thread
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isCopilotOpen) {
      scrollToBottom();
      // Focus input on open
      setTimeout(() => inputRef.current?.focus(), 200);
    }
  }, [isCopilotOpen, messages]);

  // Handle escape key to close drawer
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isCopilotOpen) {
        closeCopilot();
      }
      // Also support Cmd+K or Ctrl+K to toggle
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if (isCopilotOpen) {
          closeCopilot();
        } else {
          useDashboard().openCopilot();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isCopilotOpen, closeCopilot]);

  const handleSend = async (queryText?: string) => {
    const textToSend = (queryText || inputValue).trim();
    if (!textToSend || loading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!queryText) setInputValue('');
    setLoading(true);

    try {
      const res = await sendChatQuery(textToSend);
      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        sender: 'assistant',
        text: res.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      console.error('Copilot error:', err);
      const errorMsg: ChatMessage = {
        id: `error-${Date.now()}`,
        sender: 'assistant',
        text: 'Sorry, I encountered an error querying the facility database. Please ensure the backend server is active and try again.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleClearHistory = () => {
    setMessages([
      {
        id: 'welcome',
        sender: 'assistant',
        text: 'Chat history cleared. How can I assist you with the hospital facility telemetry?',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
  };

  return (
    <>
      {/* Backdrop overlay */}
      <div
        onClick={closeCopilot}
        style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.65)',
          backdropFilter: 'blur(4px)',
          WebkitBackdropFilter: 'blur(4px)',
          zIndex: 85,
          opacity: isCopilotOpen ? 1 : 0,
          pointerEvents: isCopilotOpen ? 'auto' : 'none',
          transition: 'opacity 0.22s ease-in-out',
        }}
      />

      {/* Slide-out Side Panel */}
      <aside
        aria-label="Kohler Copilot Drawer"
        style={{
          position: 'fixed',
          top: 0,
          right: 0,
          bottom: 0,
          width: '460px',
          maxWidth: '100vw',
          zIndex: 90,
          background: '#0d0d0d',
          borderLeft: '1px solid #262626',
          boxShadow: '-10px 0 35px rgba(0, 0, 0, 0.85)',
          transform: isCopilotOpen ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 0.28s cubic-bezier(0.16, 1, 0.3, 1)',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid #1e1e1e',
            background: '#121212',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '6px',
                background: '#1a1a1a',
                border: '1px solid #2e2e2e',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Sparkles size={16} color="#4ade80" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3
                  style={{
                    fontSize: '0.9375rem',
                    fontWeight: 600,
                    color: '#ededed',
                    letterSpacing: '-0.01em',
                  }}
                >
                  Facility Copilot
                </h3>
                <span className="tag-tech tag-tier4" style={{ fontSize: '0.62rem', padding: '1px 5px' }}>
                  GROUNDED
                </span>
              </div>
              <p style={{ fontSize: '0.72rem', color: '#737373', marginTop: '1px' }}>
                Live SQL telemetry & incident assistant
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <button
              onClick={handleClearHistory}
              title="Reset conversation"
              style={{
                background: 'transparent',
                border: '1px solid #262626',
                borderRadius: '4px',
                padding: '6px',
                color: '#737373',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.12s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = '#ededed';
                e.currentTarget.style.borderColor = '#404040';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = '#737373';
                e.currentTarget.style.borderColor = '#262626';
              }}
            >
              <RefreshCw size={13} />
            </button>
            <button
              onClick={closeCopilot}
              title="Close panel (Esc)"
              style={{
                background: 'transparent',
                border: '1px solid #262626',
                borderRadius: '4px',
                padding: '6px',
                color: '#737373',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.12s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = '#ededed';
                e.currentTarget.style.borderColor = '#404040';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = '#737373';
                e.currentTarget.style.borderColor = '#262626';
              }}
            >
              <X size={15} />
            </button>
          </div>
        </div>

        {/* Suggested Starter Queries */}
        <div
          style={{
            padding: '12px 20px',
            background: '#0a0a0a',
            borderBottom: '1px solid #1a1a1a',
          }}
        >
          <div
            style={{
              fontSize: '0.68rem',
              fontWeight: 600,
              color: '#737373',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              marginBottom: '8px',
            }}
          >
            Suggested Inquiries:
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {STARTER_QUERIES.map((q, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(q)}
                disabled={loading}
                style={{
                  textAlign: 'left',
                  fontSize: '0.75rem',
                  padding: '6px 10px',
                  borderRadius: '6px',
                  background: '#141414',
                  border: '1px solid #222222',
                  color: '#a3a3a3',
                  cursor: 'pointer',
                  transition: 'all 0.12s ease',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = '#ededed';
                  e.currentTarget.style.borderColor = '#333333';
                  e.currentTarget.style.background = '#1a1a1a';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = '#a3a3a3';
                  e.currentTarget.style.borderColor = '#222222';
                  e.currentTarget.style.background = '#141414';
                }}
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        {/* Messages Feed */}
        <div
          style={{
            flex: 1,
            padding: '18px 20px',
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
          }}
        >
          {messages.map((msg) => {
            const isUser = msg.sender === 'user';
            return (
              <div
                key={msg.id}
                style={{
                  display: 'flex',
                  gap: '10px',
                  flexDirection: isUser ? 'row-reverse' : 'row',
                  alignItems: 'flex-start',
                }}
              >
                {/* Avatar */}
                <div
                  className="avatar-circle"
                  style={{
                    width: '28px',
                    height: '28px',
                    background: isUser ? '#262626' : '#141414',
                    borderColor: isUser ? '#404040' : '#262626',
                    color: isUser ? '#ffffff' : '#4ade80',
                    fontSize: '0.7rem',
                  }}
                >
                  {isUser ? <User size={13} /> : <Bot size={13} />}
                </div>

                {/* Bubble */}
                <div
                  style={{
                    maxWidth: '82%',
                    background: isUser ? '#1c1c1c' : '#141414',
                    border: `1px solid ${isUser ? '#2e2e2e' : '#222222'}`,
                    borderRadius: '8px',
                    padding: '10px 14px',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: '8px',
                      marginBottom: '4px',
                    }}
                  >
                    <span
                      style={{
                        fontSize: '0.68rem',
                        fontWeight: 600,
                        color: isUser ? '#ededed' : '#8f8f8f',
                      }}
                    >
                      {isUser ? 'You' : 'Copilot'}
                    </span>
                    <span className="font-mono" style={{ fontSize: '0.62rem', color: '#525252' }}>
                      {mounted ? (msg.timestamp || '') : ''}
                    </span>
                  </div>
                  <div
                    style={{
                      fontSize: '0.8125rem',
                      color: '#ededed',
                      lineHeight: 1.5,
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                    }}
                  >
                    {msg.text}
                  </div>
                </div>
              </div>
            );
          })}

          {loading && (
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <div
                className="avatar-circle"
                style={{ width: '28px', height: '28px', color: '#4ade80' }}
              >
                <Bot size={13} />
              </div>
              <div
                style={{
                  background: '#141414',
                  border: '1px solid #222222',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  fontSize: '0.75rem',
                  color: '#8f8f8f',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <Loader2 size={13} className="animate-spin" color="#4ade80" />
                Querying database & generating response...
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div
          style={{
            padding: '14px 20px',
            borderTop: '1px solid #1e1e1e',
            background: '#121212',
          }}
        >
          <div style={{ display: 'flex', gap: '8px' }}>
            <input
              ref={inputRef}
              type="text"
              placeholder="Ask Copilot about facility telemetry..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleSend();
                }
              }}
              disabled={loading}
              style={{
                flex: 1,
                background: '#161616',
                border: '1px solid #262626',
                borderRadius: '9999px',
                padding: '8px 16px',
                fontSize: '0.8125rem',
                color: '#ededed',
                outline: 'none',
              }}
            />
            <button
              onClick={() => handleSend()}
              disabled={loading || !inputValue.trim()}
              className="btn-pill-primary"
              style={{
                padding: '6px 14px',
                fontSize: '0.75rem',
                opacity: (loading || !inputValue.trim()) ? 0.5 : 1,
              }}
            >
              <Send size={13} />
            </button>
          </div>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginTop: '8px',
              padding: '0 4px',
            }}
          >
            <span style={{ fontSize: '0.65rem', color: '#525252' }}>
              Press <kbd style={{ padding: '1px 4px', background: '#1c1c1c', border: '1px solid #2a2a2a', borderRadius: '3px' }}>Enter</kbd> to send
            </span>
            <span style={{ fontSize: '0.65rem', color: '#525252' }}>
              <kbd style={{ padding: '1px 4px', background: '#1c1c1c', border: '1px solid #2a2a2a', borderRadius: '3px' }}>Esc</kbd> to close
            </span>
          </div>
        </div>
      </aside>
    </>
  );
};
