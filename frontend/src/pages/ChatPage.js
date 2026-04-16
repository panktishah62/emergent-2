import React, { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import {
  Send, Zap, RotateCcw, Clock, Package, ShieldCheck,
  CheckCircle, Loader2, MapPin, Tag, Store, Globe,
  ChevronDown, AlertCircle, Sparkles, Phone, X, Crown
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const RAZORPAY_KEY = process.env.REACT_APP_RAZORPAY_KEY_ID;

const ChatPage = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [conversationState, setConversationState] = useState('collecting');

  // Staged display state
  const [discoveredVendors, setDiscoveredVendors] = useState(null);
  const [progressStates, setProgressStates] = useState([]);
  const [animatingProgress, setAnimatingProgress] = useState(false);
  const [currentProgressIdx, setCurrentProgressIdx] = useState(-1);
  const [results, setResults] = useState(null);
  const [searchMeta, setSearchMeta] = useState(null);
  const [parsedQuery, setParsedQuery] = useState(null);
  const [showResults, setShowResults] = useState(false);
  const [waitingForResults, setWaitingForResults] = useState(false);

  // Paywall state
  const [showPaywall, setShowPaywall] = useState(false);
  const [isPremium, setIsPremium] = useState(false);
  const [hasShownPaywall, setHasShownPaywall] = useState(false);
  const [paymentProcessing, setPaymentProcessing] = useState(false);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll
  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentProgressIdx, showResults, scrollToBottom]);

  // Initial greeting
  useEffect(() => {
    const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
    setSessionId(newSessionId);
    setMessages([{
      role: 'assistant',
      content: "Hey! I'm PriceHunter, your shopping assistant. Tell me what you're looking for and I'll find the best deals across online platforms and local stores. What do you need?"
    }]);
  }, []);

  // Animate progress states one by one
  useEffect(() => {
    if (!animatingProgress || progressStates.length === 0) return;

    let idx = 0;
    setCurrentProgressIdx(0);

    const interval = setInterval(() => {
      idx++;
      if (idx >= progressStates.length) {
        clearInterval(interval);
        // All progress done — show waiting state, then reveal results after 1 minute
        setWaitingForResults(true);
        setTimeout(() => {
          setWaitingForResults(false);
          setShowResults(true);
          setAnimatingProgress(false);
        }, 60000);
      } else {
        setCurrentProgressIdx(idx);
      }
    }, 800); // 800ms per step

    return () => clearInterval(interval);
  }, [animatingProgress, progressStates.length]);

  // Trigger paywall after every successful results display
  useEffect(() => {
    if (showResults && results && results.length > 0 && !isPremium) {
      const timer = setTimeout(() => {
        setShowPaywall(true);
      }, 2000); // 2s after results appear
      return () => clearTimeout(timer);
    }
  }, [showResults, results, isPremium]);

  // Razorpay payment handler
  const handlePayment = async () => {
    setPaymentProcessing(true);
    try {
      // Create order on backend
      const { data } = await axios.post(`${API}/payments/create-order`, {
        session_id: sessionId,
      });

      const options = {
        key: data.key_id || RAZORPAY_KEY,
        amount: data.amount,
        currency: data.currency,
        name: 'PriceHunter',
        description: 'Premium Upgrade — Unlimited Price Hunting',
        order_id: data.order_id,
        method: {
          upi: true,
          card: false,
          netbanking: false,
          wallet: false,
          paylater: false,
          emi: false,
        },
        handler: async (response) => {
          // Verify payment on backend
          try {
            await axios.post(`${API}/payments/verify`, {
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
              session_id: sessionId,
            });
            setIsPremium(true);
            setShowPaywall(false);
            setMessages(prev => [...prev, {
              role: 'assistant',
              content: "Premium unlocked! I'll keep helping you find the best prices across all products and services.",
              isPremium: true,
            }]);
          } catch (err) {
            console.error('Verification failed:', err);
            setMessages(prev => [...prev, {
              role: 'assistant',
              content: "Payment received but verification had an issue. Please contact support if needed.",
              isError: true,
            }]);
          }
          setPaymentProcessing(false);
        },
        modal: {
          ondismiss: () => {
            setPaymentProcessing(false);
          },
        },
        theme: {
          color: '#00FF88',
        },
      };

      const rzp = new window.Razorpay(options);
      rzp.on('payment.failed', () => {
        setPaymentProcessing(false);
      });
      rzp.open();
    } catch (err) {
      console.error('Order creation failed:', err);
      setPaymentProcessing(false);
    }
  };

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
        // Reset previous results
        setShowResults(false);
        setCurrentProgressIdx(-1);

        // Stage 1: Show discovered vendors as chat message
        if (data.discovered_vendors && data.discovered_vendors.length > 0) {
          setDiscoveredVendors(data.discovered_vendors);
          setMessages(prev => [...prev, {
            role: 'vendor_list',
            vendors: data.discovered_vendors,
          }]);
        }

        // Store data for later stages
        setParsedQuery(data.parsed_query);
        setSearchMeta(data.search_metadata);

        if (data.results && data.results.length > 0) {
          setResults(data.results);
        }

        // Stage 2: Start progress animation after a short delay
        if (data.progress_states && data.progress_states.length > 0) {
          setProgressStates(data.progress_states);
          setTimeout(() => {
            setAnimatingProgress(true);
          }, 800);
        } else {
          // No progress states — show results immediately
          setShowResults(true);
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
    setDiscoveredVendors(null);
    setShowResults(false);
    setWaitingForResults(false);
    setAnimatingProgress(false);
    setCurrentProgressIdx(-1);
    setConversationState('collecting');
    inputRef.current?.focus();
  };

  const quickReplies = [
    "fastest delivery for AirPods Pro in Mumbai",
    "cheapest tomatoes 1kg near Rajkot",
    "cheapest iPhone 15 128GB in Bangalore",
    "cheapest modular kitchen hardware in Surat"
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
              fontFamily: "'Outfit', sans-serif", color: '#FFFFFF'
            }} data-testid="app-title">PriceHunter</h1>
            <span className="text-xs px-2 py-0.5 rounded-full" style={{
              backgroundColor: 'rgba(0,255,136,0.12)', color: '#00FF88',
              fontFamily: "'JetBrains Mono', monospace"
            }}>AI</span>
          </div>
          <button onClick={resetChat} data-testid="reset-chat-btn"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200"
            style={{ backgroundColor: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: '#8BA3CB' }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(0,255,136,0.3)'; e.currentTarget.style.color = '#00FF88'; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'; e.currentTarget.style.color = '#8BA3CB'; }}
          >
            <RotateCcw className="w-3.5 h-3.5" /> New Search
          </button>
        </div>
      </header>

      {/* Chat Messages Area */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-6 space-y-4">
          <AnimatePresence initial={false}>
            {messages.map((msg, i) => {
              if (msg.role === 'vendor_list') {
                return <VendorListBubble key={`vl-${i}`} vendors={msg.vendors} />;
              }
              return <MessageBubble key={i} message={msg} index={i} />;
            })}
          </AnimatePresence>

          {/* Typing Indicator */}
          {isLoading && <TypingIndicator />}

          {/* Quick Replies (only at start) */}
          {messages.length <= 1 && !isLoading && (
            <QuickReplies replies={quickReplies} onSelect={(qr) => { setInput(qr); inputRef.current?.focus(); }} />
          )}

          {/* Stage 2: Progress Animation */}
          {progressStates.length > 0 && !showResults && (
            <ProgressAnimation
              states={progressStates}
              currentIdx={currentProgressIdx}
            />
          )}

          {/* Waiting state — after progress finishes, before results appear */}
          {waitingForResults && !showResults && (
            <WaitingForResults />
          )}

          {/* Stage 3: Results (only after progress completes) */}
          {showResults && results && results.length > 0 && (
            <>
              <SummaryMessage
                results={results}
                searchMeta={searchMeta}
              />
              <ResultsSection
                results={results}
                searchMeta={searchMeta}
                parsedQuery={parsedQuery}
              />
              {/* Final progress summary */}
              <ProgressTimeline states={progressStates} />
            </>
          )}

          {showResults && (!results || results.length === 0) && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="flex items-start gap-3">
              <AssistantAvatar />
              <div className="px-4 py-3 rounded-2xl rounded-tl-sm text-sm" style={{
                backgroundColor: 'rgba(19,27,47,0.8)', border: '1px solid rgba(255,255,255,0.06)', color: '#FFFFFF'
              }}>
                I couldn't find any results for that search. Could you try rephrasing or give me more details?
              </div>
            </motion.div>
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
        <div className="max-w-3xl mx-auto flex items-center gap-3">
          <input ref={inputRef} type="text" data-testid="chat-input"
            value={input} onChange={e => setInput(e.target.value)} onKeyDown={handleKeyDown}
            placeholder={conversationState === 'results_ready' ? "Search for something else..." : "Type your message..."}
            disabled={isLoading || animatingProgress}
            className="flex-1 px-4 py-3 rounded-xl text-sm transition-all duration-200 focus:outline-none"
            style={{ backgroundColor: 'rgba(19,27,47,0.8)', border: '1px solid rgba(255,255,255,0.1)', color: '#FFFFFF', fontFamily: "'Inter', sans-serif" }}
            onFocus={e => { e.target.style.borderColor = 'rgba(0,255,136,0.4)'; }}
            onBlur={e => { e.target.style.borderColor = 'rgba(255,255,255,0.1)'; }}
          />
          <button onClick={sendMessage} data-testid="send-message-btn"
            disabled={isLoading || !input.trim() || animatingProgress}
            className="p-3 rounded-xl transition-all duration-200 flex-shrink-0"
            style={{
              background: input.trim() && !isLoading && !animatingProgress ? 'linear-gradient(135deg, #00FF88, #00CC66)' : 'rgba(255,255,255,0.05)',
              color: input.trim() && !isLoading && !animatingProgress ? '#0A0F1C' : '#8BA3CB',
            }}
          >
            {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Paywall Modal */}
      <AnimatePresence>
        {showPaywall && (
          <PaywallModal
            onPay={handlePayment}
            onClose={() => setShowPaywall(false)}
            processing={paymentProcessing}
          />
        )}
      </AnimatePresence>
    </div>
  );
};


/* ===== Shared avatar ===== */
const AssistantAvatar = () => (
  <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
    style={{ background: 'linear-gradient(135deg, #00FF88, #00CC66)' }}>
    <Zap className="w-3.5 h-3.5" style={{ color: '#0A0F1C' }} />
  </div>
);


/* ===== Message Bubble ===== */
const MessageBubble = ({ message, index }) => {
  const isUser = message.role === 'user';
  const isPremiumMsg = message.isPremium;
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''}`}
      data-testid={`message-bubble-${index}`}
    >
      {!isUser && <AssistantAvatar />}
      <div className={`max-w-[80%] px-4 py-3 text-sm leading-relaxed ${isUser ? 'rounded-2xl rounded-tr-sm' : 'rounded-2xl rounded-tl-sm'}`}
        style={{
          backgroundColor: isPremiumMsg ? 'rgba(255,215,0,0.08)' : isUser ? 'rgba(0,255,136,0.12)' : message.isError ? 'rgba(255,68,68,0.1)' : 'rgba(19,27,47,0.8)',
          border: `1px solid ${isPremiumMsg ? 'rgba(255,215,0,0.25)' : isUser ? 'rgba(0,255,136,0.2)' : message.isError ? 'rgba(255,68,68,0.2)' : 'rgba(255,255,255,0.06)'}`,
          color: '#FFFFFF', fontFamily: "'Inter', sans-serif"
        }}
      >
        {isPremiumMsg && <Crown className="w-4 h-4 inline mr-1.5" style={{ color: '#FFD700' }} />}
        {message.content}
      </div>
    </motion.div>
  );
};


/* ===== Vendor List Chat Bubble ===== */
const VendorListBubble = ({ vendors }) => (
  <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.4 }}
    className="flex items-start gap-3"
    data-testid="vendor-list-bubble"
  >
    <AssistantAvatar />
    <div className="max-w-[85%] rounded-2xl rounded-tl-sm overflow-hidden" style={{
      backgroundColor: 'rgba(19,27,47,0.8)', border: '1px solid rgba(255,255,255,0.06)'
    }}>
      <div className="px-4 pt-3 pb-2">
        <p className="text-sm font-medium mb-2" style={{ color: '#FFFFFF', fontFamily: "'Inter', sans-serif" }}>
          Found {vendors.length} local shops nearby. Let me contact them for live prices:
        </p>
      </div>
      <div className="px-3 pb-3 space-y-1">
        {vendors.map((v, i) => (
          <motion.div key={i}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.08 }}
            className="flex items-center gap-2.5 px-3 py-2 rounded-lg"
            style={{ backgroundColor: 'rgba(255,255,255,0.03)' }}
            data-testid={`vendor-item-${i}`}
          >
            <Store className="w-3.5 h-3.5 flex-shrink-0" style={{ color: '#00FF88' }} />
            <span className="text-sm flex-1 truncate" style={{ color: '#FFFFFF', fontFamily: "'Inter', sans-serif" }}>
              {v.name}
            </span>
            <div className="flex items-center gap-1 flex-shrink-0">
              <Phone className="w-3 h-3" style={{ color: '#8BA3CB' }} />
              <span className="text-xs" style={{ color: '#8BA3CB', fontFamily: "'JetBrains Mono', monospace" }}>
                {v.phone}
              </span>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  </motion.div>
);


/* ===== Typing Indicator ===== */
const TypingIndicator = () => (
  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex items-start gap-3">
    <AssistantAvatar />
    <div className="px-4 py-3 rounded-2xl rounded-tl-sm" style={{
      backgroundColor: 'rgba(19,27,47,0.8)', border: '1px solid rgba(255,255,255,0.06)'
    }}>
      <div className="flex items-center gap-1.5">
        {[0, 0.2, 0.4].map((d, i) => (
          <motion.div key={i} animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 1.2, repeat: Infinity, delay: d }}
            className="w-2 h-2 rounded-full" style={{ backgroundColor: '#00FF88' }} />
        ))}
      </div>
    </div>
  </motion.div>
);


/* ===== Quick Replies ===== */
const QuickReplies = ({ replies, onSelect }) => (
  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
    className="space-y-2 pt-2"
  >
    <p className="text-xs font-semibold uppercase tracking-wider pl-1" style={{
      color: '#8BA3CB', fontFamily: "'JetBrains Mono', monospace"
    }}>Try asking</p>
    <div className="flex flex-wrap gap-2">
      {replies.map((qr, idx) => (
        <button key={idx} data-testid={`quick-reply-${idx}`}
          onClick={() => onSelect(qr)}
          className="px-3 py-2 text-sm rounded-xl border transition-all duration-200"
          style={{ backgroundColor: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.08)', color: '#8BA3CB', fontFamily: "'Inter', sans-serif" }}
          onMouseEnter={e => { e.currentTarget.style.backgroundColor = 'rgba(0,255,136,0.08)'; e.currentTarget.style.borderColor = 'rgba(0,255,136,0.25)'; e.currentTarget.style.color = '#00FF88'; }}
          onMouseLeave={e => { e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.02)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'; e.currentTarget.style.color = '#8BA3CB'; }}
        >{qr}</button>
      ))}
    </div>
  </motion.div>
);


/* ===== Progress Animation (live calling states) ===== */
const ProgressAnimation = ({ states, currentIdx }) => {
  if (currentIdx < 0) return null;

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
      className="flex items-start gap-3"
      data-testid="progress-animation"
    >
      <AssistantAvatar />
      <div className="max-w-[85%] rounded-2xl rounded-tl-sm p-4 space-y-1.5" style={{
        backgroundColor: 'rgba(19,27,47,0.8)', border: '1px solid rgba(255,255,255,0.06)'
      }}>
        <div className="flex items-center gap-2 mb-2.5">
          <Loader2 className="w-4 h-4 animate-spin" style={{ color: '#00E5FF' }} />
          <span className="text-xs font-bold uppercase tracking-wider" style={{
            color: '#00E5FF', fontFamily: "'JetBrains Mono', monospace"
          }}>Contacting dealers for live prices...</span>
        </div>
        {states.map((s, i) => {
          const isComplete = i < currentIdx;
          const isActive = i === currentIdx;
          const isPending = i > currentIdx;

          return (
            <motion.div key={i}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: isPending ? 0.3 : 1, x: 0 }}
              transition={{ delay: 0.05 }}
              className="flex items-center gap-2.5 py-1.5"
              data-testid={`progress-step-${i}`}
            >
              {isComplete && <CheckCircle className="w-4 h-4 flex-shrink-0" style={{ color: '#00FF88' }} />}
              {isActive && <Loader2 className="w-4 h-4 flex-shrink-0 animate-spin" style={{ color: '#00E5FF' }} />}
              {isPending && <div className="w-4 h-4 rounded-full flex-shrink-0" style={{ border: '2px solid rgba(139,163,203,0.2)' }} />}
              <span className="text-sm" style={{
                color: isComplete ? '#FFFFFF' : isActive ? '#00E5FF' : '#8BA3CB',
                fontFamily: "'Inter', sans-serif"
              }}>{s.stage}</span>
              {s.detail && isComplete && (
                <span className="text-[10px] ml-auto flex-shrink-0" style={{
                  color: 'rgba(0,255,136,0.6)', fontFamily: "'JetBrains Mono', monospace"
                }}>DONE</span>
              )}
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
};


/* ===== Waiting For Results (1-min delay indicator) ===== */
const WaitingForResults = () => (
  <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
    className="flex items-start gap-3" data-testid="waiting-for-results"
  >
    <AssistantAvatar />
    <div className="px-4 py-4 rounded-2xl rounded-tl-sm" style={{
      backgroundColor: 'rgba(19,27,47,0.8)', border: '1px solid rgba(0,229,255,0.15)'
    }}>
      <div className="flex items-center gap-2.5 mb-2">
        <Loader2 className="w-4 h-4 animate-spin" style={{ color: '#00E5FF' }} />
        <span className="text-sm font-medium" style={{ color: '#00E5FF', fontFamily: "'Inter', sans-serif" }}>
          Compiling results...
        </span>
      </div>
      <p className="text-xs" style={{ color: '#8BA3CB', fontFamily: "'Inter', sans-serif" }}>
        Analyzing prices and ranking the best deals for you. This may take a moment.
      </p>
      {/* Pulsing bar */}
      <div className="mt-3 w-full h-1 rounded-full overflow-hidden" style={{ backgroundColor: 'rgba(255,255,255,0.06)' }}>
        <motion.div
          animate={{ x: ['-100%', '100%'] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          className="h-full w-1/3 rounded-full"
          style={{ background: 'linear-gradient(90deg, transparent, #00E5FF, transparent)' }}
        />
      </div>
    </div>
  </motion.div>
);


/* ===== Summary Message (after progress) ===== */
const SummaryMessage = ({ results, searchMeta }) => {
  const online = searchMeta?.online_count || 0;
  const offline = searchMeta?.offline_count || 0;
  const time = searchMeta?.search_time || 0;
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
      className="flex items-start gap-3" data-testid="summary-message"
    >
      <AssistantAvatar />
      <div className="px-4 py-3 rounded-2xl rounded-tl-sm text-sm" style={{
        backgroundColor: 'rgba(0,255,136,0.06)', border: '1px solid rgba(0,255,136,0.15)', color: '#FFFFFF', fontFamily: "'Inter', sans-serif"
      }}>
        <Sparkles className="w-4 h-4 inline mr-1.5" style={{ color: '#00FF88' }} />
        Found <strong style={{ color: '#00FF88' }}>{results.length} results</strong> in {time}s — {online} from online platforms and {offline} from local vendors. Here are your best deals:
      </div>
    </motion.div>
  );
};


/* ===== Results Section ===== */
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
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }} className="space-y-4 pt-1" data-testid="results-section"
    >
      {/* Query & Meta Bar */}
      {parsedQuery && (
        <div className="flex flex-wrap items-center gap-2 px-3 py-2.5 rounded-xl text-xs" style={{
          backgroundColor: 'rgba(19,27,47,0.6)', border: '1px solid rgba(255,255,255,0.06)'
        }}>
          <span className="px-2 py-1 rounded-md font-semibold" style={{ backgroundColor: 'rgba(0,255,136,0.15)', color: '#00FF88' }}>
            <Tag className="w-3 h-3 inline mr-1" />{parsedQuery.product}
          </span>
          <span className="px-2 py-1 rounded-md" style={{ backgroundColor: 'rgba(255,255,255,0.05)', color: '#8BA3CB' }}>
            <MapPin className="w-3 h-3 inline mr-1" />{parsedQuery.location}
          </span>
          <span className="px-2 py-1 rounded-md" style={{ backgroundColor: 'rgba(0,229,255,0.1)', color: '#00E5FF' }}>
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
            <button key={f} onClick={() => setFilterSource(f)} data-testid={`filter-${f}`}
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
            <button key={s.v} onClick={() => setSortBy(s.v)} data-testid={`sort-${s.v}`}
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

      {/* Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {displayed.map((r, i) => (
          <ResultCard key={r.id} result={r} index={i} />
        ))}
      </div>

      {filtered.length > 6 && !showAll && (
        <button onClick={() => setShowAll(true)} data-testid="show-more-results"
          className="w-full py-2.5 rounded-xl text-sm font-medium flex items-center justify-center gap-1.5 transition-all duration-200"
          style={{ backgroundColor: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', color: '#8BA3CB' }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(0,255,136,0.3)'; e.currentTarget.style.color = '#00FF88'; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'; e.currentTarget.style.color = '#8BA3CB'; }}
        >
          <ChevronDown className="w-4 h-4" /> Show all {filtered.length} results
        </button>
      )}
    </motion.div>
  );
};


/* ===== Result Card ===== */
const ResultCard = ({ result, index }) => {
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
      {/* Top row */}
      <div className="flex items-center gap-2 mb-2.5">
        <span className="px-2.5 py-1 rounded-lg text-xs font-black" style={{
          background: rc.bg, color: rc.text, fontFamily: "'JetBrains Mono', monospace"
        }}>#{rank}</span>
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
          }}><CheckCircle className="w-3 h-3" /> Negotiated</span>
        )}
        {isBest && (
          <span className="px-2 py-1 rounded-md text-[10px] font-black uppercase" style={{
            background: 'linear-gradient(135deg, #FFD700, #FFA500)', color: '#000'
          }}>BEST DEAL</span>
        )}
      </div>

      {/* Vendor + Price */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h4 className="text-sm font-semibold truncate" style={{ color: '#FFFFFF', fontFamily: "'Outfit', sans-serif" }}>
            {result.vendor_name}
          </h4>
          <p className="text-xs mt-0.5" style={{ color: '#8BA3CB' }}>{result.product_name}</p>
        </div>
        <div className="text-right flex-shrink-0">
          <div className="text-xl font-black" style={{
            color: isBest ? '#00FF88' : '#FFFFFF', fontFamily: "'JetBrains Mono', monospace"
          }}>
            ₹{result.price.toLocaleString('en-IN')}
          </div>
        </div>
      </div>

      {/* Details */}
      <div className="flex flex-wrap items-center gap-3 mt-3 text-xs" style={{ color: '#8BA3CB' }}>
        <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {result.delivery_time}</span>
        <span className="flex items-center gap-1"><Package className="w-3 h-3" /> {result.availability}</span>
        <span className="flex items-center gap-1 ml-auto">
          <ShieldCheck className="w-3 h-3" />
          <span style={{ color: '#00FF88', fontFamily: "'JetBrains Mono', monospace" }}>{Math.round(result.confidence * 100)}%</span>
        </span>
      </div>

      {/* Confidence bar */}
      <div className="mt-2 w-full h-1 rounded-full overflow-hidden" style={{ backgroundColor: 'rgba(255,255,255,0.06)' }}>
        <motion.div initial={{ width: 0 }} animate={{ width: `${result.confidence * 100}%` }}
          transition={{ duration: 0.8, delay: index * 0.05 }}
          className="h-full rounded-full"
          style={{ background: result.confidence > 0.85 ? 'linear-gradient(90deg, #00FF88, #00CC66)' : 'linear-gradient(90deg, #FFD700, #00FF88)' }}
        />
      </div>
    </motion.div>
  );
};


/* ===== Final Progress Timeline (shown after results) ===== */
const ProgressTimeline = ({ states }) => {
  const statusIcon = (status) => {
    if (status === 'completed') return <CheckCircle className="w-3.5 h-3.5" style={{ color: '#00FF88' }} />;
    if (status === 'failed') return <AlertCircle className="w-3.5 h-3.5" style={{ color: '#FF4444' }} />;
    return <div className="w-3.5 h-3.5 rounded-full" style={{ border: '2px solid rgba(139,163,203,0.3)' }} />;
  };

  return (
    <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.2 }}
      className="rounded-2xl p-4" style={{ backgroundColor: 'rgba(19,27,47,0.4)', border: '1px solid rgba(255,255,255,0.04)' }}
      data-testid="progress-timeline"
    >
      <div className="flex items-center gap-2 mb-2.5">
        <Sparkles className="w-3.5 h-3.5" style={{ color: '#8BA3CB' }} />
        <span className="text-[10px] font-bold uppercase tracking-wider" style={{
          color: '#8BA3CB', fontFamily: "'JetBrains Mono', monospace"
        }}>Search Summary</span>
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {states.map((s, i) => (
          <div key={i} className="flex items-center gap-1.5 py-0.5" data-testid={`progress-state-${i}`}>
            {statusIcon(s.status)}
            <span className="text-xs" style={{
              color: s.status === 'completed' ? 'rgba(255,255,255,0.7)' : s.status === 'failed' ? '#FF4444' : '#8BA3CB',
            }}>{s.stage}</span>
          </div>
        ))}
      </div>
    </motion.div>
  );
};


/* ===== Paywall Modal ===== */
const PaywallModal = ({ onPay, onClose, processing }) => (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    exit={{ opacity: 0 }}
    className="fixed inset-0 z-[100] flex items-center justify-center px-4"
    style={{ backgroundColor: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)' }}
    data-testid="paywall-modal"
  >
    <motion.div
      initial={{ scale: 0.9, opacity: 0, y: 20 }}
      animate={{ scale: 1, opacity: 1, y: 0 }}
      exit={{ scale: 0.9, opacity: 0, y: 20 }}
      transition={{ type: 'spring', damping: 25, stiffness: 300 }}
      className="relative w-full max-w-md rounded-3xl overflow-hidden"
      style={{
        background: 'linear-gradient(180deg, rgba(19,27,47,0.98) 0%, rgba(10,15,28,0.99) 100%)',
        border: '1.5px solid rgba(255,215,0,0.2)',
        boxShadow: '0 24px 80px rgba(0,0,0,0.6), 0 0 60px rgba(255,215,0,0.08)',
      }}
    >
      {/* Close button */}
      <button
        onClick={onClose}
        data-testid="paywall-close-btn"
        className="absolute top-4 right-4 p-1.5 rounded-full transition-all duration-200 z-10"
        style={{ backgroundColor: 'rgba(255,255,255,0.06)', color: '#8BA3CB' }}
        onMouseEnter={e => { e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.12)'; e.currentTarget.style.color = '#FFF'; }}
        onMouseLeave={e => { e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.06)'; e.currentTarget.style.color = '#8BA3CB'; }}
      >
        <X className="w-5 h-5" />
      </button>

      {/* Top accent line */}
      <div className="h-1 w-full" style={{ background: 'linear-gradient(90deg, #FFD700, #00FF88, #FFD700)' }} />

      <div className="px-8 pt-8 pb-6 text-center space-y-5">
        {/* Crown icon */}
        <div className="flex justify-center">
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center" style={{
            background: 'linear-gradient(135deg, rgba(255,215,0,0.15), rgba(255,165,0,0.1))',
            border: '1.5px solid rgba(255,215,0,0.25)',
          }}>
            <Crown className="w-8 h-8" style={{ color: '#FFD700' }} />
          </div>
        </div>

        {/* Headline */}
        <h2 className="text-2xl font-bold" style={{
          fontFamily: "'Outfit', sans-serif",
          color: '#FFFFFF',
        }}>
          Congratulations!
        </h2>

        {/* Copy */}
        <div className="space-y-3">
          <p className="text-base leading-relaxed" style={{
            color: '#FFFFFF', fontFamily: "'Inter', sans-serif"
          }}>
            You saved a lot of money.
          </p>
          <p className="text-base leading-relaxed" style={{
            color: 'rgba(255,255,255,0.85)', fontFamily: "'Inter', sans-serif"
          }}>
            I can help you get the <span style={{ color: '#00FF88', fontWeight: 600 }}>best price across all products and services</span> at just
          </p>
          <div className="py-2">
            <span className="text-4xl font-black" style={{
              fontFamily: "'JetBrains Mono', monospace",
              background: 'linear-gradient(135deg, #FFD700, #FFA500)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}>
              ₹99
            </span>
          </div>
          <p className="text-sm" style={{
            color: '#8BA3CB', fontFamily: "'Inter', sans-serif"
          }}>
            And I promise to save you <strong style={{ color: '#00FF88' }}>1000s of rupees</strong>.
          </p>
        </div>

        {/* CTA Button */}
        <button
          onClick={onPay}
          disabled={processing}
          data-testid="paywall-pay-btn"
          className="w-full py-4 rounded-2xl text-lg font-bold transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98]"
          style={{
            background: processing
              ? 'rgba(255,255,255,0.1)'
              : 'linear-gradient(135deg, #FFD700 0%, #FFA500 50%, #FF8C00 100%)',
            color: processing ? '#8BA3CB' : '#000',
            fontFamily: "'Inter', sans-serif",
            boxShadow: processing ? 'none' : '0 8px 32px rgba(255,165,0,0.35)',
            cursor: processing ? 'wait' : 'pointer',
          }}
        >
          {processing ? (
            <span className="flex items-center justify-center gap-2">
              <Loader2 className="w-5 h-5 animate-spin" /> Processing...
            </span>
          ) : (
            'Upgrade to Premium — ₹99'
          )}
        </button>

        {/* Trust line */}
        <p className="text-[11px]" style={{ color: 'rgba(139,163,203,0.6)', fontFamily: "'Inter', sans-serif" }}>
          Secure UPI payment via Razorpay.
        </p>
      </div>
    </motion.div>
  </motion.div>
);


export default ChatPage;
