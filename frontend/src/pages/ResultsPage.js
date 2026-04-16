import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import LoadingStage from '../components/LoadingStage';
import ResultCard from '../components/ResultCard';
import { ArrowLeft, Search } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Visitor ID management
const getVisitorId = () => {
  let visitorId = localStorage.getItem('visitor_id');
  if (!visitorId) {
    visitorId = 'visitor_' + Math.random().toString(36).substring(2, 15) + Date.now();
    localStorage.setItem('visitor_id', visitorId);
  }
  return visitorId;
};

const ResultsPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { query, location: searchLocation } = location.state || {};

  const [loading, setLoading] = useState(true);
  const [currentStage, setCurrentStage] = useState(0);
  const [results, setResults] = useState([]);
  const [filteredResults, setFilteredResults] = useState([]);
  const [searchData, setSearchData] = useState(null);
  const [error, setError] = useState(null);
  
  // Sort and filter states
  const [sortBy, setSortBy] = useState('rank'); // 'rank', 'price', 'delivery'
  const [filterSource, setFilterSource] = useState('all'); // 'all', 'online', 'offline'

  const stages = [
    'Understanding your query',
    'Searching online platforms',
    'Calling nearby vendors',
    'Comparing results'
  ];

  // Apply sorting and filtering
  React.useEffect(() => {
    if (!results.length) return;
    
    let filtered = [...results];
    
    // Filter by source
    if (filterSource !== 'all') {
      filtered = filtered.filter(r => 
        r.source_type.toLowerCase() === filterSource.toLowerCase()
      );
    }
    
    // Sort
    if (sortBy === 'price') {
      filtered.sort((a, b) => a.price - b.price);
    } else if (sortBy === 'delivery') {
      // Simple sort - in production you'd parse delivery times
      filtered.sort((a, b) => a.delivery_time.localeCompare(b.delivery_time));
    }
    // 'rank' keeps original order
    
    setFilteredResults(filtered);
  }, [results, sortBy, filterSource]);

  useEffect(() => {
    if (!query) {
      navigate('/');
      return;
    }

    const performSearch = async () => {
      let stageInterval;
      try {
        // Get visitor ID
        const visitorId = getVisitorId();
        
        // Cycle through stages during loading
        stageInterval = setInterval(() => {
          setCurrentStage(prev => (prev + 1) % stages.length);
        }, 3000); // Cycle every 3 seconds to keep user engaged

        // Perform actual API call with extended timeout and visitor tracking
        const response = await axios.post(`${API}/search`, {
          query,
          location: searchLocation
        }, {
          headers: {
            'X-Visitor-ID': visitorId
          },
          timeout: 120000 // 120 second timeout for voice calls
        });

        clearInterval(stageInterval);
        setResults(response.data.results);
        setSearchData(response.data);
        setLoading(false);
      } catch (err) {
        if (stageInterval) clearInterval(stageInterval);
        console.error('Search error:', err);
        setError(err.response?.data?.detail || err.message || 'Failed to fetch results');
        setLoading(false);
      }
    };

    performSearch();
  }, [query, searchLocation]);

  if (loading) {
    return <LoadingStage stages={stages} currentStage={currentStage} />;
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6">
        <div className="text-center space-y-4">
          <p className="text-xl" style={{ color: '#FF4444' }}>
            {error}
          </p>
          <button
            onClick={() => navigate('/')}
            className="px-6 py-3 rounded-full"
            style={{
              backgroundColor: '#00FF88',
              color: '#0A0F1C',
              fontFamily: "'Inter', sans-serif"
            }}
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen relative">
      {/* Background Layer */}
      <div 
        className="fixed inset-0 z-0"
        style={{
          backgroundImage: 'url(https://static.prod-images.emergentagent.com/jobs/134413b3-51ad-4d7d-a9b8-f9d83c3de800/images/e3f50c20c28c79f30a796f23979ccd6419c87951a81abb512be8c39ee95eed75.png)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          opacity: 0.1,
          pointerEvents: 'none'
        }}
      />

      {/* Content */}
      <div className="relative z-10 px-6 py-12 md:px-12">
        <div className="max-w-6xl mx-auto space-y-8">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="flex items-center justify-between"
          >
            <button
              onClick={() => navigate('/')}
              data-testid="back-button"
              className="flex items-center gap-2 px-4 py-2 rounded-full transition-all duration-300"
              style={{
                backgroundColor: 'rgba(255, 255, 255, 0.02)',
                borderWidth: '1px',
                borderColor: 'rgba(255, 255, 255, 0.08)',
                color: '#8BA3CB'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'rgba(0, 255, 136, 0.3)';
                e.currentTarget.style.color = '#00FF88';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
                e.currentTarget.style.color = '#8BA3CB';
              }}
            >
              <ArrowLeft className="w-5 h-5" />
              <span>New Search</span>
            </button>

            <div className="flex items-center gap-2">
              <Search className="w-5 h-5" style={{ color: '#00FF88' }} />
              <span 
                className="text-lg font-medium"
                style={{ color: '#FFFFFF', fontFamily: "'Outfit', sans-serif" }}
              >
                {query}
              </span>
            </div>
          </motion.div>

          {/* Parsed Query Info */}
          {searchData?.parsed_query && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="px-6 py-4 rounded-2xl"
              style={{
                backgroundColor: 'rgba(19, 27, 47, 0.6)',
                backdropFilter: 'blur(20px)',
                borderWidth: '1px',
                borderColor: 'rgba(255, 255, 255, 0.08)'
              }}
            >
              <div className="flex flex-wrap items-center gap-3 text-sm">
                <span style={{ color: '#8BA3CB', fontFamily: "'Inter', sans-serif" }}>
                  Searching for:
                </span>
                <span 
                  className="px-3 py-1 rounded-md font-semibold"
                  style={{
                    backgroundColor: 'rgba(0, 255, 136, 0.15)',
                    color: '#00FF88',
                    fontFamily: "'Inter', sans-serif"
                  }}
                >
                  {searchData.parsed_query.product}
                </span>
                <span style={{ color: '#8BA3CB' }}>in</span>
                <span 
                  className="px-3 py-1 rounded-md"
                  style={{
                    backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    color: '#8BA3CB',
                    fontFamily: "'Inter', sans-serif"
                  }}
                >
                  {searchData.parsed_query.category}
                </span>
                <span style={{ color: '#8BA3CB' }}>•</span>
                <span 
                  className="px-3 py-1 rounded-md"
                  style={{
                    backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    color: '#8BA3CB',
                    fontFamily: "'Inter', sans-serif"
                  }}
                >
                  📍 {searchData.parsed_query.location}
                </span>
                <span style={{ color: '#8BA3CB' }}>•</span>
                <span 
                  className="px-3 py-1 rounded-md"
                  style={{
                    backgroundColor: 'rgba(0, 229, 255, 0.1)',
                    color: '#00E5FF',
                    fontFamily: "'Inter', sans-serif"
                  }}
                >
                  Intent: {searchData.parsed_query.intent}
                </span>
              </div>
            </motion.div>
          )}

          {/* Summary Bar */}
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            data-testid="summary-bar"
            className="px-6 py-4 rounded-full"
            style={{
              backgroundColor: 'rgba(19, 27, 47, 0.8)',
              backdropFilter: 'blur(20px)',
              borderWidth: '1px',
              borderColor: 'rgba(255, 255, 255, 0.08)'
            }}
          >
            <div className="flex flex-wrap items-center justify-center gap-4 text-sm">
              <span style={{ color: '#FFFFFF', fontFamily: "'JetBrains Mono', monospace" }}>
                Found <span style={{ color: '#00FF88', fontWeight: 'bold' }}>{searchData?.total_results}</span> results
              </span>
              <span style={{ color: '#8BA3CB' }}>in</span>
              <span style={{ color: '#00FF88', fontFamily: "'JetBrains Mono', monospace", fontWeight: 'bold' }}>
                {searchData?.search_time}s
              </span>
              <span style={{ color: '#8BA3CB' }}>•</span>
              <span 
                className="px-3 py-1 rounded-md text-xs font-bold uppercase"
                style={{
                  backgroundColor: 'rgba(0, 229, 255, 0.1)',
                  color: '#00E5FF',
                  borderWidth: '1px',
                  borderColor: 'rgba(0, 229, 255, 0.2)',
                  fontFamily: "'JetBrains Mono', monospace"
                }}
              >
                {searchData?.online_count} Online
              </span>
              <span 
                className="px-3 py-1 rounded-md text-xs font-bold uppercase"
                style={{
                  backgroundColor: 'rgba(0, 255, 136, 0.1)',
                  color: '#00FF88',
                  borderWidth: '1px',
                  borderColor: 'rgba(0, 255, 136, 0.2)',
                  fontFamily: "'JetBrains Mono', monospace"
                }}
              >
                {searchData?.offline_count} Offline
              </span>
            </div>
          </motion.div>

          {/* Sort and Filter Controls */}
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="flex flex-wrap items-center justify-between gap-4 px-6 py-4 rounded-2xl"
            style={{
              backgroundColor: 'rgba(19, 27, 47, 0.6)',
              backdropFilter: 'blur(20px)',
              borderWidth: '1px',
              borderColor: 'rgba(255, 255, 255, 0.08)'
            }}
          >
            <div className="flex items-center gap-3">
              <span className="text-sm font-bold" style={{ color: '#8BA3CB' }}>Sort by:</span>
              <div className="flex gap-2">
                {[
                  { value: 'rank', label: 'Best Match' },
                  { value: 'price', label: 'Price' },
                  { value: 'delivery', label: 'Delivery' }
                ].map(option => (
                  <button
                    key={option.value}
                    onClick={() => setSortBy(option.value)}
                    className="px-4 py-2 text-sm rounded-lg transition-all duration-300"
                    style={{
                      backgroundColor: sortBy === option.value 
                        ? 'rgba(0, 255, 136, 0.2)' 
                        : 'rgba(255, 255, 255, 0.05)',
                      color: sortBy === option.value ? '#00FF88' : '#8BA3CB',
                      borderWidth: '1px',
                      borderColor: sortBy === option.value 
                        ? 'rgba(0, 255, 136, 0.4)' 
                        : 'transparent',
                      fontFamily: "'Inter', sans-serif"
                    }}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <span className="text-sm font-bold" style={{ color: '#8BA3CB' }}>Show:</span>
              <div className="flex gap-2">
                {[
                  { value: 'all', label: 'All' },
                  { value: 'online', label: 'Online' },
                  { value: 'offline', label: 'Offline' }
                ].map(option => (
                  <button
                    key={option.value}
                    onClick={() => setFilterSource(option.value)}
                    className="px-4 py-2 text-sm rounded-lg transition-all duration-300"
                    style={{
                      backgroundColor: filterSource === option.value 
                        ? 'rgba(0, 255, 136, 0.2)' 
                        : 'rgba(255, 255, 255, 0.05)',
                      color: filterSource === option.value ? '#00FF88' : '#8BA3CB',
                      borderWidth: '1px',
                      borderColor: filterSource === option.value 
                        ? 'rgba(0, 255, 136, 0.4)' 
                        : 'transparent',
                      fontFamily: "'Inter', sans-serif"
                    }}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          </motion.div>

          {/* Results Grid */}
          <motion.div
            initial="hidden"
            animate="visible"
            variants={{
              visible: {
                transition: {
                  staggerChildren: 0.1
                }
              }
            }}
            className="grid grid-cols-1 md:grid-cols-2 gap-6"
          >
            {filteredResults.map((result, index) => (
              <ResultCard key={result.id} result={result} index={index} />
            ))}
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default ResultsPage;
