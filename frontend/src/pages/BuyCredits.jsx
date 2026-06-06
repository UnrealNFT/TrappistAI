import { useState } from 'react'
import { Wallet, Loader2, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import api from '../services/api'

const PACKAGES = [
  { name: 'Starter', tokens: 100, cspr: 10, popular: true }
]

const RECEIVER_WALLET = import.meta.env.VITE_RECEIVER_WALLET || 'account-hash-0123456789abcdef0123456789abcdef01234567'

export default function BuyCredits({ wallet, balance, onRefreshBalance }) {
  const [selected, setSelected] = useState(null)
  const [paying, setPaying] = useState(false)
  const [verifying, setVerifying] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [txHash, setTxHash] = useState('')

  const handlePayWithWallet = async () => {
    if (!wallet) {
      setError('Please connect your wallet first')
      return
    }

    if (!window.casperlabsHelper) {
      setError('Casper Wallet extension not found. Please install it from casperwallet.io')
      window.open('https://www.casperwallet.io/', '_blank')
      return
    }

    setPaying(true)
    setError('')
    setSuccess(false)

    try {
      console.log('Initiating payment:', selected.cspr, 'CSPR')
      
      // Amount in motes (1 CSPR = 1,000,000,000 motes)
      const amountMotes = selected.cspr * 1_000_000_000

      // Create deploy for transfer
      const deployParams = {
        amount: amountMotes.toString(),
        target: RECEIVER_WALLET,
        transferId: Date.now()
      }

      console.log('Deploy params:', deployParams)

      // Request signature from Casper Wallet
      const result = await window.casperlabsHelper.signAndDeploy(
        deployParams.amount,
        deployParams.target,
        deployParams.transferId
      )

      console.log('Payment result:', result)

      if (result && result.deployHash) {
        const deployHash = result.deployHash
        console.log('Deploy hash:', deployHash)
        setTxHash(deployHash)

        // Wait a bit then verify
        setVerifying(true)
        setPaying(false)

        // Give the blockchain time to process (5 seconds)
        await new Promise(resolve => setTimeout(resolve, 5000))

        try {
          await api.verifyPayment(wallet, deployHash, selected.cspr)
          setSuccess(true)
          setVerifying(false)
          
          // Refresh balance and reset after success
          setTimeout(() => {
            onRefreshBalance()
            setSelected(null)
            setTxHash('')
            setSuccess(false)
          }, 3000)
        } catch (verifyErr) {
          console.error('Verification error:', verifyErr)
          setError(`Payment sent but verification pending. Your transaction: ${deployHash}. Tokens will be credited automatically within 1-2 minutes.`)
          setVerifying(false)
        }
      } else {
        throw new Error('No deploy hash returned from wallet')
      }

    } catch (err) {
      console.error('Payment error:', err)
      setError(err.message || 'Payment cancelled or failed. Please try again.')
      setPaying(false)
      setVerifying(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-900 p-6">
      <div className="container mx-auto max-w-4xl">
        <h1 className="text-5xl font-bold text-white mb-4 text-center">Buy Credits</h1>
        <p className="text-white/70 text-center text-lg mb-12">
          Pay with Casper Wallet - Instant & Secure
        </p>

        {/* Package */}
        <div className="flex justify-center mb-12">
          {PACKAGES.map((pkg, i) => (
            <div
              key={i}
              onClick={() => setSelected(pkg)}
              className={`cursor-pointer p-8 rounded-2xl border-2 transition-all transform hover:scale-105 max-w-sm ${
                selected?.name === pkg.name
                  ? 'bg-gradient-to-br from-purple-500/40 to-pink-500/40 border-purple-400 shadow-2xl shadow-purple-500/50 scale-105'
                  : 'bg-white/10 backdrop-blur-md border-white/30 hover:bg-white/15'
              }`}
            >
              {pkg.popular && (
                <div className="text-purple-300 text-sm font-bold mb-3 flex items-center gap-2">
                  ✨ POPULAR CHOICE
                </div>
              )}
              <h3 className="text-white font-bold text-3xl mb-4">{pkg.name}</h3>
              <p className="text-white/80 text-6xl font-bold mb-2">{pkg.tokens}</p>
              <p className="text-white/60 text-lg mb-6">tokens</p>
              <div className="border-t border-white/30 pt-6">
                <p className="text-purple-300 font-bold text-4xl">{pkg.cspr} CSPR</p>
              </div>
            </div>
          ))}
        </div>

        {/* Payment Section */}
        {selected && (
          <div className="bg-white/10 backdrop-blur-xl p-8 rounded-2xl border border-white/20 shadow-2xl">
            <h2 className="text-3xl font-bold text-white mb-6">
              Complete Payment: {selected.name}
            </h2>

            {!wallet ? (
              <div className="text-center py-12 bg-gradient-to-r from-purple-500/20 to-pink-500/20 rounded-xl border border-purple-400/30">
                <AlertCircle className="w-16 h-16 text-purple-300 mx-auto mb-4" />
                <p className="text-white text-lg mb-6">Please connect your Casper Wallet to continue</p>
                <button
                  onClick={() => window.location.href = '/'}
                  className="bg-gradient-to-r from-purple-500 to-pink-500 text-white font-bold px-8 py-4 rounded-lg hover:shadow-lg hover:shadow-purple-500/50 transition-all"
                >
                  Connect Wallet
                </button>
              </div>
            ) : (
              <>
                {/* Payment Info */}
                <div className="mb-8 bg-gradient-to-r from-purple-500/10 to-pink-500/10 p-6 rounded-xl border border-purple-400/30">
                  <div className="flex justify-between items-center mb-4">
                    <span className="text-white/80 text-lg">Amount to pay:</span>
                    <span className="text-4xl font-bold text-white">{selected.cspr} CSPR</span>
                  </div>
                  <div className="flex justify-between items-center mb-4">
                    <span className="text-white/80 text-lg">You will receive:</span>
                    <span className="text-3xl font-bold text-purple-300">{selected.tokens} tokens</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-white/80">Your wallet:</span>
                    <span className="text-sm text-white/90 font-mono bg-black/30 px-3 py-1 rounded">
                      {wallet.slice(0, 12)}...{wallet.slice(-8)}
                    </span>
                  </div>
                </div>

                {/* Status Messages */}
                {error && (
                  <div className="mb-6 p-4 bg-red-500/20 border-2 border-red-500/50 rounded-xl flex items-start gap-3">
                    <XCircle className="w-6 h-6 text-red-300 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-red-300 font-semibold mb-1">Error</p>
                      <p className="text-red-200 text-sm">{error}</p>
                    </div>
                  </div>
                )}
                
                {success && (
                  <div className="mb-6 p-4 bg-green-500/20 border-2 border-green-500/50 rounded-xl flex items-start gap-3">
                    <CheckCircle className="w-6 h-6 text-green-300 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-green-300 font-bold text-lg">Payment Successful! 🎉</p>
                      <p className="text-green-200 text-sm mt-1">✅ {selected.tokens} tokens have been credited to your account</p>
                    </div>
                  </div>
                )}

                {txHash && !success && (
                  <div className="mb-6 p-4 bg-blue-500/20 border-2 border-blue-500/50 rounded-xl">
                    <p className="text-blue-300 font-semibold mb-2">Transaction Submitted</p>
                    <p className="text-blue-200 text-xs mb-2">Deploy Hash:</p>
                    <code className="text-blue-100 text-xs break-all block bg-black/30 p-2 rounded">{txHash}</code>
                  </div>
                )}

                {/* Pay Button */}
                <button
                  onClick={handlePayWithWallet}
                  disabled={paying || verifying || success}
                  className="w-full bg-gradient-to-r from-purple-500 to-pink-500 text-white font-bold py-5 rounded-xl text-lg hover:shadow-2xl hover:shadow-purple-500/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3 mb-6"
                >
                  {paying ? (
                    <>
                      <Loader2 className="w-6 h-6 animate-spin" />
                      <span>Waiting for wallet approval...</span>
                    </>
                  ) : verifying ? (
                    <>
                      <Loader2 className="w-6 h-6 animate-spin" />
                      <span>Verifying payment...</span>
                    </>
                  ) : success ? (
                    <>
                      <CheckCircle className="w-6 h-6" />
                      <span>Payment Complete!</span>
                    </>
                  ) : (
                    <>
                      <Wallet className="w-6 h-6" />
                      <span>Pay {selected.cspr} CSPR with Casper Wallet</span>
                    </>
                  )}
                </button>

                {/* Info Box */}
                <div className="p-4 bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-400/30 rounded-xl">
                  <p className="text-purple-200 text-sm leading-relaxed">
                    💡 <strong>How it works:</strong> Click the button above and approve the transaction in your Casper Wallet extension. Your tokens will be credited automatically within seconds!
                  </p>
                </div>

                {/* Help Link */}
                <div className="mt-6 text-center">
                  <p className="text-white/60 text-sm">
                    Need help?{' '}
                    <a
                      href="https://cspr.live/"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-purple-300 hover:text-purple-200 underline font-semibold"
                    >
                      View on CSPR.live →
                    </a>
                  </p>
                </div>
              </>
            )}
          </div>
        )}

        {/* Info Notice */}
        <div className="mt-8 text-center">
          <p className="text-white/50 text-sm">
            💡 Your tokens will be credited automatically within 1-2 minutes after payment confirmation.
          </p>
        </div>
      </div>
    </div>
  )
}
