import React from 'react';
import { motion } from 'framer-motion';
import { Clock, TrendingUp, ShieldCheck, Package } from 'lucide-react';

const ResultCard = ({ result, index }) => {
  const isBestDeal = result.is_best_deal;
  const isOnline = result.source_type === 'ONLINE';

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
      className={`relative p-6 md:p-8 rounded-2xl transition-all duration-300 cursor-pointer ${
        isBestDeal ? 'md:col-span-2' : ''
      }`}
      style={{
        backgroundColor: isBestDeal 
          ? 'rgba(0, 255, 136, 0.08)' 
          : 'rgba(255, 255, 255, 0.02)',
        backdropFilter: 'blur(20px)',
        borderWidth: '1px',
        borderColor: isBestDeal 
          ? 'rgba(0, 255, 136, 0.4)' 
          : 'rgba(255, 255, 255, 0.05)',
        boxShadow: isBestDeal 
          ? '0 8px 32px rgba(0, 255, 136, 0.15)' 
          : 'none'
      }}
      whileHover={{
        y: -4,
        borderColor: 'rgba(0, 255, 136, 0.3)',
        backgroundColor: isBestDeal 
          ? 'rgba(0, 255, 136, 0.1)' 
          : 'rgba(255, 255, 255, 0.04)'
      }}
    >
      {/* Best Deal Badge */}
      {isBestDeal && (
        <div 
          className="absolute -top-3 left-6 px-4 py-1 rounded-md text-xs font-bold uppercase"
          style={{
            backgroundColor: '#00FF88',
            color: '#0A0F1C',
            fontFamily: "'JetBrains Mono', monospace",
            boxShadow: '0 4px 12px rgba(0, 255, 136, 0.4)'
          }}
        >
          BEST DEAL
        </div>
      )}

      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="space-y-2 flex-1">
          {/* Rank Badge */}
          <div className="flex items-center gap-3">
            <div 
              className="w-10 h-10 rounded-full flex items-center justify-center font-bold"
              style={{
                backgroundColor: isBestDeal 
                  ? 'rgba(0, 255, 136, 0.2)' 
                  : 'rgba(255, 255, 255, 0.05)',
                color: isBestDeal ? '#00FF88' : '#8BA3CB',
                fontFamily: "'JetBrains Mono', monospace"
              }}
            >
              #{result.rank}
            </div>

            {/* Source Type Badge */}
            <span 
              className="px-3 py-1 rounded-md text-xs font-bold uppercase"
              style={{
                backgroundColor: isOnline 
                  ? 'rgba(0, 229, 255, 0.1)' 
                  : 'rgba(0, 255, 136, 0.1)',
                color: isOnline ? '#00E5FF' : '#00FF88',
                borderWidth: '1px',
                borderColor: isOnline 
                  ? 'rgba(0, 229, 255, 0.2)' 
                  : 'rgba(0, 255, 136, 0.2)',
                fontFamily: "'JetBrains Mono', monospace"
              }}
            >
              {result.source_type}
            </span>
          </div>

          {/* Vendor Name */}
          <h3 
            className="text-xl md:text-2xl font-medium"
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
            className="text-3xl md:text-4xl font-bold tracking-tight"
            style={{
              color: '#FFFFFF',
              fontFamily: "'JetBrains Mono', monospace"
            }}
          >
            ₹{result.price.toLocaleString('en-IN')}
          </div>
        </div>
      </div>

      {/* Details */}
      <div className="space-y-3">
        {/* Delivery Time */}
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4" style={{ color: '#8BA3CB' }} />
          <span 
            className="text-sm"
            style={{
              color: '#8BA3CB',
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
            className="text-sm"
            style={{
              color: '#8BA3CB',
              fontFamily: "'Inter', sans-serif"
            }}
          >
            {result.availability}
          </span>
        </div>

        {/* Confidence Meter */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4" style={{ color: '#8BA3CB' }} />
              <span 
                className="text-xs uppercase tracking-wide"
                style={{
                  color: '#8BA3CB',
                  fontFamily: "'JetBrains Mono', monospace"
                }}
              >
                Confidence
              </span>
            </div>
            <span 
              className="text-xs font-bold"
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
              transition={{ duration: 0.8, delay: index * 0.1 }}
              className="h-full rounded-full"
              style={{
                background: result.confidence > 0.85 
                  ? 'linear-gradient(90deg, #00FF88 0%, #00DD77 100%)'
                  : 'linear-gradient(90deg, #FFD700 0%, #00FF88 100%)'
              }}
            />
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default ResultCard;