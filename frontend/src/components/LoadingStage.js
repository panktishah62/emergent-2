import React from 'react';
import { motion } from 'framer-motion';

const LoadingStage = ({ stages, currentStage }) => {
  const stageEmojis = ['🧠', '🔍', '📞', '📊'];
  const stageDescriptions = [
    'Understanding your query...',
    'Searching online platforms...',
    'Calling nearby vendors...',
    'Comparing results...'
  ];

  return (
    <div className="min-h-screen flex items-center justify-center px-6" style={{ backgroundColor: '#0A0F1C' }}>
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="text-center space-y-12 max-w-2xl w-full"
      >
        {/* Animated Logo */}
        <motion.div
          animate={{ 
            scale: [1, 1.05, 1],
            rotate: [0, 5, -5, 0]
          }}
          transition={{ 
            duration: 3, 
            repeat: Infinity,
            ease: "easeInOut"
          }}
          className="text-8xl"
        >
          {stageEmojis[currentStage]}
        </motion.div>

        {/* Current Stage Text */}
        <motion.h2
          key={currentStage}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.5 }}
          className="text-2xl font-semibold"
          style={{ 
            color: '#FFFFFF',
            fontFamily: "'Outfit', sans-serif"
          }}
        >
          {stageDescriptions[currentStage]}
        </motion.h2>

        {/* Progress Bar Container */}
        <div className="space-y-6">
          <div 
            className="w-full h-2 rounded-full overflow-hidden"
            style={{ backgroundColor: 'rgba(255, 255, 255, 0.1)' }}
          >
            {/* Animated Progress Bar */}
            <motion.div
              className="h-full rounded-full"
              style={{
                background: 'linear-gradient(90deg, #00FF88 0%, #00CC66 100%)',
                boxShadow: '0 0 20px rgba(0, 255, 136, 0.6)'
              }}
              initial={{ width: '0%' }}
              animate={{ 
                width: ['0%', '100%'],
              }}
              transition={{ 
                duration: 3,
                repeat: Infinity,
                ease: "linear"
              }}
            />
          </div>

          {/* Stage Indicators */}
          <div className="flex justify-between items-center">
            {stageDescriptions.map((stage, index) => {
              const isActive = index === currentStage;
              const isCompleted = index < currentStage;
              
              return (
                <div key={index} className="flex flex-col items-center gap-2 flex-1">
                  <motion.div 
                    className="w-3 h-3 rounded-full"
                    style={{
                      backgroundColor: isActive 
                        ? '#00FF88' 
                        : isCompleted 
                        ? '#8BA3CB' 
                        : 'rgba(139, 163, 203, 0.3)'
                    }}
                    animate={isActive ? {
                      scale: [1, 1.3, 1],
                      boxShadow: [
                        '0 0 0px rgba(0, 255, 136, 0)',
                        '0 0 20px rgba(0, 255, 136, 0.6)',
                        '0 0 0px rgba(0, 255, 136, 0)'
                      ]
                    } : {}}
                    transition={{ duration: 1.5, repeat: Infinity }}
                  />
                  <span 
                    className="text-xs text-center hidden md:block"
                    style={{
                      color: isActive ? '#00FF88' : isCompleted ? '#8BA3CB' : 'rgba(139, 163, 203, 0.5)',
                      fontFamily: "'Inter', sans-serif"
                    }}
                  >
                    {stage.split('...')[0]}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Pulsing Message */}
        <motion.p
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="text-sm"
          style={{
            color: '#8BA3CB',
            fontFamily: "'JetBrains Mono', monospace"
          }}
        >
          Finding you the best deals...
        </motion.p>
      </motion.div>
    </div>
  );
};

export default LoadingStage;