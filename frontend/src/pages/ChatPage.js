import React, { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import {
  Send, Zap, RotateCcw, Clock, Package, ShieldCheck,
  CheckCircle, Loader2, MapPin, Tag, Store, Globe,
  ChevronDown, AlertCircle, Sparkles
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ChatPage = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [searchMeta, setSearchMeta] = useState(null);
  const [progressStates, setProgressStates] = useState([]);
  const [parsedQuery, setParsedQuery] = useState(null);
  const [conversationState, setConversationState] = useState('collecting');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const resultsRef = useRef(null);

  // Auto-scroll to bottom of messages
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, progressStates, scrollToBottom]);

  // Scroll to results when they arrive
  useEffect(() => {
    if (results && resultsRef.current) {
      setTimeout(() => {
        resultsRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 300);
    }
  }, [results]);

  // Send initial greeting
  useEffect(() => {
    const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
    setSessionId(newSessionId);
    setMessages([{
      role: 'assistant',
      content: "Hey! I'm PriceHunter, your shopping assistant. Tell me what you're looking for and I'll find the best deals across online platforms and local stores. What do you need?"
    }]);
  }, []);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || isLoading) return;

    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setIsLoading(true);

    try {
      const response = await axios.post(`${API}/chat/message`, {
        session_id: sessionId,
        message: text,
      }, { timeout: 120000 });

      const data = response.data;

      // Add assistant message
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.assistant_message
      }]);

      setConversationState(data.conversation_state);

      if (data.search_triggered) {
        // Show progress states
        setProgressStates(data.progress_states || []);
        setParsedQuery(data.parsed_query);

        if (data.results && data.results.length > 0) {
          setResults(data.results);
          setSearchMeta(data.search_metadata);

          // Add summary message
          const online = data.search_metadata?.online_count || 0;
          const offline = data.search_metadata?.offline_count || 0;
          const time = data.search_metadata?.search_time || 0;
          setMessages(prev => [...prev, {
            role: 'assistant',
            content: `Found ${data.results.length} results in ${time}s — ${online} online and ${offline} from local vendors. Here are your best options:`,
            isSearchSummary: true
          }]);
        } else {
          setMessages(prev => [...prev, {
            role: 'assistant',
            content: "I couldn't find any results for that search. Could you try rephrasing or give me more details?"
          }]);
        }
      }
    } catch (err) {
      console.error('Chat error:', err);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "Sorry, something went wrong. Please try again.",
        isError: true
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const resetChat = async () => {
    try {
      await axios.post(`${API}/chat/reset`, { session_id: sessionId });
    } catch (e) { /* ignore */ }
    const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
    setSessionId(newSessionId);
    setMessages([{
      role: 'assistant',
      content: "Fresh start! What are you looking for today?"
    }]);
    setResults(null);
    setSearchMeta(null);
    setProgressStates([]);
    setParsedQuery(null);
    setConversationState('collecting');
    inputRef.current?.focus();
  };

  const quickReplies = [
    "cheapest iPhone 15 in Bangalore",
    "tomatoes near Rajkot",
    "laptop under 50000 in Mumbai",
    "nearest pharmacy in Delhi"
  ];

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: '#0A0F1C' }}>
      {/* Header */}
      <header className="sticky top-0 z-50 px-4 py-3 border-b" style={{
        backgroundColor: 'rgba(10, 15, 28, 0.95)',
        backdropFilter: 'blur(20px)',
        borderColor: 'rgba(255,255,255,0.06)'
      }}>
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{
              background: 'linear-gradient(135deg, #00FF88, #00CC66)',
              boxShadow: '0 0 16px rgba(0,255,136,0.25)'
            }}>
              <Zap className="w-4 h-4" style={{ color: '#0A0F1C' }} />
            </div>
            <h1 className="text-lg font-bold tracking-tight" style={{
              fontFamily: "'Outfit', sans-serif",
              color: '#FFFFFF'
            }} data-testid="app-title">PriceHunter</h1>
            <span className="text-xs px-2 py-0.5 rounded-full" style={{
              backgroundColor: 'rgba(0,255,136,0.12)',
              color: '#00FF88',
              fontFamily: "'JetBrains Mono', monospace"
            }}>AI</span>
          </div>
          <button
            onClick={resetChat}
            data-testid="reset-chat-btn"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200"
            style={{
              backgroundColor: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.08)',
              color: '#8BA3CB'
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(0,255,136,0.3)'; e.currentTarget.style.color = '#00FF88'; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'; e.currentTarget.style.color = '#8BA3CB'; }}
          >
            <RotateCcw className="w-3.5 h-3.5" />
            New Search
          </button>
        </div>
      </header>

      {/* Chat Messages Area */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-6 space-y-4">
          <AnimatePresence initial={false}>
            {messages.map((msg, i) => (
              <MessageBubble key={i} message={msg} index={i} />
            ))}
          </AnimatePresence>

          {/* Typing Indicator */}
          {isLoading && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-start gap-3"
            >
              <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0" style={{
                background: 'linear-gradient(135deg, #00FF88, #00CC66)'
              }}>
                <Zap className="w-3.5 h-3.5" style={{ color: '#0A0F1C' }} />
              </div>
              <div className="px-4 py-3 rounded-2xl rounded-tl-sm" style={{
                backgroundColor: 'rgba(19,27,47,0.8)',
                border: '1px solid rgba(255,255,255,0.06)'
              }}>
                <div className="flex items-center gap-1.5">
                  <motion.div animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, delay: 0 }}
                    className="w-2 h-2 rounded-full" style={{ backgroundColor: '#00FF88' }} />
                  <motion.div animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, delay: 0.2 }}
                    className="w-2 h-2 rounded-full" style={{ backgroundColor: '#00FF88' }} />
                  <motion.div animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.2, repeat: Infinity, delay: 0.4 }}
                    className="w-2 h-2 rounded-full" style={{ backgroundColor: '#00FF88' }} />
                </div>
              </div>
            </motion.div>
          )}

          {/* Quick Replies (only at start) */}
          {messages.length <= 1 && !isLoading && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="space-y-2 pt-2"
            >
              <p className="text-xs font-semibold uppercase tracking-wider pl-1" style={{
                color: '#8BA3CB',
                fontFamily: "'JetBrains Mono', monospace"
              }}>Try asking</p>
              <div className="flex flex-wrap gap-2">
                {quickReplies.map((qr, idx) => (
                  <button
                    key={idx}
                    data-testid={`quick-reply-${idx}`}
                    onClick={() => { setInput(qr); inputRef.current?.focus(); }}
                    className="px-3 py-2 text-sm rounded-xl border transition-all duration-200"
                    style={{
                      backgroundColor: 'rgba(255,255,255,0.02)',
                      borderColor: 'rgba(255,255,255,0.08)',
                      color: '#8BA3CB',
                      fontFamily: "'Inter', sans-serif"
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.backgroundColor = 'rgba(0,255,136,0.08)';
                      e.currentTarget.style.borderColor = 'rgba(0,255,136,0.25)';
                      e.currentTarget.style.color = '#00FF88';
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.02)';
                      e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)';
                      e.currentTarget.style.color = '#8BA3CB';
                    }}
                  >
                    {qr}
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          {/* Results Section */}
          {results && results.length > 0 && (
            <div ref={resultsRef}>
              <ResultsSection
                results={results}
                searchMeta={searchMeta}
                parsedQuery={parsedQuery}
              />
            </div>
          )}

          {/* Progress States */}
          {progressStates.length > 0 && (
            <ProgressTimeline states={progressStates} />
          )}

          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Input Area */}
      <div className="sticky bottom-0 z-50 px-4 py-3 border-t" style={{
        backgroundColor: 'rgba(10, 15, 28, 0.95)',
        backdropFilter: 'blur(20px)',
        borderColor: 'rgba(255,255,255,0.06)'
      }}>
        <div className="max-w-3xl mx-auto">
          <div className="flex items-center gap-3">
            <input
              ref={inputRef}
              type="text"
              data-testid="chat-input"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={conversationState === 'results_ready' ? "Ask about results or search for something else..." : "Type your message..."}
              disabled={isLoading}
              className="flex-1 px-4 py-3 rounded-xl text-sm transition-all duration-200 focus:outline-none"
              style={{
                backgroundColor: 'rgba(19,27,47,0.8)',
                border: '1px solid rgba(255,255,255,0.1)',
                color: '#FFFFFF',
                fontFamily: "'Inter', sans-serif",
              }}
              onFocus={e => { e.target.style.borderColor = 'rgba(0,255,136,0.4)'; }}
              onBlur={e => { e.target.style.borderColor = 'rgba(255,255,255,0.1)'; }}
            />
            <button
              onClick={sendMessage}
              data-testid="send-message-btn"
              disabled={isLoading || !input.trim()}
              className="p-3 rounded-xl transition-all duration-200 flex-shrink-0"
              style={{
                background: input.trim() && !isLoading
                  ? 'linear-gradient(135deg, #00FF88, #00CC66)'
                  : 'rgba(255,255,255,0.05)',
                color: input.trim() && !isLoading ? '#0A0F1C' : '#8BA3CB',
                cursor: input.trim() && !isLoading ? 'pointer' : 'default',
              }}
            >
              {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};


/* ========== Sub-components ========== */

const MessageBubble = ({ message, index }) => {
  const isUser = message.role === 'user';

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''}`}
      data-testid={`message-bubble-${index}`}
    >
      {/* Avatar */}
      {!isUser && (
        <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0" style={{
          background: 'linear-gradient(135deg, #00FF88, #00CC66)'
        }}>
          <Zap className="w-3.5 h-3.5" style={{ color: '#0A0F1C' }} />
        </div>
      )}

      {/* Bubble */}
      <div
        className={`max-w-[80%] px-4 py-3 text-sm leading-relaxed ${
          isUser ? 'rounded-2xl rounded-tr-sm' : 'rounded-2xl rounded-tl-sm'
        }`}
        style={{
          backgroundColor: isUser
            ? 'rgba(0,255,136,0.12)'
            : message.isError
              ? 'rgba(255,68,68,0.1)'
              : 'rgba(19,27,47,0.8)',
          border: `1px solid ${isUser
            ? 'rgba(0,255,136,0.2)'
            : message.isError
              ? 'rgba(255,68,68,0.2)'
              : 'rgba(255,255,255,0.06)'}`,
          color: '#FFFFFF',
          fontFamily: "'Inter', sans-serif"
        }}
      >
        {message.content}
      </div>
    </motion.div>
  );
};


const ResultsSection = ({ results, searchMeta, parsedQuery }) => {
  const [filterSource, setFilterSource] = useState('all');
  const [sortBy, setSortBy] = useState('rank');
  const [showAll, setShowAll] = useState(false);

  const filtered = results.filter(r => {
    if (filterSource === 'all') return true;
    return r.source_type.toLowerCase() === filterSource;
  }).sort((a, b) => {
    if (sortBy === 'price') return a.price - b.price;
    if (sortBy === 'delivery') return a.delivery_time.localeCompare(b.delivery_time);
    return a.rank - b.rank;
  });

  const displayed = showAll ? filtered : filtered.slice(0, 6);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="space-y-4 pt-2"
      data-testid="results-section"
    >
      {/* Query & Meta Bar */}
      {parsedQuery && (
        <div className="flex flex-wrap items-center gap-2 px-3 py-2.5 rounded-xl text-xs" style={{
          backgroundColor: 'rgba(19,27,47,0.6)',
          border: '1px solid rgba(255,255,255,0.06)'
        }}>
          <span className="px-2 py-1 rounded-md font-semibold" style={{
            backgroundColor: 'rgba(0,255,136,0.15)', color: '#00FF88'
          }}>
            <Tag className="w-3 h-3 inline mr-1" />{parsedQuery.product}
          </span>
          <span className="px-2 py-1 rounded-md" style={{
            backgroundColor: 'rgba(255,255,255,0.05)', color: '#8BA3CB'
          }}>
            <MapPin className="w-3 h-3 inline mr-1" />{parsedQuery.location}
          </span>
          <span className="px-2 py-1 rounded-md" style={{
            backgroundColor: 'rgba(0,229,255,0.1)', color: '#00E5FF'
          }}>
            {parsedQuery.intent}
          </span>
          {searchMeta && (
            <span className="ml-auto" style={{ color: '#8BA3CB', fontFamily: "'JetBrains Mono', monospace" }}>
              {searchMeta.total_results} results in {searchMeta.search_time}s
            </span>
          )}
        </div>
      )}

      {/* Filter & Sort */}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <div className="flex items-center gap-1.5">
          <span style={{ color: '#8BA3CB' }}>Show:</span>
          {['all', 'online', 'offline'].map(f => (
            <button
              key={f}
              onClick={() => setFilterSource(f)}
              data-testid={`filter-${f}`}
              className="px-2.5 py-1.5 rounded-lg transition-all duration-200 capitalize"
              style={{
                backgroundColor: filterSource === f ? 'rgba(0,255,136,0.15)' : 'rgba(255,255,255,0.03)',
                color: filterSource === f ? '#00FF88' : '#8BA3CB',
                border: `1px solid ${filterSource === f ? 'rgba(0,255,136,0.3)' : 'transparent'}`,
              }}
            >{f}</button>
          ))}
        </div>
        <div className="flex items-center gap-1.5 ml-auto">
          <span style={{ color: '#8BA3CB' }}>Sort:</span>
          {[{ v: 'rank', l: 'Best' }, { v: 'price', l: 'Price' }, { v: 'delivery', l: 'Speed' }].map(s => (
            <button
              key={s.v}
              onClick={() => setSortBy(s.v)}
              data-testid={`sort-${s.v}`}
              className="px-2.5 py-1.5 rounded-lg transition-all duration-200"
              style={{
                backgroundColor: sortBy === s.v ? 'rgba(0,255,136,0.15)' : 'rgba(255,255,255,0.03)',
                color: sortBy === s.v ? '#00FF88' : '#8BA3CB',
                border: `1px solid ${sortBy === s.v ? 'rgba(0,255,136,0.3)' : 'transparent'}`,
              }}
            >{s.l}</button>
          ))}
        </div>
      </div>

      {/* Results Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {displayed.map((r, i) => (
          <ResultCardInline key={r.id} result={r} index={i} />
        ))}
      </div>

      {/* Show More */}
      {filtered.length > 6 && !showAll && (
        <button
          onClick={() => setShowAll(true)}
          data-testid="show-more-results"
          className="w-full py-2.5 rounded-xl text-sm font-medium flex items-center justify-center gap-1.5 transition-all duration-200"
          style={{
            backgroundColor: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.08)',
            color: '#8BA3CB'
          }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(0,255,136,0.3)'; e.currentTarget.style.color = '#00FF88'; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'; e.currentTarget.style.color = '#8BA3CB'; }}
        >
          <ChevronDown className="w-4 h-4" />
          Show all {filtered.length} results
        </button>
      )}
    </motion.div>
  );
};


const ResultCardInline = ({ result, index }) => {
  const isOnline = result.source_type === 'ONLINE';
  const isBest = result.is_best_deal;
  const rank = result.rank;

  const rankColors = {
    1: { bg: 'linear-gradient(135deg, #FFD700, #FFA500)', text: '#000' },
    2: { bg: 'linear-gradient(135deg, #C0C0C0, #808080)', text: '#000' },
    3: { bg: 'linear-gradient(135deg, #CD7F32, #8B4513)', text: '#FFF' },
  };
  const rc = rankColors[rank] || { bg: 'rgba(255,255,255,0.05)', text: '#8BA3CB' };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      data-testid={`result-card-${index}`}
      className={`p-4 rounded-2xl transition-all duration-200 ${isBest ? 'md:col-span-2' : ''}`}
      style={{
        backgroundColor: isBest ? 'rgba(0,255,136,0.06)' : 'rgba(19,27,47,0.7)',
        border: `1.5px solid ${isBest ? 'rgba(0,255,136,0.4)' : 'rgba(255,255,255,0.05)'}`,
      }}
      whileHover={{ y: -3, borderColor: 'rgba(0,255,136,0.3)' }}
    >
      {/* Top row: rank + source + vendor */}
      <div className="flex items-center gap-2 mb-2.5">
        <span className="px-2.5 py-1 rounded-lg text-xs font-black" style={{
          background: rc.bg, color: rc.text, fontFamily: "'JetBrains Mono', monospace"
        }}>
          #{rank}
        </span>
        <span className="px-2 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider" style={{
          backgroundColor: isOnline ? 'rgba(0,229,255,0.12)' : 'rgba(0,255,136,0.12)',
          color: isOnline ? '#00E5FF' : '#00FF88',
        }}>
          {isOnline ? <Globe className="w-3 h-3 inline mr-0.5" /> : <Store className="w-3 h-3 inline mr-0.5" />}
          {result.source_type}
        </span>
        {result.negotiated && (
          <span className="px-2 py-1 rounded-md text-[10px] font-bold flex items-center gap-0.5" style={{
            backgroundColor: 'rgba(0,255,136,0.15)', color: '#00FF88'
          }}>
            <CheckCircle className="w-3 h-3" /> Negotiated
          </span>
        )}
        {isBest && (
          <span className="px-2 py-1 rounded-md text-[10px] font-black uppercase" style={{
            background: 'linear-gradient(135deg, #FFD700, #FFA500)', color: '#000'
          }}>
            BEST DEAL
          </span>
        )}
      </div>

      {/* Vendor name + price */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h4 className="text-sm font-semibold truncate" style={{
            color: '#FFFFFF', fontFamily: "'Outfit', sans-serif"
          }}>{result.vendor_name}</h4>
          <p className="text-xs mt-0.5" style={{ color: '#8BA3CB' }}>{result.product_name}</p>
        </div>
        <div className="text-right flex-shrink-0">
          <div className="text-xl font-black" style={{
            color: isBest ? '#00FF88' : '#FFFFFF',
            fontFamily: "'JetBrains Mono', monospace"
          }}>
            ₹{result.price.toLocaleString('en-IN')}
          </div>
        </div>
      </div>

      {/* Details row */}
      <div className="flex flex-wrap items-center gap-3 mt-3 text-xs" style={{ color: '#8BA3CB' }}>
        <span className="flex items-center gap-1">
          <Clock className="w-3 h-3" /> {result.delivery_time}
        </span>
        <span className="flex items-center gap-1">
          <Package className="w-3 h-3" /> {result.availability}
        </span>
        <span className="flex items-center gap-1 ml-auto">
          <ShieldCheck className="w-3 h-3" />
          <span style={{ color: '#00FF88', fontFamily: "'JetBrains Mono', monospace" }}>
            {Math.round(result.confidence * 100)}%
          </span>
        </span>
      </div>

      {/* Confidence bar */}
      <div className="mt-2 w-full h-1 rounded-full overflow-hidden" style={{ backgroundColor: 'rgba(255,255,255,0.06)' }}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${result.confidence * 100}%` }}
          transition={{ duration: 0.8, delay: index * 0.05 }}
          className="h-full rounded-full"
          style={{
            background: result.confidence > 0.85
              ? 'linear-gradient(90deg, #00FF88, #00CC66)'
              : 'linear-gradient(90deg, #FFD700, #00FF88)'
          }}
        />
      </div>

      {/* Notes */}
      {result.notes && (
        <p className="text-[11px] mt-2 italic" style={{ color: 'rgba(139,163,203,0.7)' }}>
          {result.notes}
        </p>
      )}
    </motion.div>
  );
};


const ProgressTimeline = ({ states }) => {
  const statusIcon = (status) => {
    if (status === 'completed') return <CheckCircle className="w-4 h-4" style={{ color: '#00FF88' }} />;
    if (status === 'active') return <Loader2 className="w-4 h-4 animate-spin" style={{ color: '#00E5FF' }} />;
    if (status === 'failed') return <AlertCircle className="w-4 h-4" style={{ color: '#FF4444' }} />;
    return <div className="w-4 h-4 rounded-full" style={{ border: '2px solid rgba(139,163,203,0.3)' }} />;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.3 }}
      className="rounded-2xl p-4 space-y-1"
      style={{
        backgroundColor: 'rgba(19,27,47,0.5)',
        border: '1px solid rgba(255,255,255,0.06)'
      }}
      data-testid="progress-timeline"
    >
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="w-4 h-4" style={{ color: '#00FF88' }} />
        <span className="text-xs font-bold uppercase tracking-wider" style={{
          color: '#8BA3CB', fontFamily: "'JetBrains Mono', monospace"
        }}>Search Progress</span>
      </div>
      {states.map((s, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.08 }}
          className="flex items-center gap-3 py-2"
          data-testid={`progress-state-${i}`}
        >
          <div className="flex-shrink-0">{statusIcon(s.status)}</div>
          <div className="flex-1 min-w-0">
            <span className="text-sm font-medium" style={{
              color: s.status === 'completed' ? '#FFFFFF'
                : s.status === 'active' ? '#00E5FF'
                : s.status === 'failed' ? '#FF4444'
                : '#8BA3CB',
              fontFamily: "'Inter', sans-serif"
            }}>{s.stage}</span>
            {s.detail && (
              <span className="block text-xs mt-0.5" style={{ color: 'rgba(139,163,203,0.7)' }}>
                {s.detail}
              </span>
            )}
          </div>
          {s.status === 'completed' && (
            <span className="text-[10px] font-bold" style={{ color: 'rgba(0,255,136,0.6)' }}>DONE</span>
          )}
        </motion.div>
      ))}
    </motion.div>
  );
};


export default ChatPage;
