import React from 'react';
import { motion } from 'framer-motion';
import { Clock, Package, ShieldCheck, CheckCircle } from 'lucide-react';

const ResultCard = ({ result, index }) => {
  const isBestDeal = result.is_best_deal;
  const isOnline = result.source_type === 'ONLINE';
  const rank = result.rank;
  
  // Rank badge colors
  const getRankBadge = () => {
    if (rank === 1) {
      return {
        bg: 'linear-gradient(135deg, #FFD700 0%, #FFA500 100%)',
        text: '#000',
        label: '🥇 #1'
      };
    } else if (rank === 2) {
      return {
        bg: 'linear-gradient(135deg, #C0C0C0 0%, #808080 100%)',
        text: '#000',
        label: '🥈 #2'
      };
    } else if (rank === 3) {
      return {
        bg: 'linear-gradient(135deg, #CD7F32 0%, #8B4513 100%)',
        text: '#FFF',
        label: '🥉 #3'
      };
    }
    return {
      bg: 'rgba(255, 255, 255, 0.05)',
      text: '#8BA3CB',
      label: `#${rank}`
    };
  };

  const rankBadge = getRankBadge();

  const cardVariants = {
    hidden: { opacity: 0, y: 20, scale: 0.95 },
    visible: { 
      opacity: 1, 
      y: 0, 
      scale: 1,
      transition: { duration: 0.4, ease: 'easeOut' }
    }
  };

  return (
    <motion.div
      variants={cardVariants}
      data-testid={`result-card-${index}`}
      className={`relative p-6 md:p-8 rounded-3xl transition-all duration-300 cursor-pointer ${
        isBestDeal ? 'md:col-span-2' : ''
      }`}
      style={{
        backgroundColor: isBestDeal 
          ? 'rgba(0, 255, 136, 0.08)' 
          : 'rgba(19, 27, 47, 0.8)',
        backdropFilter: 'blur(20px)',
        borderWidth: '2px',
        borderColor: isBestDeal 
          ? '#00FF88' 
          : 'rgba(255, 255, 255, 0.05)',
        boxShadow: isBestDeal 
          ? '0 8px 32px rgba(0, 255, 136, 0.2)' 
          : '0 4px 16px rgba(0, 0, 0, 0.2)'
      }}
      whileHover={{
        y: -6,
        scale: 1.02,
        borderColor: '#00FF88',
        boxShadow: '0 12px 48px rgba(0, 255, 136, 0.25)'
      }}
    >
      {/* Best Deal Badge */}
      {isBestDeal && (
        <motion.div 
          initial={{ scale: 0, rotate: -180 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ type: 'spring', stiffness: 200, delay: 0.2 }}
          className="absolute -top-4 left-6 px-5 py-2 rounded-full text-xs font-black uppercase tracking-wider"
          style={{
            background: 'linear-gradient(135deg, #FFD700 0%, #FFA500 100%)',
            color: '#000',
            fontFamily: "'JetBrains Mono', monospace",
            boxShadow: '0 4px 20px rgba(255, 215, 0, 0.5)'
          }}
        >
          ⭐ BEST DEAL
        </motion.div>
      )}

      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="space-y-3 flex-1">
          {/* Rank & Source Badges */}
          <div className="flex items-center gap-3">
            {/* Rank Badge */}
            <div 
              className="px-4 py-2 rounded-xl font-black text-lg"
              style={{
                background: rankBadge.bg,
                color: rankBadge.text,
                fontFamily: "'JetBrains Mono', monospace",
                boxShadow: rank <= 3 ? '0 4px 12px rgba(0, 0, 0, 0.3)' : 'none'
              }}
            >
              {rankBadge.label}
            </div>

            {/* Source Type Badge */}
            <span 
              className="px-4 py-2 rounded-xl text-xs font-black uppercase tracking-wider"
              style={{
                backgroundColor: isOnline 
                  ? 'rgba(0, 229, 255, 0.15)' 
                  : 'rgba(0, 255, 136, 0.15)',
                color: isOnline ? '#00E5FF' : '#00FF88',
                borderWidth: '2px',
                borderColor: isOnline 
                  ? 'rgba(0, 229, 255, 0.3)' 
                  : 'rgba(0, 255, 136, 0.3)',
                fontFamily: "'JetBrains Mono', monospace"
              }}
            >
              {result.source_type}
            </span>

            {/* Negotiated Tag */}
            {result.negotiated && (
              <motion.span
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className="px-3 py-1 rounded-lg text-xs font-bold flex items-center gap-1"
                style={{
                  backgroundColor: 'rgba(0, 255, 136, 0.2)',
                  color: '#00FF88',
                  borderWidth: '1px',
                  borderColor: 'rgba(0, 255, 136, 0.4)'
                }}
              >
                <CheckCircle className="w-3 h-3" />
                Negotiated
              </motion.span>
            )}
          </div>

          {/* Vendor Name */}
          <h3 
            className="text-xl md:text-2xl font-semibold"
            style={{
              color: '#FFFFFF',
              fontFamily: "'Outfit', sans-serif"
            }}
          >
            {result.vendor_name}
          </h3>

          {/* Product Name */}
          <p 
            className="text-sm"
            style={{
              color: '#8BA3CB',
              fontFamily: "'Inter', sans-serif"
            }}
          >
            {result.product_name}
          </p>
        </div>

        {/* Price */}
        <div className="text-right">
          <div 
            className="text-4xl md:text-5xl font-black tracking-tight"
            style={{
              color: isBestDeal ? '#00FF88' : '#FFFFFF',
              fontFamily: "'JetBrains Mono', monospace",
              textShadow: isBestDeal ? '0 0 20px rgba(0, 255, 136, 0.3)' : 'none'
            }}
          >
            ₹{result.price.toLocaleString('en-IN')}
          </div>
        </div>
      </div>

      {/* Details */}
      <div className="space-y-3 mt-6">
        {/* Delivery Time */}
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4" style={{ color: '#8BA3CB' }} />
          <span 
            className="text-sm font-medium"
            style={{
              color: '#FFFFFF',
              fontFamily: "'Inter', sans-serif"
            }}
          >
            {result.delivery_time}
          </span>
        </div>

        {/* Availability */}
        <div className="flex items-center gap-2">
          <Package className="w-4 h-4" style={{ color: '#8BA3CB' }} />
          <span 
            className="text-sm font-medium"
            style={{
              color: '#FFFFFF',
              fontFamily: "'Inter', sans-serif"
            }}
          >
            {result.availability}
          </span>
        </div>

        {/* Confidence Meter */}
        <div className="space-y-2 pt-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4" style={{ color: '#8BA3CB' }} />
              <span 
                className="text-xs uppercase tracking-wider font-bold"
                style={{
                  color: '#8BA3CB',
                  fontFamily: "'JetBrains Mono', monospace"
                }}
              >
                Confidence
              </span>
            </div>
            <span 
              className="text-xs font-black"
              style={{
                color: '#00FF88',
                fontFamily: "'JetBrains Mono', monospace"
              }}
            >
              {Math.round(result.confidence * 100)}%
            </span>
          </div>

          {/* Progress Bar */}
          <div 
            className="w-full h-2 rounded-full overflow-hidden"
            style={{ backgroundColor: 'rgba(255, 255, 255, 0.1)' }}
          >
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${result.confidence * 100}%` }}
              transition={{ duration: 1, delay: index * 0.1, ease: 'easeOut' }}
              className="h-full rounded-full"
              style={{
                background: result.confidence > 0.85 
                  ? 'linear-gradient(90deg, #00FF88 0%, #00CC66 100%)'
                  : 'linear-gradient(90deg, #FFD700 0%, #00FF88 100%)',
                boxShadow: '0 0 10px rgba(0, 255, 136, 0.5)'
              }}
            />
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default ResultCard;