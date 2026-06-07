import { useState } from 'react'
import { Wallet, Loader2, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import { CLPublicKey, DeployUtil } from 'casper-js-sdk'

const PACKAGES = [
  { name: 'Starter', tokens: 100, cspr: 1000, popular: true }
]

// 🔥 CONFIGURATION CASPER (à configurer avec ta vraie adresse)
const CASPER_CONFIG = {
  receiverWallet: '0202e5a88e2baf0306484eced583f8642902752668b4b91070dc2abd01d6304d2cd8',
  chainName: 'casper',  // 'casper' pour mainnet, 'casper-test' pour testnet
  paymentAmount: '100000000'  // 0.1 CSPR en motes pour les frais de gas
}

export default function BuyCredits({ wallet, balance, provider, onPurchaseComplete }) {
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

    if (!provider) {
      setError('Wallet provider not available. Please reconnect your wallet.')
      return
    }

    setPaying(true)
    setError('')
    setSuccess(false)

    try {
      console.log('🚀 Initiating payment:', selected.cspr, 'CSPR')
      
      // Montant en motes (1 CSPR = 1,000,000,000 motes)
      const amountMotes = (selected.cspr * 1_000_000_000).toString()
      
      // RÉUTILISER le provider déjà connecté au lieu d'en créer un nouveau
      console.log('✅ Using existing provider')

      // Vérifier la connexion
      const isConnected = await provider.isConnected()
      
      if (!isConnected) {
        throw new Error('Wallet not connected. Please reconnect.')
      }

      console.log('✅ Wallet connected, creating deploy...')

      // Créer les clés publiques
      const senderPublicKey = CLPublicKey.fromHex(wallet)
      const receiverPublicKey = CLPublicKey.fromHex(CASPER_CONFIG.receiverWallet)

      // Créer les paramètres du deploy
      const deployParams = new DeployUtil.DeployParams(
        senderPublicKey,
        CASPER_CONFIG.chainName,
        1,  // gas price
        1800000  // ttl (30 minutes)
      )

      // Créer le transfert avec un ID unique
      const transferId = Date.now()
      const transferArgs = DeployUtil.ExecutableDeployItem.newTransfer(
        amountMotes,
        receiverPublicKey,
        null,
        transferId
      )

      // Payment standard pour les frais de gas
      const payment = DeployUtil.standardPayment(CASPER_CONFIG.paymentAmount)

      // Créer le deploy
      const deploy = DeployUtil.makeDeploy(deployParams, transferArgs, payment)
      const deployJSON = DeployUtil.deployToJson(deploy)

      console.log('📝 Deploy created, requesting signature...')

      // Demander la signature au wallet
      const signedResult = await provider.sign(JSON.stringify(deployJSON), wallet)

      if (!signedResult || signedResult.cancelled) {
        throw new Error('Payment cancelled')
      }

      console.log('✅ Deploy signed!')

      // Calculer le hash du deploy
      const deployHash = Array.from(deploy.hash)
        .map(b => b.toString(16).padStart(2, '0'))
        .join('')

      setTxHash(deployHash)

      // Convertir la signature en hex
      const signatureHex = Array.from(signedResult.signature)
        .map(b => b.toString(16).padStart(2, '0'))
        .join('')

      // Construire le deploy signé complet
      const deployJson = DeployUtil.deployToJson(deploy)
      deployJson.deploy.header.account = deployJson.deploy.header.account.toLowerCase()

      // Déterminer l'algorithme de signature (01 = ED25519, 02 = SECP256K1)
      const keyPrefix = wallet.substring(0, 2)

      // Ajouter l'approbation avec la signature
      deployJson.deploy.approvals = [{
        signer: senderPublicKey.toHex().toLowerCase(),
        signature: keyPrefix + signatureHex
      }]

      console.log('📡 Sending deploy to backend (Step 1)...')
      setPaying(false)
      setVerifying(true)

      // STEP 1: Send deploy to RPC via backend (like ScreenerLand)
      const sendResponse = await fetch(`${import.meta.env.VITE_API_URL}/api/casper/send-deploy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deployJson })
      })

      if (!sendResponse.ok) {
        const errorData = await sendResponse.json()
        throw new Error(errorData.detail || 'Failed to send deploy')
      }

      const sendData = await sendResponse.json()
      const confirmedHash = sendData.deployHash

      console.log('✅ Deploy sent to blockchain:', confirmedHash)
      console.log('🔐 Verifying payment on blockchain (Step 2)...')

      // STEP 2: Verify payment and credit tokens (like ScreenerLand)
      const verifyResponse = await fetch(`${import.meta.env.VITE_API_URL}/api/payment/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet,
          deployHash: confirmedHash,
          amount: selected.cspr,
          tokens: selected.tokens
        })
      })

      const verifyData = await verifyResponse.json()

      if (verifyResponse.ok && verifyData.success) {
        console.log('✅ Payment verified and tokens credited!')
        setSuccess(true)
        setVerifying(false)

        // Refresh balance and reset after success
        setTimeout(() => {
          onPurchaseComplete()
          setSelected(null)
          setTxHash('')
          setSuccess(false)
        }, 3000)
      } else if (verifyData.pending) {
        console.warn('⏳ Payment still pending - starting auto-verification')
        
        // AUTO-VERIFICATION : continue de vérifier automatiquement toutes les 10s
        let attempts = 0
        const maxAttempts = 20 // 20 × 10s = 3 minutes max
        
        const pollInterval = setInterval(async () => {
          attempts++
          console.log(`🔄 Auto-verification attempt ${attempts}/${maxAttempts}...`)
          
          try {
            const retryResponse = await fetch(`${import.meta.env.VITE_API_URL}/api/payment/verify`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                wallet,
                deployHash: confirmedHash,
                amount: selected.cspr,
                tokens: selected.tokens
              })
            })
            
            const retryData = await retryResponse.json()
            
            if (retryResponse.ok && retryData.success) {
              console.log('✅ AUTO-VERIFIED! Tokens credited!')
              clearInterval(pollInterval)
              setSuccess(true)
              setVerifying(false)
              setError('')
              
              // Refresh balance
              setTimeout(() => {
                onPurchaseComplete()
                setSelected(null)
                setTxHash('')
                setSuccess(false)
              }, 3000)
            } else if (attempts >= maxAttempts) {
              // Timeout après 3 minutes
              console.warn('❌ Auto-verification timeout after 3 minutes')
              clearInterval(pollInterval)
              setVerifying(false)
              setError('⏳ Blockchain confirmation is taking longer than usual. Your payment has been sent successfully - please check your balance in 5-10 minutes. Refresh this page to see your updated balance.')
            }
            // Sinon continue de poll
            
          } catch (pollError) {
            console.error('Poll error:', pollError)
            if (attempts >= maxAttempts) {
              clearInterval(pollInterval)
              setVerifying(false)
              setError('Unable to verify payment. Please check your balance in a few minutes.')
            }
          }
        }, 10000) // Toutes les 10 secondes
        
        // Message pendant qu'on poll
        setError('⏳ Waiting for blockchain confirmation... Checking automatically every 10 seconds. Please wait, do not close this page.')

        
      } else {
        throw new Error(verifyData.error || 'Payment verification failed')
      }

    } catch (err) {
      console.error('❌ Payment error:', err)
      setError(err.message || 'Payment failed. Please try again.')
      setPaying(false)
      setVerifying(false)
    }
  }

  return (
    <div className="min-h-screen bg-black p-6">
      <div className="container mx-auto max-w-4xl">
        <h1 className="text-5xl font-bold text-green-400 mb-4 text-center animate-glow">Buy Credits</h1>
        <p className="text-green-300/70 text-center text-lg mb-12">
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
                  ? 'glass border-green-400 shadow-2xl shadow-green-500/50 scale-105'
                  : 'glass border-green-500/30 hover:border-green-400/50'
              }`}
            >
              {pkg.popular && (
                <div className="text-green-400 text-sm font-bold mb-3 flex items-center gap-2 animate-blink">
                  ✨ POPULAR CHOICE
                </div>
              )}
              <h3 className="text-green-300 font-bold text-3xl mb-4">{pkg.name}</h3>
              <p className="text-green-400 text-6xl font-bold mb-2">{pkg.tokens}</p>
              <p className="text-green-300/60 text-lg mb-6">tokens</p>
              <div className="border-t border-green-500/30 pt-6">
                <p className="text-green-400 font-bold text-4xl">{pkg.cspr} CSPR</p>
              </div>
            </div>
          ))}
        </div>

        {/* Payment Section */}
        {selected && (
          <div className="glass p-8 rounded-2xl border border-green-500/30 shadow-2xl shadow-green-500/20">
            <h2 className="text-3xl font-bold text-green-400 mb-6">
              Complete Payment: {selected.name}
            </h2>

            {!wallet ? (
              <div className="text-center py-12 glass rounded-xl border border-green-500/30">
                <AlertCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
                <p className="text-green-300 text-lg mb-6">Please connect your Casper Wallet to continue</p>
                <button
                  onClick={() => window.location.href = '/'}
                  className="bg-green-500 text-black font-bold px-8 py-4 rounded-lg hover:shadow-lg hover:shadow-green-500/50 transition-all hover:bg-green-400"
                >
                  Connect Wallet
                </button>
              </div>
            ) : (
              <>
                {/* Payment Info */}
                <div className="mb-8 glass p-6 rounded-xl border border-green-500/30">
                  <div className="flex justify-between items-center mb-4">
                    <span className="text-green-300/80 text-lg">Amount to pay:</span>
                    <span className="text-4xl font-bold text-green-400">{selected.cspr} CSPR</span>
                  </div>
                  <div className="flex justify-between items-center mb-4">
                    <span className="text-green-300/80 text-lg">You will receive:</span>
                    <span className="text-3xl font-bold text-green-400">{selected.tokens} tokens</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-green-300/80">Your wallet:</span>
                    <span className="text-sm text-green-300 font-mono bg-black/30 px-3 py-1 rounded">
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
                  <div className="mb-6 p-4 glass border-2 border-green-500/50 rounded-xl">
                    <p className="text-green-400 font-semibold mb-2">Transaction Submitted</p>
                    <p className="text-green-300 text-xs mb-2">Deploy Hash:</p>
                    <code className="text-green-400 text-xs break-all block bg-black/30 p-2 rounded">{txHash}</code>
                    <a
                      href={`https://cspr.live/deploy/${txHash}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-green-400 hover:text-green-300 underline text-sm mt-2 inline-block"
                    >
                      View on CSPR.live →
                    </a>
                  </div>
                )}

                {/* Pay Button */}
                <button
                  onClick={handlePayWithWallet}
                  disabled={paying || verifying || success}
                  className="w-full bg-green-500 text-black font-bold py-5 rounded-xl text-lg hover:shadow-2xl hover:shadow-green-500/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3 mb-6 hover:bg-green-400"
                >
                  {paying ? (
                    <>
                      <Loader2 className="w-6 h-6 animate-spin" />
                      <span>Waiting for wallet approval...</span>
                    </>
                  ) : verifying ? (
                    <>
                      <Loader2 className="w-6 h-6 animate-spin" />
                      <span>Verifying payment on blockchain...</span>
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
                <div className="p-4 glass border border-green-500/30 rounded-xl">
                  <p className="text-green-300 text-sm leading-relaxed">
                    💡 <strong>How it works:</strong> Click the button above to sign the transaction with your Casper Wallet. We'll verify the payment on the blockchain and credit your tokens automatically!
                  </p>
                </div>

                {/* Help Link */}
                <div className="mt-6 text-center">
                  <p className="text-green-300/60 text-sm">
                    Need help?{' '}
                    <a
                      href="https://cspr.live/"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-green-400 hover:text-green-300 underline font-semibold"
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
          <p className="text-green-300/50 text-sm">
            💡 Your tokens will be credited instantly after blockchain confirmation.
          </p>
        </div>
      </div>
    </div>
  )
}
