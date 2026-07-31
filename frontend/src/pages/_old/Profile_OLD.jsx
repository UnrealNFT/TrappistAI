import { useState, useEffect } from 'react'
import { User, Link, CheckCircle, X, Loader2, ExternalLink } from 'lucide-react'
import { getProfileInfo, linkTelegram, verifyTelegramCode, unlinkTelegram } from '../services/api'

export default function Profile({ wallet }) {
  const [loading, setLoading] = useState(false)
  const [profileData, setProfileData] = useState(null)
  const [telegramUsername, setTelegramUsername] = useState('')
  const [verificationCode, setVerificationCode] = useState('')
  const [generatedCode, setGeneratedCode] = useState('')
  const [isLinking, setIsLinking] = useState(false)
  const [isVerifying, setIsVerifying] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    if (wallet) {
      loadProfile()
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

  const handleLinkTelegram = async () => {
    if (!telegramUsername.trim()) {
      setError('Please enter your Telegram username')
      return
    }

    // Remove @ if user included it
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

  if (!wallet) {
    return (
      <div className="min-h-screen bg-black text-green-400 flex items-center justify-center p-8">
        <div className="text-center">
          <User className="w-16 h-16 mx-auto mb-4 opacity-50" />
          <h2 className="text-2xl font-bold mb-2">Connect Wallet First</h2>
          <p className="text-green-400/60">Please connect your Casper wallet to view your profile</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-black text-green-400 p-8">
      <div className="max-w-2xl mx-auto">
        
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2 flex items-center gap-3">
            <User className="w-10 h-10" />
            Profile
          </h1>
          <p className="text-green-400/60">Manage your TrappistAI account</p>
        </div>

        {/* Wallet Info */}
        <div className="bg-green-500/5 border border-green-500/20 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-bold mb-4">🔐 Wallet</h2>
          <div className="flex items-center justify-between">
            <code className="text-sm">{wallet}</code>
            <span className="text-green-400/60 text-sm">Connected</span>
          </div>
        </div>

        {/* Telegram Linking */}
        <div className="bg-green-500/5 border border-green-500/20 rounded-lg p-6">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <Link className="w-6 h-6" />
            Telegram Integration
          </h2>

          {loading && !isLinking ? (
            <div className="flex items-center gap-2 text-green-400/60">
              <Loader2 className="w-4 h-4 animate-spin" />
              Loading...
            </div>
          ) : profileData?.telegram_username ? (
            // Already linked
            <div>
              <div className="flex items-center gap-3 mb-4">
                <CheckCircle className="w-6 h-6 text-green-400" />
                <div>
                  <p className="font-bold">Linked to Telegram</p>
                  <p className="text-green-400/60 text-sm">@{profileData.telegram_username}</p>
                </div>
              </div>
              
              <p className="text-sm text-green-400/60 mb-4">
                🎉 Your generations will sync with <a href="https://t.me/PiranAI_bot" target="_blank" rel="noopener noreferrer" className="underline hover:text-green-400">@PiranAI_bot</a>
              </p>

              <button
                onClick={handleUnlink}
                className="px-4 py-2 bg-red-500/20 border border-red-500/50 rounded text-red-400 hover:bg-red-500/30 text-sm"
              >
                Unlink Account
              </button>
            </div>
          ) : isVerifying ? (
            // Enter verification code
            <div>
              <p className="text-green-400/80 mb-4">
                ✅ Code generated for <span className="font-bold">@{telegramUsername}</span>
              </p>
              
              {/* Display the generated code */}
              <div className="bg-green-500/10 border-2 border-green-500/50 rounded-lg p-6 mb-6 text-center">
                <p className="text-sm text-green-400/60 mb-2">Your verification code:</p>
                <p className="text-4xl font-bold tracking-widest text-green-400 mb-4">{generatedCode}</p>
                <p className="text-sm text-green-400/80">
                  Go to <a href="https://t.me/PiraAi_bot" target="_blank" rel="noopener noreferrer" className="underline hover:text-green-400 font-bold">@PiraAi_bot</a> and type:
                </p>
                <code className="inline-block mt-2 px-4 py-2 bg-black border border-green-500/30 rounded text-green-400">
                  /verify {generatedCode}
                </code>
              </div>
              
              <p className="text-sm text-green-400/60 mb-4">
                After verifying on Telegram, click "Check Status" below.
              </p>

              <div className="flex gap-3">
                <button
                  onClick={async () => {
                    setLoading(true)
                    await loadProfile()
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
                  className="flex-1 px-4 py-3 bg-green-500/20 border border-green-500/50 rounded hover:bg-green-500/30 disabled:opacity-50 disabled:cursor-not-allowed font-bold"
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
                  className="px-4 py-3 border border-green-500/30 rounded hover:border-green-500/50"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            // Enter username
            <div>
              <p className="text-sm text-green-400/60 mb-4">
                Link your Telegram account to sync your generations with <a href="https://t.me/PiranAI_bot" target="_blank" rel="noopener noreferrer" className="underline hover:text-green-400">@PiranAI_bot</a>
              </p>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm mb-2">Telegram Username</label>
                  <input
                    type="text"
                    value={telegramUsername}
                    onChange={(e) => setTelegramUsername(e.target.value)}
                    placeholder="@your_username"
                    className="w-full px-4 py-3 bg-black border border-green-500/30 rounded focus:outline-none focus:border-green-500"
                  />
                </div>

                <button
                  onClick={handleLinkTelegram}
                  disabled={!telegramUsername.trim() || isLinking}
                  className="w-full px-4 py-3 bg-green-500/20 border border-green-500/50 rounded hover:bg-green-500/30 disabled:opacity-50 disabled:cursor-not-allowed font-bold flex items-center justify-center gap-2"
                >
                  {isLinking ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Sending code...
                    </>
                  ) : (
                    <>
                      <Link className="w-4 h-4" />
                      Link Telegram Account
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Error/Success Messages */}
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

        {/* Info Box */}
        <div className="mt-6 p-4 bg-green-500/5 border border-green-500/10 rounded text-sm text-green-400/60">
          <p className="mb-2">ℹ️ <strong>Why link Telegram?</strong></p>
          <ul className="list-disc list-inside space-y-1 ml-2">
            <li>Receive notifications when generations complete</li>
            <li>Access your generations from both website and Telegram</li>
            <li>Unified experience across platforms</li>
          </ul>
        </div>

      </div>
    </div>
  )
}
