import { useState, useEffect } from 'react'
import { User, Link as LinkIcon, CheckCircle, X, Loader2, ExternalLink, Gem, Image as ImageIcon, Music, Box, Calendar, Hash } from 'lucide-react'
import { getProfileInfo, linkTelegram, verifyTelegramCode, unlinkTelegram } from '../services/api'

export default function Profile({ wallet }) {
  // Tab state - simplified to 2 tabs
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
  
  // Gallery state - removed RWA/tokenize state
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

  // Only gallery items (removed RWA separation)
  const galleryItems = tokens

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

  const handleTokenizeClick = (token) => {
    setSelectedToken(token)
    setCustomMode(false)
    setCustomParts('')
    setTokenizeForm({ partsForSale: 100, pricePerPart: 10 })
    setShowTokenizeModal(true)
  }

  const handleTokenizeSubmit = async () => {
    if (!selectedToken || !wallet) return

    try {
      setTokenizeLoading(true)
      
      alert(
        `🔜 Casper Wallet Integration Coming Soon!\n\n` +
        `You will tokenize:\n` +
        `• Token #${selectedToken.tokenId}\n` +
        `• ${tokenizeForm.partsForSale.toLocaleString()} total parts\n` +
        `• Type: ${selectedToken.assetType}\n\n` +
        `For now, your items are saved in the gallery. Real blockchain minting coming in Phase C!`
      )
      
      setShowTokenizeModal(false)
    } catch (err) {
      console.error('Tokenize error:', err)
      alert('❌ ' + err.message)
    } finally {
      setTokenizeLoading(false)
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
        return <Gem className="w-6 h-6" />
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
          <p className="text-gray-400">Manage your account, assets, and blockchain tokens</p>
        </div>

        {/* Tab Navigation */}
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
            Gallery ({galleryItems.length})
          </button>
          <button
            onClick={() => setActiveTab('rwa')}
            className={`flex-1 px-6 py-3 rounded-lg font-medium transition ${
              activeTab === 'rwa'
                ? 'bg-purple-600 text-white'
                : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
          >
            <Gem className="w-4 h-4 inline mr-2" />
            My RWA ({rwaItems.length})
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
                    🎉 Your generations sync with <a href="https://t.me/PiraAi_bot" target="_blank" rel="noopener noreferrer" className="underline hover:text-purple-400">@PiraAi_bot</a>
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
                      Go to <a href="https://t.me/PiraAi_bot" target="_blank" rel="noopener noreferrer" className="underline hover:text-purple-400 font-bold">@PiraAi_bot</a> and type:
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
                          setError('Not verified yet. Please type /verify ' + generatedCode + ' on @PiraAi_bot')
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
                    Link your Telegram account to sync with <a href="https://t.me/PiraAi_bot" target="_blank" rel="noopener noreferrer" className="underline hover:text-purple-400">@PiraAi_bot</a>
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
                <li>Unified experience across platforms</li>
              </ul>
            </div>
          </div>
        )}

        {activeTab === 'gallery' && (
          <div>
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-white mb-2">📁 My Gallery</h2>
              <p className="text-gray-400">Items saved from Telegram. Click "Tokenize" to mint on Casper blockchain.</p>
            </div>

            {tokensLoading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
              </div>
            ) : galleryItems.length === 0 ? (
              <div className="text-center py-20">
                <ImageIcon className="w-16 h-16 mx-auto mb-4 text-gray-600" />
                <h3 className="text-xl font-bold text-white mb-2">No items in gallery</h3>
                <p className="text-gray-400 mb-4">
                  Generate AI content on Telegram and save it to your gallery!
                </p>
                <a
                  href="https://t.me/PiraAi_bot"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium"
                >
                  <ExternalLink className="w-4 h-4" />
                  Open @PiraAi_bot
                </a>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {galleryItems.map((token) => (
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
                        <h3 className="font-bold text-white">Item #{token.tokenId}</h3>
                      </div>
                      
                      <div className="text-sm text-gray-400 mb-3 space-y-1">
                        <div className="flex items-center gap-2">
                          <Calendar className="w-3 h-3" />
                          {formatDate(token.createdAt)}
                        </div>
                        <div className="flex items-center gap-2">
                          <Hash className="w-3 h-3" />
                          {token.totalShares?.toLocaleString() || 100} parts
                        </div>
                      </div>

                      {token.prompt && (
                        <p className="text-xs text-gray-500 mb-3 line-clamp-2">{token.prompt}</p>
                      )}

                      <div className="flex gap-2">
                        <a
                          href={token.assetUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex-1 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded text-sm text-center"
                        >
                          View
                        </a>
                        <button
                          onClick={() => handleTokenizeClick(token)}
                          className="flex-1 px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded text-sm font-medium"
                        >
                          💎 Tokenize
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'rwa' && (
          <div>
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-white mb-2">💎 My RWA Tokens</h2>
              <p className="text-gray-400">Tokenized assets on Casper blockchain. Ready to list on marketplace.</p>
            </div>

            {tokensLoading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
              </div>
            ) : rwaItems.length === 0 ? (
              <div className="text-center py-20">
                <Gem className="w-16 h-16 mx-auto mb-4 text-gray-600" />
                <h3 className="text-xl font-bold text-white mb-2">No RWA tokens yet</h3>
                <p className="text-gray-400 mb-4">
                  Tokenize items from your gallery to create on-chain RWA NFTs!
                </p>
                <button
                  onClick={() => setActiveTab('gallery')}
                  className="inline-flex items-center gap-2 px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium"
                >
                  Go to Gallery
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {rwaItems.map((token) => (
                  <div key={token.tokenId} className="bg-gray-900/50 border border-green-500/30 rounded-lg overflow-hidden hover:border-green-500/50 transition">
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
                        <Gem className="w-5 h-5 text-green-400" />
                        <h3 className="font-bold text-white">RWA #{token.tokenId}</h3>
                        <span className="ml-auto text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded">On-chain</span>
                      </div>
                      
                      <div className="text-sm text-gray-400 mb-3 space-y-1">
                        <div className="flex items-center gap-2">
                          <Calendar className="w-3 h-3" />
                          {formatDate(token.createdAt)}
                        </div>
                        <div className="flex items-center gap-2">
                          <Hash className="w-3 h-3" />
                          {token.totalShares?.toLocaleString() || 100} parts
                        </div>
                      </div>

                      {token.prompt && (
                        <p className="text-xs text-gray-500 mb-3 line-clamp-2">{token.prompt}</p>
                      )}

                      <div className="flex gap-2">
                        <a
                          href={token.assetUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex-1 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded text-sm text-center"
                        >
                          View
                        </a>
                        {token.cspr_tx_hash && (
                          <a
                            href={`https://cspr.live/deploy/${token.cspr_tx_hash}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex-1 px-3 py-2 bg-green-600 hover:bg-green-700 text-white rounded text-sm flex items-center justify-center gap-1"
                          >
                            <ExternalLink className="w-3 h-3" />
                            Explorer
                          </a>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Tokenize Modal */}
      {showTokenizeModal && selectedToken && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50">
          <div className="bg-gray-900 border border-gray-800 rounded-lg max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-white">💎 Tokenize on Casper</h2>
                <button
                  onClick={() => setShowTokenizeModal(false)}
                  className="text-gray-400 hover:text-white"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              <p className="text-gray-400 text-sm mb-6">
                Create fractional ownership NFT on Casper blockchain
              </p>

              <div className="space-y-4">
                {/* Parts Selection */}
                <div>
                  <label className="block text-white font-medium mb-3">
                    Choose Total Parts
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => {
                        setCustomMode(false)
                        setTokenizeForm({ ...tokenizeForm, partsForSale: 100 })
                      }}
                      className={`px-4 py-3 rounded-lg border-2 transition ${
                        !customMode && tokenizeForm.partsForSale === 100
                          ? 'border-purple-500 bg-purple-500/20'
                          : 'border-gray-700 hover:border-gray-600'
                      }`}
                    >
                      <div className="text-white font-bold">100</div>
                      <div className="text-xs text-gray-400">1% per part</div>
                    </button>
                    <button
                      onClick={() => {
                        setCustomMode(false)
                        setTokenizeForm({ ...tokenizeForm, partsForSale: 1000 })
                      }}
                      className={`px-4 py-3 rounded-lg border-2 transition ${
                        !customMode && tokenizeForm.partsForSale === 1000
                          ? 'border-purple-500 bg-purple-500/20'
                          : 'border-gray-700 hover:border-gray-600'
                      }`}
                    >
                      <div className="text-white font-bold">1,000</div>
                      <div className="text-xs text-gray-400">0.1% per part</div>
                    </button>
                    <button
                      onClick={() => {
                        setCustomMode(false)
                        setTokenizeForm({ ...tokenizeForm, partsForSale: 10000 })
                      }}
                      className={`px-4 py-3 rounded-lg border-2 transition ${
                        !customMode && tokenizeForm.partsForSale === 10000
                          ? 'border-purple-500 bg-purple-500/20'
                          : 'border-gray-700 hover:border-gray-600'
                      }`}
                    >
                      <div className="text-white font-bold">10,000</div>
                      <div className="text-xs text-gray-400">0.01% per part</div>
                    </button>
                    <button
                      onClick={() => {
                        setCustomMode(true)
                        setCustomParts('')
                      }}
                      className={`px-4 py-3 rounded-lg border-2 transition ${
                        customMode
                          ? 'border-purple-500 bg-purple-500/20'
                          : 'border-gray-700 hover:border-gray-600'
                      }`}
                    >
                      <div className="text-white font-bold">Custom</div>
                      <div className="text-xs text-gray-400">Your choice</div>
                    </button>
                  </div>
                  
                  {customMode && (
                    <div className="mt-3 space-y-2">
                      <input
                        type="number"
                        min="1"
                        max="1000000000"
                        value={customParts}
                        onChange={(e) => {
                          const value = e.target.value
                          setCustomParts(value)
                          if (value && parseInt(value) > 0) {
                            setTokenizeForm({ ...tokenizeForm, partsForSale: parseInt(value) })
                          }
                        }}
                        placeholder="e.g., 21000000 for Bitcoin themed NFT"
                        className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:border-purple-500 focus:outline-none"
                      />
                      <p className="text-xs text-gray-400">
                        💡 <span className="text-purple-400">Example:</span> 21,000,000 parts for Bitcoin 3D model
                      </p>
                    </div>
                  )}
                  
                  <p className="text-gray-500 text-xs mt-2">
                    More parts = better liquidity for marketplace trading
                  </p>
                </div>

                {/* Info Box */}
                <div className="bg-purple-900/30 border border-purple-500/30 rounded-lg p-4">
                  <h3 className="text-white font-semibold mb-2">📝 What happens next?</h3>
                  <ul className="text-sm text-gray-300 space-y-1">
                    <li>• Casper Wallet will open for signature</li>
                    <li>• Real on-chain transaction on Casper Network</li>
                    <li>• NFT will be viewable on cspr.live explorer</li>
                    <li>• You can list it on marketplace after minting</li>
                  </ul>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowTokenizeModal(false)}
                  className="flex-1 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleTokenizeSubmit}
                  disabled={tokenizeLoading}
                  className="flex-1 px-4 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {tokenizeLoading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      Minting...
                    </>
                  ) : (
                    <>
                      <Gem className="w-4 h-4" />
                      Tokenize & Sign
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
