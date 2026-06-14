import { useState, useEffect } from 'react'
import { User, Link as LinkIcon, CheckCircle, X, Loader2, ExternalLink, Image as ImageIcon, Music, Box, Calendar } from 'lucide-react'
import { getProfileInfo, linkTelegram, verifyTelegramCode, unlinkTelegram } from '../services/api'

export default function Profile({ wallet }) {
  // Tab state - 2 tabs only
  const [activeTab, setActiveTab] = useState('telegram') // telegram, gallery
  
  // Telegram state
  const [loading, setLoading] = useState(false)
  const [profileData, setProfileData] = useState(null)
  const [telegramUsername, setTelegramUsername] = useState('')
  const [verificationCode, setVerificationCode] = useState('')
  const [generatedCode, setGeneratedCode] = useState('')
  const [isLinking, setIsLinking] = useState(false)
  const [isVerifying, setIsVerifying] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  
  // Gallery state
  const [tokens, setTokens] = useState([])
  const [tokensLoading, setTokensLoading] = useState(false)
  const [tokensError, setTokensError] = useState(null)

  useEffect(() => {
    if (wallet) {
      loadProfile()
      fetchTokens()
    }
  }, [wallet])

  const loadProfile = async () => {
    try {
      setLoading(true)
      const data = await getProfileInfo(wallet)
      setProfileData(data)
    } catch (err) {
      console.error('Failed to load profile:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchTokens = async () => {
    try {
      setTokensLoading(true)
      setTokensError(null)
      
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const response = await fetch(`${API_URL}/api/rwa/my-tokens/${wallet}`)
      
      if (!response.ok) {
        throw new Error('Failed to fetch tokens')
      }
      
      const data = await response.json()
      setTokens(data.tokens || [])
    } catch (err) {
      console.error('Error fetching tokens:', err)
      setTokensError(err.message)
    } finally {
      setTokensLoading(false)
    }
  }

  const handleLinkTelegram = async () => {
    if (!telegramUsername.trim()) {
      setError('Please enter your Telegram username')
      return
    }

    const username = telegramUsername.trim().replace('@', '')
    setIsLinking(true)
    setError('')
    setSuccess('')

    try {
      const response = await linkTelegram(wallet, username)
      setGeneratedCode(response.code)
      setIsVerifying(true)
      setSuccess(`✅ Code generated! Use it on Telegram: /verify ${response.code}`)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate verification code')
    } finally {
      setIsLinking(false)
    }
  }

  const handleVerifyCode = async () => {
    if (!verificationCode.trim()) {
      setError('Please enter the 6-digit code')
      return
    }

    setLoading(true)
    setError('')

    try {
      await verifyTelegramCode(wallet, verificationCode)
      setSuccess('🎉 Telegram account linked successfully!')
      setIsVerifying(false)
      setTelegramUsername('')
      setVerificationCode('')
      await loadProfile()
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid code. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleUnlink = async () => {
    if (!confirm('Are you sure you want to unlink your Telegram account?')) return
    
    setLoading(true)
    setError('')
    
    try {
      await unlinkTelegram(wallet)
      setSuccess('✅ Telegram account unlinked successfully')
      await loadProfile()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to unlink Telegram account')
    } finally {
      setLoading(false)
    }
  }

  const getAssetIcon = (assetType) => {
    switch (assetType) {
      case 'image':
        return <ImageIcon className="w-6 h-6" />
      case 'music':
        return <Music className="w-6 h-6" />
      case '3d':
        return <Box className="w-6 h-6" />
      default:
        return <ImageIcon className="w-6 h-6" />
    }
  }

  const formatDate = (dateString) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (!wallet) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-900 via-black to-blue-900 pt-20 px-4 flex items-center justify-center">
        <div className="text-center">
          <User className="w-16 h-16 mx-auto mb-4 text-purple-400 opacity-50" />
          <h2 className="text-2xl font-bold text-white mb-2">Connect Wallet First</h2>
          <p className="text-gray-400">Please connect your Casper wallet to view your profile</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-black to-blue-900 pt-20 px-4 pb-20">
      <div className="max-w-6xl mx-auto">
        
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2 flex items-center gap-3">
            <User className="w-10 h-10" />
            My Profile
          </h1>
          <p className="text-gray-400">Manage your account and AI creations</p>
        </div>

        {/* Tab Navigation - Simplified */}
        <div className="flex gap-2 mb-6 bg-gray-900/50 p-2 rounded-lg">
          <button
            onClick={() => setActiveTab('telegram')}
            className={`flex-1 px-6 py-3 rounded-lg font-medium transition ${
              activeTab === 'telegram'
                ? 'bg-purple-600 text-white'
                : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
          >
            <LinkIcon className="w-4 h-4 inline mr-2" />
            Telegram
          </button>
          <button
            onClick={() => setActiveTab('gallery')}
            className={`flex-1 px-6 py-3 rounded-lg font-medium transition ${
              activeTab === 'gallery'
                ? 'bg-purple-600 text-white'
                : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
          >
            <ImageIcon className="w-4 h-4 inline mr-2" />
            My Gallery ({tokens.length})
          </button>
        </div>

        {/* Tab Content */}
        {activeTab === 'telegram' && (
          <div className="space-y-6">
            {/* Wallet Info */}
            <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-6">
              <h2 className="text-xl font-bold text-white mb-4">🔐 Wallet</h2>
              <div className="flex items-center justify-between">
                <code className="text-sm text-gray-300">{wallet.substring(0, 20)}...{wallet.substring(wallet.length - 20)}</code>
                <span className="text-green-400 text-sm">Connected</span>
              </div>
            </div>

            {/* Telegram Integration */}
            <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-6">
              <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <LinkIcon className="w-6 h-6" />
                Telegram Integration
              </h2>

              {loading && !isLinking ? (
                <div className="flex items-center gap-2 text-gray-400">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Loading...
                </div>
              ) : profileData?.telegram_username ? (
                <div>
                  <div className="flex items-center gap-3 mb-4">
                    <CheckCircle className="w-6 h-6 text-green-400" />
                    <div>
                      <p className="font-bold text-white">Linked to Telegram</p>
                      <p className="text-gray-400 text-sm">@{profileData.telegram_username}</p>
                    </div>
                  </div>
                  
                  <p className="text-sm text-gray-400 mb-4">
                    🎉 Your creations sync with <a href="https://t.me/TrappistAI_bot" target="_blank" rel="noopener noreferrer" className="underline hover:text-purple-400">@TrappistAI_bot</a>
                  </p>

                  <button
                    onClick={handleUnlink}
                    className="px-4 py-2 bg-red-500/20 border border-red-500/50 rounded text-red-400 hover:bg-red-500/30 text-sm"
                  >
                    Unlink Account
                  </button>
                </div>
              ) : isVerifying ? (
                <div>
                  <p className="text-white mb-4">
                    ✅ Code generated for <span className="font-bold">@{telegramUsername}</span>
                  </p>
                  
                  <div className="bg-purple-900/30 border-2 border-purple-500/50 rounded-lg p-6 mb-6 text-center">
                    <p className="text-sm text-gray-400 mb-2">Your verification code:</p>
                    <p className="text-4xl font-bold tracking-widest text-purple-400 mb-4">{generatedCode}</p>
                    <p className="text-sm text-gray-300">
                      Go to <a href="https://t.me/TrappistAI_bot" target="_blank" rel="noopener noreferrer" className="underline hover:text-purple-400 font-bold">@TrappistAI_bot</a> and type:
                    </p>
                    <code className="inline-block mt-2 px-4 py-2 bg-black border border-purple-500/30 rounded text-purple-400">
                      /verify {generatedCode}
                    </code>
                  </div>

                  <div className="flex gap-3">
                    <button
                      onClick={async () => {
                        setLoading(true)
                        const updated = await getProfileInfo(wallet)
                        if (updated.telegram_verified) {
                          setSuccess('🎉 Telegram account linked successfully!')
                          setIsVerifying(false)
                          setTelegramUsername('')
                          setGeneratedCode('')
                        } else {
                          setError('Not verified yet. Please type /verify ' + generatedCode + ' on @TrappistAI_bot')
                        }
                        setLoading(false)
                      }}
                      disabled={loading}
                      className="flex-1 px-4 py-3 bg-purple-600 rounded hover:bg-purple-700 disabled:opacity-50 text-white font-bold"
                    >
                      {loading ? (
                        <span className="flex items-center justify-center gap-2">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Checking...
                        </span>
                      ) : (
                        'Check Status'
                      )}
                    </button>
                    
                    <button
                      onClick={() => {
                        setIsVerifying(false)
                        setGeneratedCode('')
                        setError('')
                        setSuccess('')
                      }}
                      className="px-4 py-3 border border-gray-700 rounded hover:border-gray-600 text-white"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  <p className="text-sm text-gray-400 mb-4">
                    Link your Telegram account to sync with <a href="https://t.me/TrappistAI_bot" target="_blank" rel="noopener noreferrer" className="underline hover:text-purple-400">@TrappistAI_bot</a>
                  </p>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm text-gray-300 mb-2">Telegram Username</label>
                      <input
                        type="text"
                        value={telegramUsername}
                        onChange={(e) => setTelegramUsername(e.target.value)}
                        placeholder="@your_username"
                        className="w-full px-4 py-3 bg-black border border-gray-700 rounded text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
                      />
                    </div>

                    <button
                      onClick={handleLinkTelegram}
                      disabled={!telegramUsername.trim() || isLinking}
                      className="w-full px-4 py-3 bg-purple-600 rounded hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold flex items-center justify-center gap-2"
                    >
                      {isLinking ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Sending code...
                        </>
                      ) : (
                        <>
                          <LinkIcon className="w-4 h-4" />
                          Link Telegram Account
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}

              {error && (
                <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded text-red-400 text-sm flex items-start gap-2">
                  <X className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  {error}
                </div>
              )}
              
              {success && (
                <div className="mt-4 p-3 bg-green-500/10 border border-green-500/30 rounded text-green-400 text-sm flex items-start gap-2">
                  <CheckCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  {success}
                </div>
              )}
            </div>

            {/* Info */}
            <div className="p-4 bg-purple-900/20 border border-purple-500/20 rounded text-sm text-gray-300">
              <p className="mb-2">ℹ️ <strong className="text-white">Why link Telegram?</strong></p>
              <ul className="list-disc list-inside space-y-1 ml-2 text-gray-400">
                <li>Generate AI content directly from Telegram</li>
                <li>Save items to your gallery instantly</li>
                <li>Share creations with community</li>
              </ul>
            </div>
          </div>
        )}

        {activeTab === 'gallery' && (
          <div>
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-white mb-2">📁 My Gallery</h2>
              <p className="text-gray-400">All your AI creations saved from Telegram</p>
            </div>

            {tokensLoading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
              </div>
            ) : tokens.length === 0 ? (
              <div className="text-center py-20">
                <ImageIcon className="w-16 h-16 mx-auto mb-4 text-gray-600" />
                <h3 className="text-xl font-bold text-white mb-2">No items in gallery</h3>
                <p className="text-gray-400 mb-4">
                  Generate AI content on Telegram and save it to your gallery!
                </p>
                <a
                  href="https://t.me/TrappistAI_bot"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium"
                >
                  <ExternalLink className="w-4 h-4" />
                  Open @TrappistAI_bot
                </a>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {tokens.map((token) => (
                  <div key={token.tokenId} className="bg-gray-900/50 border border-gray-800 rounded-lg overflow-hidden hover:border-purple-500/50 transition">
                    {/* Asset Preview */}
                    {token.assetType === 'image' && (
                      <img src={token.assetUrl} alt="Asset" className="w-full h-48 object-cover" />
                    )}
                    {token.assetType === 'music' && (
                      <div className="w-full h-48 bg-gradient-to-br from-purple-900/50 to-blue-900/50 flex items-center justify-center">
                        <Music className="w-16 h-16 text-purple-400" />
                      </div>
                    )}
                    {token.assetType === '3d' && (
                      <div className="w-full h-48 bg-gradient-to-br from-blue-900/50 to-cyan-900/50 flex items-center justify-center">
                        <Box className="w-16 h-16 text-cyan-400" />
                      </div>
                    )}

                    <div className="p-4">
                      <div className="flex items-center gap-2 mb-2">
                        {getAssetIcon(token.assetType)}
                        <h3 className="font-bold text-white capitalize">{token.assetType} #{token.tokenId}</h3>
                      </div>
                      
                      <div className="text-sm text-gray-400 mb-3 flex items-center gap-2">
                        <Calendar className="w-3 h-3" />
                        {formatDate(token.createdAt)}
                      </div>

                      {token.prompt && (
                        <p className="text-xs text-gray-500 mb-3 line-clamp-2">{token.prompt}</p>
                      )}

                      <a
                        href={token.assetUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="w-full px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded text-sm text-center block"
                      >
                        View Full Size
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
