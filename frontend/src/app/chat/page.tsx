'use client';

// frontend/src/app/chat/page.tsx — Grounded Facility Intelligence Chat Interface

import React, { useState } from 'react';
import { MessageSquare, Send, Sparkles, User, Bot, Loader2 } from 'lucide-react';
import { sendChatQuery } from '../../lib/api';

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

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text: 'Hello. I am the Kohler Facility Intelligence Assistant. I can answer questions grounded in real-time hospital hydraulic telemetry, learned baselines, and active operational dispatch tickets. How can I assist you?',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [inputValue, setInputValue] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

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
      console.error('Chat error:', err);
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

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  return (
    <div className="command-panel" style={{ padding: '24px', maxWidth: '1000px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ paddingBottom: '16px', marginBottom: '20px' }} className="tech-divider">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h2 style={{ fontSize: '0.75rem', fontWeight: 600, color: '#8f8f8f', textTransform: 'uppercase', letterSpacing: '0.06em', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <MessageSquare size={14} color="#8f8f8f" />
              FACILITY INTELLIGENCE CHAT
            </h2>
            <p style={{ fontSize: '0.8125rem', color: '#8f8f8f', marginTop: '4px' }}>
              Grounded natural-language queries evaluated over live hydraulic telemetry and PostgreSQL records.
            </p>
          </div>
          <span className="tag-tech tag-tier4">
            <Sparkles size={10} color="#4ade80" /> LLM GROUNDED
          </span>
        </div>
      </div>

      {/* Suggested Starters */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ fontSize: '0.72rem', fontWeight: 600, color: '#8f8f8f', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '8px' }}>
          Suggested Starter Queries:
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {STARTER_QUERIES.map((q, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(q)}
              className="btn-pill-outline"
              disabled={loading}
              style={{ fontSize: '0.75rem' }}
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Chat Messages Log */}
      <div style={{
        background: '#121212',
        border: '1px solid #262626',
        borderRadius: '8px',
        padding: '20px',
        minHeight: '380px',
        maxHeight: '520px',
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        marginBottom: '20px'
      }}>
        {messages.map((msg) => {
          const isUser = msg.sender === 'user';
          return (
            <div
              key={msg.id}
              style={{
                display: 'flex',
                gap: '12px',
                flexDirection: isUser ? 'row-reverse' : 'row',
                alignItems: 'flex-start'
              }}
            >
              {/* Avatar */}
              <div className="avatar-circle" style={{
                background: isUser ? '#262626' : '#181818',
                borderColor: isUser ? '#404040' : '#262626',
                color: isUser ? '#ffffff' : '#ededed',
              }}>
                {isUser ? <User size={16} /> : <Bot size={16} />}
              </div>

              {/* Message Content */}
              <div style={{
                maxWidth: '78%',
                background: isUser ? '#1f1f1f' : '#161616',
                border: `1px solid ${isUser ? '#333333' : '#262626'}`,
                borderRadius: '8px',
                padding: '12px 16px',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', marginBottom: '4px' }}>
                  <span style={{ fontSize: '0.72rem', fontWeight: 600, color: isUser ? '#ededed' : '#8f8f8f' }}>
                    {isUser ? 'Facility Manager' : 'Kohler LLM Engine'}
                  </span>
                  <span className="font-mono" style={{ fontSize: '0.65rem', color: '#525252' }}>
                    {msg.timestamp}
                  </span>
                </div>
                <div style={{ fontSize: '0.875rem', color: '#ededed', lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>
                  {msg.text}
                </div>
              </div>
            </div>
          );
        })}

        {loading && (
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <div className="avatar-circle">
              <Bot size={16} />
            </div>
            <div style={{
              background: '#161616',
              border: '1px solid #262626',
              borderRadius: '8px',
              padding: '12px 16px',
              fontSize: '0.8125rem',
              color: '#8f8f8f',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <Loader2 size={14} className="animate-spin" color="#8f8f8f" />
              Evaluating telemetry data & generating grounded response...
            </div>
          </div>
        )}
      </div>

      {/* Input Bar */}
      <div style={{ display: 'flex', gap: '10px' }}>
        <input
          type="text"
          placeholder="Ask a question about facility leaks, waste rates, or ticket status..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          style={{
            flex: 1,
            background: '#141414',
            border: '1px solid #262626',
            borderRadius: '9999px',
            padding: '10px 20px',
            fontSize: '0.875rem',
            color: '#ededed',
            outline: 'none'
          }}
        />
        <button
          onClick={() => handleSend()}
          disabled={loading || !inputValue.trim()}
          className="btn-pill-primary"
          style={{ padding: '8px 20px', opacity: (loading || !inputValue.trim()) ? 0.6 : 1 }}
        >
          <Send size={14} /> Ask Assistant
        </button>
      </div>
    </div>
  );
}
