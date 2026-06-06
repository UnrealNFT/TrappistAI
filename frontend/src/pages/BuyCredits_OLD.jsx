import { useState } from 'react'
import { Check, Loader2, ExternalLink, Copy } from 'lucide-react'
import { verifyPayment } from '../services/api'

const PACKAGES = [
  { name: 'Starter', tokens: 100, cspr: 10, popular: true }
]

const RECEIVER_WALLET = import.meta.env.VITE_RECEIVER_WALLET || '0123456789abcdef0123456789abcdef01234567'

export default function BuyCredits({ wallet, onPurchaseComplete }) {
  const [selectedPackage, setSelectedPackage] = useState(null)
  const [txHash, setTxHash] = useState('')
  const [verifying, setVerifying] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

  const handleSelectPackage = (pkg) => {
    setSelectedPackage(pkg)
    setError(null)
    setSuccess(false)
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    alert('Copied to clipboard!')
  }

  const handleVerify = async () => {
    if (!wallet) {
      alert('Please connect your wallet first')
      return
    }

    if (!txHash.trim()) {
      setError('Please enter transaction hash')
      return
    }

    setVerifying(true)
    setError(null)

    try {
      const result = await verifyPayment(wallet, txHash)
      setSuccess(true)
      setTimeout(() => {
        onPurchaseComplete()
        setSelectedPackage(null)
        setTxHash('')
        setSuccess(false)
      }, 3000)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setVerifying(false)
    }
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold text-white mb-4 text-center">Buy Credits</h1>
      <p className="text-white/70 text-center mb-12">Choose a package and pay with CSPR</p>

      {/* Package */}
      <div className="flex justify-center mb-12">
        {PACKAGES.map((pkg, i) => (
          <div
            key={i}
            onClick={() => handleSelectPackage(pkg)}
            className={`cursor-pointer p-6 rounded-xl border transition hover:scale-105 ${
              selectedPackage?.name === pkg.name
                ? 'bg-gradient-to-br from-purple-500/30 to-pink-500/30 border-purple-400 shadow-lg shadow-purple-500/50'
                : 'bg-white/10 backdrop-blur-md border-white/20 hover:bg-white/20'
            }`}
          >
            {pkg.popular && (
              <div className="text-purple-300 text-sm font-semibold mb-2">✨ POPULAR</div>
            )}
            <h3 className="text-white font-bold text-2xl mb-2">{pkg.name}</h3>
            <p className="text-white/70 text-4xl font-bold mb-2">{pkg.tokens}</p>
            <p className="text-white/60 text-sm mb-4">tokens</p>
            <div className="border-t border-white/20 pt-4">
              <p className="text-purple-300 font-bold text-xl">{pkg.cspr} CSPR</p>
            </div>
            {selectedPackage?.name === pkg.name && (
              <div className="mt-4 flex justify-center">
                <Check className="w-6 h-6 text-green-400" />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Payment Instructions */}
      {selectedPackage && (
        <div className="max-w-2xl mx-auto bg-white/10 backdrop-blur-md p-8 rounded-xl border border-white/20">
          <h2 className="text-2xl font-bold text-white mb-6">
            Complete Payment: {selectedPackage.name}
          </h2>

          {/* Step 1 */}
          <div className="mb-6">
            <div className="flex items-center space-x-2 mb-3">
              <div className="w-8 h-8 bg-purple-500 rounded-full flex items-center justify-center text-white font-bold">
                1
              </div>
              <h3 className="text-white font-semibold text-lg">Send {selectedPackage.cspr} CSPR</h3>
            </div>
            
            <div className="bg-white/5 p-4 rounded-lg border border-white/20">
              <p className="text-white/70 text-sm mb-2">Receiver Address:</p>
              <div className="flex items-center space-x-2">
                <code className="text-white font-mono text-sm break-all bg-black/30 p-2 rounded flex-1">
                  {RECEIVER_WALLET}
                </code>
                <button
                  onClick={() => copyToClipboard(RECEIVER_WALLET)}
                  className="p-2 bg-purple-500/20 hover:bg-purple-500/30 rounded transition"
                >
                  <Copy className="w-4 h-4 text-white" />
                </button>
              </div>
            </div>

            <div className="mt-4 flex items-start space-x-2 text-yellow-300 text-sm">
              <span>⚠️</span>
              <p>Send exactly {selectedPackage.cspr} CSPR to avoid payment errors</p>
            </div>
          </div>

          {/* Step 2 */}
          <div className="mb-6">
            <div className="flex items-center space-x-2 mb-3">
              <div className="w-8 h-8 bg-purple-500 rounded-full flex items-center justify-center text-white font-bold">
                2
              </div>
              <h3 className="text-white font-semibold text-lg">Enter Transaction Hash</h3>
            </div>
            
            <input
              type="text"
              value={txHash}
              onChange={(e) => setTxHash(e.target.value)}
              placeholder="Paste your transaction hash here..."
              className="w-full p-3 rounded-lg bg-white/10 border border-white/20 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>

          {/* Verify Button */}
          <button
            onClick={handleVerify}
            disabled={verifying || success}
            className="w-full bg-gradient-to-r from-purple-500 to-pink-500 px-8 py-3 rounded-lg text-white font-semibold hover:scale-105 transition disabled:opacity-50 disabled:hover:scale-100 flex items-center justify-center space-x-2"
          >
            {verifying ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Verifying...</span>
              </>
            ) : success ? (
              <>
                <Check className="w-5 h-5" />
                <span>Payment Confirmed!</span>
              </>
            ) : (
              <span>Verify Payment</span>
            )}
          </button>

          {/* Error */}
          {error && (
            <div className="mt-4 p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-white">
              {error}
            </div>
          )}

          {/* Success */}
          {success && (
            <div className="mt-4 p-4 bg-green-500/20 border border-green-500/50 rounded-lg text-white">
              ✅ {selectedPackage.tokens} tokens have been credited to your account!
            </div>
          )}

          {/* Help */}
          <div className="mt-6 pt-6 border-t border-white/20">
            <p className="text-white/60 text-sm mb-2">Need help?</p>
            <a
              href="https://cspr.live/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-purple-300 hover:text-purple-200 text-sm flex items-center space-x-1"
            >
              <span>View on CSPR.live</span>
              <ExternalLink className="w-4 h-4" />
            </a>
          </div>
        </div>
      )}

      {/* Auto-credit info */}
      {!selectedPackage && (
        <div className="max-w-2xl mx-auto bg-white/10 backdrop-blur-md p-6 rounded-xl border border-white/20 text-center">
          <p className="text-white/70">
            💡 Your tokens will be credited automatically within 1-2 minutes after payment confirmation.
          </p>
        </div>
      )}
    </div>
  )
}
