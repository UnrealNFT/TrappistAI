import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Sparkles, Image, Music, Box, Calendar, Loader2, ExternalLink, User } from 'lucide-react'

const Community = ({ wallet }) => {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all') // all, image, music, 3d

  useEffect(() => {
    fetchCommunityItems()
  }, [filter])

  const fetchCommunityItems = async () => {
    try {
      setLoading(true)
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      
      // Fetch all shared items (isPublic = true)
      const response = await fetch(`${API_URL}/api/community/feed`)
      const data = await response.json()
      
      if (data.success) {
        let filteredItems = data.listings || []
        
        // Filter by type
        if (filter !== 'all') {
          filteredItems = filteredItems.filter(item => item.assetType === filter)
        }
        
        setItems(filteredItems)
      }
    } catch (error) {
      console.error('Error fetching community items:', error)
    } finally {
      setLoading(false)
    }
  }

  const getAssetIcon = (assetType) => {
    switch (assetType) {
      case 'image':
        return <Image className="w-5 h-5" />
      case 'music':
        return <Music className="w-5 h-5" />
      case '3d':
        return <Box className="w-5 h-5" />
      default:
        return <Sparkles className="w-5 h-5" />
    }
  }

  const formatDate = (dateString) => {
    const date = new Date(dateString)
    const now = new Date()
    const diff = now - date
    const hours = Math.floor(diff / (1000 * 60 * 60))
    const days = Math.floor(hours / 24)
    
    if (days > 0) return `${days}d ago`
    if (hours > 0) return `${hours}h ago`
    return 'Just now'
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-900 via-black to-gray-900 pt-20 px-4 pb-20">
      <div className="max-w-7xl mx-auto">
        
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2 flex items-center gap-3">
            <Sparkles className="w-10 h-10 text-green-400" />
            Community Feed
          </h1>
          <p className="text-gray-400">Discover AI creations shared by the community</p>
        </div>

        {/* Filters */}
        <div className="flex gap-2 mb-8 overflow-x-auto pb-2">
          <button
            onClick={() => setFilter('all')}
            className={`px-4 py-2 rounded-lg font-medium transition whitespace-nowrap ${
              filter === 'all'
                ? 'bg-green-600 text-white'
                : 'bg-gray-900/50 text-gray-400 hover:text-white'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setFilter('image')}
            className={`px-4 py-2 rounded-lg font-medium transition whitespace-nowrap flex items-center gap-2 ${
              filter === 'image'
                ? 'bg-green-600 text-white'
                : 'bg-gray-900/50 text-gray-400 hover:text-white'
            }`}
          >
            <Image className="w-4 h-4" />
            Images
          </button>
          <button
            onClick={() => setFilter('music')}
            className={`px-4 py-2 rounded-lg font-medium transition whitespace-nowrap flex items-center gap-2 ${
              filter === 'music'
                ? 'bg-green-600 text-white'
                : 'bg-gray-900/50 text-gray-400 hover:text-white'
            }`}
          >
            <Music className="w-4 h-4" />
            Music
          </button>
          <button
            onClick={() => setFilter('3d')}
            className={`px-4 py-2 rounded-lg font-medium transition whitespace-nowrap flex items-center gap-2 ${
              filter === '3d'
                ? 'bg-green-600 text-white'
                : 'bg-gray-900/50 text-gray-400 hover:text-white'
            }`}
          >
            <Box className="w-4 h-4" />
            3D Models
          </button>
        </div>

        {/* Loading */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-green-400" />
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-20">
            <Sparkles className="w-16 h-16 mx-auto mb-4 text-gray-600" />
            <h3 className="text-xl font-bold text-white mb-2">No items shared yet</h3>
            <p className="text-gray-400">
              Be the first to share your AI creations with the community!
            </p>
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
          >
            {items.map((item, index) => (
              <motion.div
                key={item.listingId || index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className="bg-gray-900/50 border border-gray-800 rounded-lg overflow-hidden hover:border-green-500/50 transition group"
              >
                {/* Asset Preview */}
                <div className="relative">
                  {item.assetType === 'image' && (
                    <img 
                      src={item.assetUrl} 
                      alt="Community creation" 
                      className="w-full h-64 object-cover group-hover:scale-105 transition-transform duration-300" 
                    />
                  )}
                  {item.assetType === 'music' && (
                    <div className="w-full h-64 bg-gradient-to-br from-green-900/50 to-gray-900/50 flex items-center justify-center">
                      <Music className="w-20 h-20 text-green-400 group-hover:scale-110 transition-transform" />
                    </div>
                  )}
                  {item.assetType === '3d' && (
                    <div className="w-full h-64 bg-gradient-to-br from-blue-900/50 to-cyan-900/50 flex items-center justify-center">
                      <Box className="w-20 h-20 text-cyan-400 group-hover:scale-110 transition-transform" />
                    </div>
                  )}
                  
                  {/* Type Badge */}
                  <div className="absolute top-3 left-3 px-3 py-1 bg-black/70 backdrop-blur-sm rounded-full flex items-center gap-2">
                    {getAssetIcon(item.assetType)}
                    <span className="text-white text-sm font-medium capitalize">{item.assetType}</span>
                  </div>
                </div>

                {/* Content */}
                <div className="p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <User className="w-4 h-4 text-gray-400" />
                    <span className="text-sm text-gray-400">
                      {item.walletAddress ? `${item.walletAddress.substring(0, 8)}...` : 'Anonymous'}
                    </span>
                    <span className="text-gray-600">•</span>
                    <div className="flex items-center gap-1 text-sm text-gray-400">
                      <Calendar className="w-3 h-3" />
                      {formatDate(item.createdAt)}
                    </div>
                  </div>

                  {item.prompt && (
                    <p className="text-sm text-gray-300 mb-4 line-clamp-2">
                      {item.prompt}
                    </p>
                  )}

                  <a
                    href={item.assetUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-full px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition flex items-center justify-center gap-2"
                  >
                    <ExternalLink className="w-4 h-4" />
                    View Full
                  </a>
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}
      </div>
    </div>
  )
}

export default Community
