/**
 * x402 Payment Flow — Option B (native CSPR, TESTNET)
 *
 * x402 here = an HTTP envelope (402 challenge + on-chain proof receipt) around a
 * native CSPR transfer to the SAME treasury wallet as the manual flow, but on
 * the Casper TESTNET. No CEP-18 token, no external facilitator.
 *
 * Flow:
 *  1. GET  /api/buy-credits-x402            -> HTTP 402 + PAYMENT-REQUIRED header
 *  2. Build a native CSPR transfer deploy on `casper-test`, sign with wallet
 *  3. POST /api/buy-credits-x402            -> PAYMENT-SIGNATURE header (base64)
 *  4. Backend settles on testnet, credits tokens, returns PAYMENT-RESPONSE receipt
 */

import { useState, useEffect } from 'react'
import { Wallet, Loader2, CheckCircle, XCircle, AlertCircle, ExternalLink, Zap } from 'lucide-react'
import { CLPublicKey, DeployUtil } from 'casper-js-sdk'
import toast from 'react-hot-toast'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// TESTNET configuration (native CSPR, same treasury wallet as manual payment)
const X402_CONFIG = {
  chainName: 'casper-test',
  paymentAmount: '100000000', // 0.1 CSPR gas (motes)
}

export default function BuyCreditsX402({ wallet, balance, provider, onPurchaseComplete }) {
  const [requirement, setRequirement] = useState(null)
  const [loadingInfo, setLoadingInfo] = useState(true)
  const [paying, setPaying] = useState(false)
  const [verifying, setVerifying] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [receipt, setReceipt] = useState(null)

  useEffect(() => {
    loadPaymentInfo()
  }, [])

  const loadPaymentInfo = async () => {
    setLoadingInfo(true)
    setError('')
    try {
      const response = await fetch(`${API_URL}/api/buy-credits-x402`)
      if (response.status !== 402) {
        throw new Error(`Expected HTTP 402, got ${response.status}`)
      }
      const header = response.headers.get('payment-required') || response.headers.get('PAYMENT-REQUIRED')
      const info = header ? JSON.parse(atob(header)) : await response.json()
      const accepted = info.accepts?.[0]
      if (!accepted) throw new Error('No accepted payment option returned')
      setRequirement(accepted)
    } catch (e) {
      console.error('x402 load info error:', e)
      setError(`Failed to load payment info: ${e.message}`)
    } finally {
      setLoadingInfo(false)
    }
  }

  const formatCspr = (motes) => {
    if (!motes || !/^\d+$/.test(String(motes))) return `${motes} CSPR`
    return `${(Number(motes) / 1_000_000_000).toLocaleString()} CSPR`
  }

  const handlePay = async () => {
    if (!wallet || !provider) {
      setError('Please connect your wallet first.')
      return
    }
    if (!requirement) {
      setError('Payment information not loaded.')
      return
    }

    setPaying(true)
    setError('')
    setSuccess(false)
    setReceipt(null)

    try {
      const amountMotes = String(requirement.amount)

      // Ensure wallet is connected
      const isConnected = await provider.isConnected()
      if (!isConnected) throw new Error('Wallet not connected. Please reconnect.')

      const senderPublicKey = CLPublicKey.fromHex(wallet)
      const receiverPublicKey = CLPublicKey.fromHex(requirement.payTo)

      // Build a native CSPR transfer deploy on TESTNET
      const deployParams = new DeployUtil.DeployParams(
        senderPublicKey,
        X402_CONFIG.chainName, // 'casper-test'
        1,
        1800000
      )
      // On-chain marker: transfer-id starts with 402 so the payment is
      // recognizable as an x402 purchase on the explorer.
      const transferId = Number('402' + String(Date.now()).slice(-12))
      const transferArgs = DeployUtil.ExecutableDeployItem.newTransfer(
        amountMotes,
        receiverPublicKey,
        null,
        transferId
      )
      const payment = DeployUtil.standardPayment(X402_CONFIG.paymentAmount)
      const deploy = DeployUtil.makeDeploy(deployParams, transferArgs, payment)
      const deployJSON = DeployUtil.deployToJson(deploy)

      // Request signature
      const signedResult = await provider.sign(JSON.stringify(deployJSON), wallet)
      if (!signedResult || signedResult.cancelled) {
        throw new Error('Payment cancelled')
      }

      // Assemble signed deploy JSON
      const signatureHex = Array.from(signedResult.signature)
        .map((b) => b.toString(16).padStart(2, '0'))
        .join('')
      const deployJson = DeployUtil.deployToJson(deploy)
      deployJson.deploy.header.account = deployJson.deploy.header.account.toLowerCase()
      const keyPrefix = wallet.substring(0, 2) // 01 = ED25519, 02 = SECP256K1
      deployJson.deploy.approvals = [
        {
          signer: senderPublicKey.toHex().toLowerCase(),
          signature: keyPrefix + signatureHex,
        },
      ]

      setPaying(false)
      setVerifying(true)

      // Build x402 PAYMENT-SIGNATURE payload (base64 JSON)
      const paymentPayload = { deployJson, wallet }
      const paymentSignature = btoa(JSON.stringify(paymentPayload))

      const settleResponse = await fetch(`${API_URL}/api/buy-credits-x402`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'PAYMENT-SIGNATURE': paymentSignature,
        },
      })

      const data = await settleResponse.json().catch(() => ({}))

      if (settleResponse.ok && data.success) {
        setReceipt(data.receipt || null)
        setSuccess(true)
        setVerifying(false)
        toast.success(`✅ x402 settled! +${data.tokens} credits`)
        setTimeout(() => {
          onPurchaseComplete && onPurchaseComplete()
        }, 2000)
      } else if (settleResponse.status === 202 && data.pending) {
        setVerifying(false)
        setError('Payment sent but testnet confirmation is pending. Wait ~1 min and refresh.')
      } else {
        setVerifying(false)
        throw new Error(data.detail || data.message || 'Payment failed')
      }
    } catch (e) {
      console.error('x402 payment error:', e)
      setPaying(false)
      setVerifying(false)
      setError(e.message || 'Payment failed')
      toast.error(e.message || 'Payment failed')
    }
  }

  return (
    <div className="min-h-screen bg-dark-bg py-12 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-2 flex items-center justify-center gap-2">
            <Zap className="text-purple-400" /> x402 Payment
          </h1>
          <p className="text-slate-300">
            Pay with native CSPR via the x402 protocol — on{' '}
            <span className="text-yellow-400 font-semibold">Casper Testnet</span>.
          </p>
        </div>

        {/* Testnet notice */}
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4 mb-6 flex items-start gap-3">
          <AlertCircle className="text-yellow-400 flex-shrink-0 mt-0.5" size={20} />
          <div className="text-sm text-yellow-100">
            This uses the <strong>Casper Testnet</strong>. Switch your wallet to a
            testnet account and fund it with the{' '}
            <a
              href="https://testnet.cspr.live/tools/faucet"
              target="_blank"
              rel="noopener noreferrer"
              className="underline text-yellow-300"
            >
              testnet faucet
            </a>
            . No real funds are used.
          </div>
        </div>

        {/* Payment details */}
        <div className="bg-white/5 border border-white/10 rounded-xl p-6 mb-6">
          <h2 className="text-lg font-bold text-white mb-4">Payment Details</h2>
          {loadingInfo ? (
            <div className="flex items-center gap-2 text-slate-400">
              <Loader2 className="animate-spin" size={18} /> Loading requirements...
            </div>
          ) : requirement ? (
            <div className="space-y-3 text-sm">
              <Row label="Network" value={requirement.network} />
              <Row label="Amount" value={formatCspr(requirement.amount)} />
              <Row label="Credits" value={`${requirement.extra?.tokens ?? 100} generation credits`} />
              {requirement.extra?.memo && <Row label="Memo" value={requirement.extra.memo} />}
              <Row
                label="Receiver"
                value={`${requirement.payTo.slice(0, 16)}...${requirement.payTo.slice(-6)}`}
                mono
              />
            </div>
          ) : (
            <div className="text-red-400 text-sm">Could not load payment requirements.</div>
          )}
        </div>

        {/* Wallet status */}
        {!wallet && (
          <div className="bg-white/5 border border-white/10 rounded-xl p-4 mb-6 flex items-center gap-2 text-slate-300 text-sm">
            <Wallet size={18} /> Connect your wallet (top-right) and switch it to a testnet account.
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mb-6 flex items-start gap-2 text-red-200 text-sm">
            <XCircle size={18} className="flex-shrink-0 mt-0.5" /> {error}
          </div>
        )}

        {/* Success + receipt */}
        {success && (
          <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-2 text-green-300 font-semibold mb-2">
              <CheckCircle size={18} /> x402 payment settled on testnet!
            </div>
            {receipt && (
              <div className="text-xs text-green-100 space-y-1">
                <div>Tokens credited: {requirement?.extra?.tokens ?? 100}</div>
                {receipt.explorer && (
                  <a
                    href={receipt.explorer}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 underline text-green-300"
                  >
                    View proof on testnet explorer <ExternalLink size={12} />
                  </a>
                )}
              </div>
            )}
          </div>
        )}

        {/* Pay button */}
        <button
          onClick={handlePay}
          disabled={!wallet || !requirement || paying || verifying || success}
          className="w-full bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 disabled:opacity-50 text-white font-bold py-4 px-6 rounded-xl transition-all disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {paying ? (
            <>
              <Loader2 className="animate-spin" size={18} /> Signing...
            </>
          ) : verifying ? (
            <>
              <Loader2 className="animate-spin" size={18} /> Settling on testnet...
            </>
          ) : (
            <>
              <Zap size={18} /> Pay with x402
            </>
          )}
        </button>
      </div>
    </div>
  )
}

function Row({ label, value, mono }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-slate-400">{label}</span>
      <span className={`text-white text-right ${mono ? 'font-mono text-xs break-all' : ''}`}>{value}</span>
    </div>
  )
}
