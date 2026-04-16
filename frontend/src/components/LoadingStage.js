import React from 'react';
import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';

const LoadingStage = ({ stages, currentStage }) => {
  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="text-center space-y-12"
      >
        {/* Glowing Orb */}
        <div className="flex justify-center">
          <div 
            className="relative w-32 h-32 rounded-full flex items-center justify-center"
            style={{
              background: 'linear-gradient(135deg, rgba(0, 255, 136, 0.2) 0%, rgba(0, 255, 136, 0.05) 100%)',
              border: '2px solid rgba(0, 255, 136, 0.4)',
              boxShadow: '0 0 60px rgba(0, 255, 136, 0.3)'
            }}
          >
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
            >
              <Loader2 className="w-16 h-16" style={{ color: '#00FF88' }} />
            </motion.div>
            
            {/* Pulse rings */}
            <motion.div
              className="absolute inset-0 rounded-full"
              style={{
                border: '2px solid rgba(0, 255, 136, 0.3)'
              }}
              animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0, 0.5] }}
              transition={{ duration: 2, repeat: Infinity }}
            />
          </div>
        </div>

        {/* Stages List */}
        <div className="space-y-4 max-w-md mx-auto">
          {stages.map((stage, index) => {
            const isActive = index === currentStage;
            const isCompleted = index < currentStage;
            const isUpcoming = index > currentStage;

            return (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: index * 0.1 }}
                className="flex items-center gap-4 px-6 py-3 rounded-xl"
                style={{
                  backgroundColor: isActive 
                    ? 'rgba(0, 255, 136, 0.1)' 
                    : 'rgba(255, 255, 255, 0.02)',
                  borderWidth: '1px',
                  borderColor: isActive 
                    ? 'rgba(0, 255, 136, 0.3)' 
                    : 'rgba(255, 255, 255, 0.05)'
                }}
              >
                {/* Status Indicator */}
                <div 
                  className="w-3 h-3 rounded-full flex-shrink-0"
                  style={{
                    backgroundColor: isActive 
                      ? '#00FF88' 
                      : isCompleted 
                      ? '#8BA3CB' 
                      : 'rgba(139, 163, 203, 0.3)'
                  }}
                >
                  {isActive && (
                    <motion.div
                      className="w-full h-full rounded-full"
                      style={{ backgroundColor: '#00FF88' }}
                      animate={{ scale: [1, 1.5, 1], opacity: [1, 0.5, 1] }}
                      transition={{ duration: 1, repeat: Infinity }}
                    />
                  )}
                </div>

                {/* Stage Text */}
                <span
                  className="text-base font-medium"
                  style={{
                    color: isActive 
                      ? '#00FF88' 
                      : isCompleted 
                      ? '#8BA3CB' 
                      : 'rgba(139, 163, 203, 0.5)',
                    fontFamily: "'Inter', sans-serif"
                  }}
                >
                  {stage}
                </span>
              </motion.div>
            );
          })}
        </div>

        {/* Loading Text */}
        <motion.p
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="text-sm"
          style={{
            color: '#8BA3CB',
            fontFamily: "'JetBrains Mono', monospace"
          }}
        >
          This may take a few moments...
        </motion.p>
      </motion.div>
    </div>
  );
};

export default LoadingStage;