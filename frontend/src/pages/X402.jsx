import SEO from '../components/SEO'

export default function X402() {
  return (
    <div className="container mx-auto px-4 py-12 max-w-4xl">
      <SEO
        title="x402 AI Generator - Pay for AI with CSPR | TrappistAI"
        description="Discover how TrappistAI uses the x402 payment protocol to let you pay for AI image, music and 3D generation with native CSPR on Casper blockchain."
        keywords="x402, x402 protocol, AI generator crypto, pay for AI with CSPR, Casper blockchain AI, crypto AI image generator, x402 payments"
      />

      <article className="prose prose-invert max-w-none">
        <h1 className="text-4xl md:text-5xl font-bold text-green-400 mb-6">
          x402 AI Generator: Pay for AI with CSPR
        </h1>

        <p className="text-lg text-green-200/80 mb-8">
          TrappistAI is the first multi-modal AI generation platform to integrate the{' '}
          <strong className="text-green-300">x402 payment protocol</strong>. Generate images,
          music, 3D models and chat with AI — then pay programmatically with native CSPR tokens on
          the Casper blockchain.
        </p>

        <section className="mb-12">
          <h2 className="text-2xl font-semibold text-green-300 mb-4">What is x402?</h2>
          <p className="text-green-200/70 mb-4">
            x402 is an HTTP standard that turns payment into a native web primitive. Instead of
            asking users to send tokens manually, an x402-protected resource returns{' '}
            <code className="bg-green-900/40 px-2 py-1 rounded">402 Payment Required</code>. The
            client signs a blockchain payment, resends the request with the proof, and receives the
            resource instantly.
          </p>
          <p className="text-green-200/70">
            For AI services, x402 means a developer can call an API, pay with crypto, and get a
            generation back in a single flow — no subscription, no credit card, no custody.
          </p>
        </section>

        <section className="mb-12">
          <h2 className="text-2xl font-semibold text-green-300 mb-4">
            Why use TrappistAI as your x402 AI generator?
          </h2>
          <ul className="space-y-3 text-green-200/70 list-disc pl-5">
            <li>
              <strong>Multi-modal AI</strong> — images (FLUX.1-schnell), music (HeartMuLa, MiniMax),
              3D models (Hunyuan, Tripo3D) and chat.
            </li>
            <li>
              <strong>Native CSPR payments</strong> — powered by Casper mainnet, settled
              on-chain.
            </li>
            <li>
              <strong>No manual billing</strong> — the protocol handles pricing, verification and
              settlement automatically.
            </li>
            <li>
              <strong>Live USD to CSPR conversion</strong> — prices are converted using CoinGecko,
              Kraken, CryptoCompare or CoinMarketCap fallbacks.
            </li>
            <li>
              <strong>Developer-friendly</strong> — standard HTTP headers, base64 JSON payloads,
              receipt proofs.
            </li>
          </ul>
        </section>

        <section className="mb-12">
          <h2 className="text-2xl font-semibold text-green-300 mb-4">How it works</h2>
          <ol className="space-y-3 text-green-200/70 list-decimal pl-5">
            <li>
              Send a request to <code className="bg-green-900/40 px-2 py-1 rounded">POST /api/v1/agent/generate/image</code>.
            </li>
            <li>
              Receive <code className="bg-green-900/40 px-2 py-1 rounded">402 Payment Required</code>{' '}
              with a <code className="bg-green-900/40 px-2 py-1 rounded">PAYMENT-REQUIRED</code>{' '}
              header containing the price in CSPR.
            </li>
            <li>
              Sign a native CSPR transfer to the receiver wallet using your Casper wallet or SDK.
            </li>
            <li>
              Resend the request with the signed deploy in the{' '}
              <code className="bg-green-900/40 px-2 py-1 rounded">PAYMENT-SIGNATURE</code> header.
            </li>
            <li>
              The server verifies, settles on-chain and returns your AI-generated asset plus a{' '}
              <code className="bg-green-900/40 px-2 py-1 rounded">PAYMENT-RESPONSE</code> receipt.
            </li>
          </ol>
        </section>

        <section className="mb-12">
          <h2 className="text-2xl font-semibold text-green-300 mb-4">Try the example</h2>
          <pre className="bg-black/50 border border-green-500/30 rounded-lg p-4 overflow-x-auto text-sm text-green-200/80">
{`# Step 1: get the 402 challenge
curl -i -X POST https://trappist.land/api/v1/agent/generate/image \\
  -H "Content-Type: application/json" \\
  -d '{"prompt":"a cyberpunk cat","wallet":"YOUR_WALLET_PUBKEY"}'

# Step 2: sign the CSPR transfer, then resend with the proof
curl -X POST https://trappist.land/api/v1/agent/generate/image \\
  -H "Content-Type: application/json" \\
  -H "PAYMENT-SIGNATURE: BASE64_ENCODED_SIGNED_DEPLOY" \\
  -d '{"prompt":"a cyberpunk cat","wallet":"YOUR_WALLET_PUBKEY"}'`}
          </pre>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-green-300 mb-4">Start building</h2>
          <p className="text-green-200/70">
            Read the full agent reference at{' '}
            <a
              href="/docs/API_AGENT_X402.md"
              className="text-green-400 underline hover:text-green-300"
            >
              docs/API_AGENT_X402.md
            </a>{' '}
            or explore the open-source code on{' '}
            <a
              href="https://github.com/UnrealNFT/TrappistAI"
              target="_blank"
              rel="noopener noreferrer"
              className="text-green-400 underline hover:text-green-300"
            >
              GitHub
            </a>
            .
          </p>
        </section>
      </article>
    </div>
  )
}
