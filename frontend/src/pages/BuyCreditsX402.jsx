/**
 * x402 Payment Flow with CSPR.click
 * 
 * Based on: https://github.com/make-software/casper-x402/tree/master/go/examples/csprclick-x402
 * 
 * Flow:
 * 1. Fetch payment requirements (HTTP 402)
 * 2. Sign EIP-712 typed data with CSPR.click
 * 3. Submit payment signature
 * 4. Display result
 */

import { useState, useEffect } from 'react'
import { PublicKey } from 'casper-js-sdk'
import toast from 'react-hot-toast'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const DEFAULT_DOMAIN_NAME = 'Wrapped Casper'
const DEFAULT_DOMAIN_VERSION = '1'

export default function BuyCreditsX402() {
  const [activeAccount, setActiveAccount] = useState(null)
  const [paymentInfo, setPaymentInfo] = useState(null)
  const [paymentRequirement, setPaymentRequirement] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState('')
  const [paymentResponse, setPaymentResponse] = useState('')

  // Initialize CSPR.click
  useEffect(() => {
    const scriptId = 'csprclick-script'

    const onSignedIn = async (evt) => {
      console.log('✅ CSPR.click signed in:', evt.account)
      setActiveAccount(evt.account)
    }

    const onSwitchedAccount = async (evt) => {
      console.log('🔄 CSPR.click switched account:', evt.account)
      setActiveAccount(evt.account)
    }

    const onSignedOut = async () => {
      console.log('👋 CSPR.click signed out')
      setActiveAccount(null)
    }

    const onDisconnected = async () => {
      console.log('⚠️ CSPR.click disconnected')
      setActiveAccount(null)
    }

    const addListeners = () => {
      if (window.csprclick) {
        window.csprclick.on('csprclick:signed_in', onSignedIn)
        window.csprclick.on('csprclick:switched_account', onSwitchedAccount)
        window.csprclick.on('csprclick:signed_out', onSignedOut)
        window.csprclick.on('csprclick:disconnected', onDisconnected)
      }
    }

    // Load CSPR.click script if not already loaded
    if (!document.getElementById(scriptId)) {
      const script = document.createElement('script')
      script.id = scriptId
      script.src = 'https://cdn.cspr.click/ui/v2.1.0/csprclick-client-2.1.0.js'
      script.defer = true
      script.onload = addListeners
      document.body.appendChild(script)
    } else {
      addListeners()
    }

    return () => {
      if (window.csprclick) {
        window.csprclick.off('csprclick:signed_in', onSignedIn)
        window.csprclick.off('csprclick:switched_account', onSwitchedAccount)
        window.csprclick.off('csprclick:signed_out', onSignedOut)
        window.csprclick.off('csprclick:disconnected', onDisconnected)
      }
    }
  }, [])

  // Fetch payment requirements on mount
  useEffect(() => {
    loadPaymentInfo()
  }, [])

  const loadPaymentInfo = async () => {
    try {
      console.log('📡 Fetching payment requirements...')
      
      const response = await fetch(`${API_URL}/api/buy-credits-x402`)
      
      // Check for 402 Payment Required
      if (response.status !== 402) {
        throw new Error(`Expected HTTP 402, got ${response.status}`)
      }

      const paymentRequired = response.headers.get('payment-required') || response.headers.get('PAYMENT-REQUIRED')
      
      if (!paymentRequired) {
        throw new Error('Missing PAYMENT-REQUIRED header')
      }

      // Parse base64 JSON
      const decoded = atob(paymentRequired)
      const nextPaymentInfo = JSON.parse(decoded)
      
      console.log('✅ Payment requirements:', nextPaymentInfo)

      const accepted = nextPaymentInfo.accepts[0]
      if (!accepted) {
        throw new Error('No accepted payment options')
      }

      setPaymentInfo(nextPaymentInfo)
      setPaymentRequirement(accepted)
      
    } catch (error) {
      console.error('❌ Error loading payment info:', error)
      toast.error(`Failed to load payment info: ${error.message}`)
      setResult(JSON.stringify({ error: error.message }, null, 2))
    }
  }

  const handlePayment = async () => {
    if (!activeAccount) {
      toast.error('Please sign in with CSPR.click first')
      return
    }

    if (!paymentInfo || !paymentRequirement) {
      toast.error('Payment information not loaded')
      return
    }

    setLoading(true)
    setResult('Requesting signature from CSPR.click...')
    setPaymentResponse('')

    try {
      const publicKey = activeAccount.public_key
      
      // Calculate account hash (00 + blake2b hash of public key)
      const accountHash = '00' + PublicKey.fromHex(publicKey)
        .accountHash()
        .toHex()
        .replace('account-hash-', '')

      // Generate random nonce (32 bytes = 64 hex chars)
      const randomBytes = new Uint8Array(32)
      crypto.getRandomValues(randomBytes)
      const nonce = '0x' + Array.from(randomBytes)
        .map(b => b.toString(16).padStart(2, '0'))
        .join('')

      // Time bounds
      const validAfter = Math.floor(Date.now() / 1000)
      const validBefore = validAfter + 60 * 60 // 1 hour

      // Parse amount to integer
      const value = parseInt(paymentRequirement.amount)

      // Get domain info from extra
      const assetName = paymentRequirement.extra?.name || DEFAULT_DOMAIN_NAME
      const assetVersion = paymentRequirement.extra?.version || DEFAULT_DOMAIN_VERSION

      // Build EIP-712 typed data
      const typedData = {
        domain: {
          name: assetName,
          version: assetVersion,
          chain_name: paymentRequirement.network,
          contract_package_hash: paymentRequirement.asset
        },
        types: {
          TransferWithAuthorization: [
            { name: 'from', type: 'address' },
            { name: 'to', type: 'address' },
            { name: 'value', type: 'uint256' },
            { name: 'validAfter', type: 'uint256' },
            { name: 'validBefore', type: 'uint256' },
            { name: 'nonce', type: 'bytes32' }
          ]
        },
        primaryType: 'TransferWithAuthorization',
        message: {
          from: accountHash,
          to: paymentRequirement.payTo,
          value,
          validAfter,
          validBefore,
          nonce
        }
      }

      console.log('📝 Signing typed data:', typedData)

      // Request signature from CSPR.click
      const signResult = await window.csprclick.signTypedData(
        { typedData, options: { returnHashArtifacts: true } },
        publicKey.toLowerCase()
      )

      if (signResult?.cancelled || signResult?.error) {
        throw new Error(signResult.error || 'Signing cancelled')
      }

      console.log('✅ Signature obtained:', signResult)

      // Build PaymentPayload
      const paymentPayload = {
        x402Version: paymentInfo.x402Version,
        resource: {
          url: paymentInfo.resource.url || '/api/buy-credits-x402'
        },
        accepted: paymentRequirement,
        payload: {
          authorization: {
            from: accountHash,
            to: paymentRequirement.payTo,
            value: paymentRequirement.amount,
            validAfter: validAfter.toString(),
            validBefore: validBefore.toString(),
            nonce: nonce
          },
          publicKey: signResult.publicKey,
          signature: signResult.signatureHex
        }
      }

      console.log('📤 Submitting payment:', paymentPayload)
      setResult('Submitting payment to backend...')

      // Send payment signature
      const paidResponse = await fetch(`${API_URL}/api/buy-credits-x402`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'PAYMENT-SIGNATURE': btoa(JSON.stringify(paymentPayload))
        }
      })

      const responseText = await paidResponse.text()
      let formattedResponse = responseText

      try {
        formattedResponse = JSON.stringify(JSON.parse(responseText), null, 2)
      } catch {
        // Keep non-JSON as-is
      }

      setResult(formattedResponse)

      // Check for PAYMENT-RESPONSE header
      const paymentResponseHeader = paidResponse.headers.get('payment-response') || paidResponse.headers.get('PAYMENT-RESPONSE')
      if (paymentResponseHeader) {
        const decoded = atob(paymentResponseHeader)
        setPaymentResponse(decoded)
      }

      if (paidResponse.ok) {
        toast.success('✅ Payment successful! Tokens credited.')
      } else {
        toast.error('❌ Payment failed')
      }

    } catch (error) {
      console.error('❌ Payment error:', error)
      toast.error(`Payment failed: ${error.message}`)
      setResult(JSON.stringify({ error: error.message }, null, 2))
    } finally {
      setLoading(false)
    }
  }

  const formatAmount = (amount, decimals, symbol) => {
    if (!amount || !/^\d+$/.test(amount)) {
      return `${amount} ${symbol || ''}`
    }

    const parsedDecimals = parseInt(decimals) || 0
    const paddedAmount = amount.padStart(parsedDecimals + 1, '0')
    
    const integerPart = parsedDecimals === 0 
      ? paddedAmount 
      : paddedAmount.slice(0, -parsedDecimals).replace(/^0+(?=\d)/, '') || '0'
    
    const fractionPart = parsedDecimals === 0 
      ? '' 
      : '.' + paddedAmount.slice(-parsedDecimals)
    
    return `${integerPart}${fractionPart} ${symbol || ''}`
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">
            x402 Payment (CSPR.click)
          </h1>
          <p className="text-slate-300">
            Buy 100 tokens for 10 CSPR using x402 protocol
          </p>
        </div>

        {/* CSPR.click Container */}
        <div className="bg-white/10 backdrop-blur-md rounded-lg p-6 mb-6">
          <h2 className="text-xl font-bold text-white mb-4">
            1. Connect Wallet
          </h2>
          <div id="csprclick-connect" className="flex justify-center">
            {/* CSPR.click widget will render here */}
          </div>
          {activeAccount && (
            <div className="mt-4 text-center text-green-400">
              ✅ Connected: {activeAccount.public_key.slice(0, 10)}...
            </div>
          )}
        </div>

        {/* Payment Info */}
        <div className="bg-white/10 backdrop-blur-md rounded-lg p-6 mb-6">
          <h2 className="text-xl font-bold text-white mb-4">
            2. Payment Details
          </h2>
          {paymentRequirement ? (
            <div className="space-y-3 text-sm">
              <div>
                <span className="text-slate-400">Network:</span>
                <span className="text-white ml-2">{paymentRequirement.network}</span>
              </div>
              <div>
                <span className="text-slate-400">Amount:</span>
                <span className="text-white ml-2">
                  {formatAmount(
                    paymentRequirement.amount,
                    paymentRequirement.extra?.decimals,
                    paymentRequirement.extra?.symbol
                  )}
                </span>
              </div>
              <div>
                <span className="text-slate-400">Receiver:</span>
                <span className="text-white ml-2 font-mono text-xs">
                  {paymentRequirement.payTo.slice(0, 20)}...
                </span>
              </div>
              <div>
                <span className="text-slate-400">Tokens:</span>
                <span className="text-white ml-2">100 generation credits</span>
              </div>
            </div>
          ) : (
            <div className="text-slate-400">Loading payment requirements...</div>
          )}
        </div>

        {/* Pay Button */}
        <button
          onClick={handlePayment}
          disabled={!activeAccount || loading || !paymentRequirement}
          className="w-full bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 disabled:from-slate-600 disabled:to-slate-700 text-white font-bold py-4 px-6 rounded-lg transition-all disabled:cursor-not-allowed"
        >
          {loading ? '⏳ Processing...' : '💳 Pay with x402'}
        </button>

        {/* Result */}
        {result && (
          <div className="bg-white/10 backdrop-blur-md rounded-lg p-6 mt-6">
            <h2 className="text-xl font-bold text-white mb-4">
              Result
            </h2>
            <pre className="bg-black/50 text-green-400 p-4 rounded overflow-x-auto text-xs">
              {result}
            </pre>
          </div>
        )}

        {/* Payment Response */}
        {paymentResponse && (
          <div className="bg-white/10 backdrop-blur-md rounded-lg p-6 mt-6">
            <h2 className="text-xl font-bold text-white mb-4">
              Payment Response (x402)
            </h2>
            <pre className="bg-black/50 text-blue-400 p-4 rounded overflow-x-auto text-xs">
              {paymentResponse}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}
