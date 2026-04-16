import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Sparkles, MapPin, TrendingUp } from 'lucide-react';

const SearchPage = () => {
  const [query, setQuery] = useState('');
  const [location, setLocation] = useState('');
  const navigate = useNavigate();

  const handleSearch = (e) => {
    e.preventDefault();
    if (query.trim()) {
      navigate('/results', { state: { query, location } });
    }
  };

  const exampleQueries = [
    'cheapest iPhone 15 near Koramangala',
    'best price for tomatoes in Rajkot',
    'fastest delivery for laptop in Mumbai',
    'nearest store for milk in Delhi'
  ];

  return (
    <div className="min-h-screen relative">
      {/* Background Layer */}
      <div 
        className="fixed inset-0 z-0"
        style={{
          backgroundImage: 'url(https://static.prod-images.emergentagent.com/jobs/134413b3-51ad-4d7d-a9b8-f9d83c3de800/images/1d48159cb851139e8c5199bc398b36f17dae57cf0e259fc187babd56058a8642.png)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          opacity: 0.2,
          pointerEvents: 'none'
        }}
      />

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen px-6 py-12">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className="w-full max-w-4xl mx-auto text-center space-y-8"
        >
          {/* Logo and Title */}
          <div className="space-y-4">
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="inline-flex items-center justify-center w-20 h-20 rounded-full"
              style={{
                background: 'linear-gradient(135deg, rgba(0, 255, 136, 0.1) 0%, rgba(0, 255, 136, 0.05) 100%)',
                border: '2px solid rgba(0, 255, 136, 0.3)',
                boxShadow: '0 0 40px rgba(0, 255, 136, 0.2)'
              }}
            >
              <TrendingUp className="w-10 h-10" style={{ color: '#00FF88' }} />
            </motion.div>

            <h1 
              className="text-5xl md:text-6xl lg:text-7xl font-light tracking-tighter"
              style={{ fontFamily: "'Outfit', sans-serif", color: '#FFFFFF' }}
            >
              Price<span style={{ color: '#00FF88' }}>Hunter</span>
            </h1>
            
            <p 
              className="text-base md:text-lg leading-relaxed max-w-2xl mx-auto"
              style={{ color: '#8BA3CB' }}
            >
              Find the best deals across online platforms and local vendors in India.
              <br />
              Compare prices instantly with AI-powered search.
            </p>
          </div>

          {/* Search Form */}
          <motion.form
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            onSubmit={handleSearch}
            className="space-y-4"
          >
            {/* Main Search Input */}
            <div className="relative">
              <div className="absolute left-6 top-1/2 transform -translate-y-1/2 z-10">
                <Sparkles className="w-6 h-6" style={{ color: '#00FF88' }} />
              </div>
              <input
                type="text"
                data-testid="search-input"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="What are you looking for?"
                className="w-full px-16 py-6 text-xl md:text-2xl rounded-full border transition-all duration-300"
                style={{
                  backgroundColor: 'rgba(19, 27, 47, 0.8)',
                  backdropFilter: 'blur(20px)',
                  borderColor: 'rgba(0, 255, 136, 0.3)',
                  color: '#FFFFFF',
                  fontFamily: "'Inter', sans-serif"
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = 'rgba(0, 255, 136, 0.5)';
                  e.target.style.boxShadow = '0 0 30px rgba(0, 255, 136, 0.15)';
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = 'rgba(0, 255, 136, 0.3)';
                  e.target.style.boxShadow = 'none';
                }}
              />
            </div>

            {/* Location Input */}
            <div className="relative max-w-md mx-auto">
              <div className="absolute left-4 top-1/2 transform -translate-y-1/2 z-10">
                <MapPin className="w-5 h-5" style={{ color: '#8BA3CB' }} />
              </div>
              <input
                type="text"
                data-testid="location-input"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="Location (optional)"
                className="w-full px-12 py-3 text-base rounded-full border transition-all duration-300"
                style={{
                  backgroundColor: 'rgba(19, 27, 47, 0.6)',
                  backdropFilter: 'blur(20px)',
                  borderColor: 'rgba(255, 255, 255, 0.08)',
                  color: '#FFFFFF',
                  fontFamily: "'Inter', sans-serif"
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = 'rgba(0, 255, 136, 0.3)';
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = 'rgba(255, 255, 255, 0.08)';
                }}
              />
            </div>

            {/* Search Button */}
            <button
              type="submit"
              data-testid="search-submit-button"
              className="px-12 py-4 text-lg font-semibold rounded-full transition-all duration-300 transform hover:scale-105"
              style={{
                backgroundColor: '#00FF88',
                color: '#0A0F1C',
                fontFamily: "'Inter', sans-serif"
              }}
              onMouseEnter={(e) => {
                e.target.style.backgroundColor = '#FFFFFF';
                e.target.style.boxShadow = '0 0 40px rgba(0, 255, 136, 0.3)';
              }}
              onMouseLeave={(e) => {
                e.target.style.backgroundColor = '#00FF88';
                e.target.style.boxShadow = 'none';
              }}
            >
              Search Deals
            </button>
          </motion.form>

          {/* Example Queries */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.8 }}
            className="space-y-3"
          >
            <p 
              className="text-xs font-bold uppercase tracking-widest"
              style={{ color: '#8BA3CB', fontFamily: "'JetBrains Mono', monospace" }}
            >
              Try These
            </p>
            <div className="flex flex-wrap justify-center gap-3">
              {exampleQueries.map((example, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    const parts = example.split(' near ').length > 1 
                      ? example.split(' near ') 
                      : example.split(' in ');
                    setQuery(parts[0]);
                    if (parts[1]) setLocation(parts[1]);
                  }}
                  className="px-4 py-2 text-sm rounded-md border transition-all duration-300"
                  style={{
                    backgroundColor: 'rgba(255, 255, 255, 0.02)',
                    borderColor: 'rgba(255, 255, 255, 0.08)',
                    color: '#8BA3CB',
                    fontFamily: "'Inter', sans-serif"
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.borderColor = 'rgba(0, 255, 136, 0.3)';
                    e.target.style.color = '#00FF88';
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.borderColor = 'rgba(255, 255, 255, 0.08)';
                    e.target.style.color = '#8BA3CB';
                  }}
                >
                  {example}
                </button>
              ))}
            </div>
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
};

export default SearchPage;