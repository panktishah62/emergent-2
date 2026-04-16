import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Zap, MapPin } from 'lucide-react';

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
    'nearest pharmacy in Delhi'
  ];

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Animated Background */}
      <div className="fixed inset-0 z-0">
        <div 
          className="absolute inset-0"
          style={{
            backgroundImage: 'url(https://static.prod-images.emergentagent.com/jobs/134413b3-51ad-4d7d-a9b8-f9d83c3de800/images/1d48159cb851139e8c5199bc398b36f17dae57cf0e259fc187babd56058a8642.png)',
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            opacity: 0.15
          }}
        />
        {/* Gradient overlay */}
        <div 
          className="absolute inset-0"
          style={{
            background: 'radial-gradient(circle at 50% 50%, rgba(0, 255, 136, 0.05) 0%, transparent 50%)'
          }}
        />
      </div>

      {/* Header */}
      <motion.header
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="relative z-10 pt-8 px-6"
      >
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-center gap-3">
            <div 
              className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{
                background: 'linear-gradient(135deg, #00FF88 0%, #00CC66 100%)',
                boxShadow: '0 0 20px rgba(0, 255, 136, 0.3)'
              }}
            >
              <Zap className="w-6 h-6" style={{ color: '#0A0F1C' }} />
            </div>
            <h1 
              className="text-4xl font-bold tracking-tight"
              style={{ 
                fontFamily: "'Outfit', sans-serif", 
                color: '#FFFFFF',
                textShadow: '0 0 30px rgba(0, 255, 136, 0.2)'
              }}
            >
              PriceHunter
            </h1>
          </div>
          <p 
            className="text-center mt-2 text-sm font-medium tracking-wide"
            style={{ 
              color: '#8BA3CB',
              fontFamily: "'Inter', sans-serif"
            }}
          >
            Online + Offline. Every price. One search.
          </p>
        </div>
      </motion.header>

      {/* Main Content */}
      <div className="relative z-10 flex flex-col items-center justify-center min-h-[calc(100vh-180px)] px-6 py-12">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: 'easeOut', delay: 0.2 }}
          className="w-full max-w-4xl mx-auto space-y-6"
        >
          {/* Search Form */}
          <form onSubmit={handleSearch} className="space-y-4">
            {/* Main Search Input */}
            <div className="relative">
              <input
                type="text"
                data-testid="search-input"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="What are you looking for? e.g., cheapest iPhone 15 near Koramangala"
                className="w-full px-8 py-7 text-xl rounded-3xl border-2 transition-all duration-300 focus:outline-none"
                style={{
                  backgroundColor: 'rgba(19, 27, 47, 0.95)',
                  backdropFilter: 'blur(20px)',
                  borderColor: 'rgba(0, 255, 136, 0.2)',
                  color: '#FFFFFF',
                  fontFamily: "'Inter', sans-serif",
                  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)'
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = '#00FF88';
                  e.target.style.boxShadow = '0 8px 32px rgba(0, 255, 136, 0.25)';
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = 'rgba(0, 255, 136, 0.2)';
                  e.target.style.boxShadow = '0 8px 32px rgba(0, 0, 0, 0.3)';
                }}
              />
            </div>

            {/* Location Input */}
            <div className="flex items-center gap-4">
              <div className="relative flex-1">
                <MapPin 
                  className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5" 
                  style={{ color: '#8BA3CB' }} 
                />
                <input
                  type="text"
                  data-testid="location-input"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="Location (optional) e.g., Koramangala Bangalore"
                  className="w-full pl-12 pr-4 py-4 text-base rounded-2xl border transition-all duration-300 focus:outline-none"
                  style={{
                    backgroundColor: 'rgba(19, 27, 47, 0.8)',
                    backdropFilter: 'blur(20px)',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    color: '#FFFFFF',
                    fontFamily: "'Inter', sans-serif"
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = 'rgba(0, 255, 136, 0.4)';
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = 'rgba(255, 255, 255, 0.1)';
                  }}
                />
              </div>

              {/* Search Button with Gradient */}
              <button
                type="submit"
                data-testid="search-submit-button"
                className="px-10 py-4 text-lg font-bold rounded-2xl transition-all duration-300 transform hover:scale-105 active:scale-95"
                style={{
                  background: 'linear-gradient(135deg, #00FF88 0%, #00CC66 100%)',
                  color: '#0A0F1C',
                  fontFamily: "'Inter', sans-serif",
                  boxShadow: '0 8px 24px rgba(0, 255, 136, 0.35)'
                }}
                onMouseEnter={(e) => {
                  e.target.style.boxShadow = '0 12px 32px rgba(0, 255, 136, 0.5)';
                }}
                onMouseLeave={(e) => {
                  e.target.style.boxShadow = '0 8px 24px rgba(0, 255, 136, 0.35)';
                }}
              >
                Search
              </button>
            </div>
          </form>

          {/* Example Queries */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.6 }}
            className="space-y-3 pt-4"
          >
            <p 
              className="text-xs font-bold uppercase tracking-widest text-center"
              style={{ color: '#8BA3CB', fontFamily: "'JetBrains Mono', monospace" }}
            >
              Try These
            </p>
            <div className="flex flex-wrap justify-center gap-3">
              {exampleQueries.map((example, idx) => (
                <motion.button
                  key={idx}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.7 + idx * 0.1 }}
                  onClick={() => {
                    const parts = example.split(' near ').length > 1 
                      ? example.split(' near ') 
                      : example.split(' in ');
                    setQuery(parts[0]);
                    if (parts[1]) setLocation(parts[1]);
                  }}
                  className="px-4 py-2 text-sm rounded-xl border transition-all duration-300"
                  style={{
                    backgroundColor: 'rgba(255, 255, 255, 0.03)',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    color: '#8BA3CB',
                    fontFamily: "'Inter', sans-serif"
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.backgroundColor = 'rgba(0, 255, 136, 0.1)';
                    e.target.style.borderColor = 'rgba(0, 255, 136, 0.3)';
                    e.target.style.color = '#00FF88';
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.03)';
                    e.target.style.borderColor = 'rgba(255, 255, 255, 0.1)';
                    e.target.style.color = '#8BA3CB';
                  }}
                >
                  {example}
                </motion.button>
              ))}
            </div>
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
};

export default SearchPage;