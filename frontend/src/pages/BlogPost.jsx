import { useParams, Link } from 'react-router-dom'
import SEO from '../components/SEO'

const POSTS = {
  'what-is-x402-ai-payments': {
    title: 'What is x402 and How to Pay for AI with CSPR',
    description:
      'Discover the x402 payment protocol and how TrappistAI uses it to let developers pay for AI image, music and 3D generation with native CSPR tokens.',
    keywords:
      'x402 protocol, pay for AI with crypto, CSPR payments, AI agent payments, Casper blockchain',
    content: `
      <h1>What is x402 and How to Pay for AI with CSPR</h1>

      <p>The internet runs on HTTP. Yet, until recently, there was no standard way for a server to say "pay me" and for a client to prove it paid. <strong>x402</strong> fixes that by turning payment into a native HTTP primitive.</p>

      <p>x402 is a protocol that uses the <code>402 Payment Required</code> status code to request payment, and a cryptographic signature to prove it. It works with any asset, any chain, and any wallet that can sign transactions.</p>

      <h2>Why x402 matters for AI</h2>
      <p>AI APIs are usually billed with credit cards, subscriptions or API keys. These systems are slow, require identity, and are hard to automate. x402 lets an AI agent request a generation, pay with crypto, and receive the result in a single HTTP flow.</p>

      <h2>How TrappistAI uses x402</h2>
      <p>TrappistAI is a multi-modal AI generation platform. Users can generate images, music, 3D models and chat with AI. With x402, developers can pay for these generations using <strong>native CSPR tokens</strong> on the Casper blockchain.</p>

      <p>The flow is simple:</p>
      <ol>
        <li>The client sends a request to <code>/api/v1/agent/generate/image</code>.</li>
        <li>The server replies with <code>402 Payment Required</code> and a <code>PAYMENT-REQUIRED</code> header containing the price in CSPR.</li>
        <li>The client signs a CSPR transfer and resends the request with the proof in the <code>PAYMENT-SIGNATURE</code> header.</li>
        <li>The server verifies the signature, settles the payment on-chain and returns the generated asset.</li>
      </ol>

      <h2>Benefits of paying for AI with CSPR</h2>
      <ul>
        <li><strong>No subscription</strong> — pay per generation</li>
        <li><strong>No custody</strong> — you keep control of your wallet</li>
        <li><strong>Programmable</strong> — perfect for AI agents and backend services</li>
        <li><strong>Fast settlement</strong> — Casper finalizes transfers quickly</li>
      </ul>

      <p>Ready to try it? Visit the <a href="/x402">x402 AI generator page</a> or read the full API reference on GitHub.</p>
    `,
  },
  'build-ai-agent-x402': {
    title: 'How to Build an AI Agent with x402 Payments',
    description:
      'A step-by-step guide to building an AI agent that requests resources, pays with CSPR, and receives generated content using the x402 protocol.',
    keywords:
      'build AI agent, x402 tutorial, crypto AI agent, CSPR API payments, autonomous AI payments',
    content: `
      <h1>How to Build an AI Agent with x402 Payments</h1>

      <p>Autonomous AI agents need a way to pay for resources without human intervention. Credit cards do not work for machines. The x402 protocol solves this by letting agents negotiate prices and prove payments over standard HTTP.</p>

      <p>In this guide, you will learn how to build an agent that generates images on TrappistAI using CSPR payments.</p>

      <h2>Prerequisites</h2>
      <ul>
        <li>A Casper wallet with CSPR tokens</li>
        <li>Node.js or Python installed</li>
        <li>The TrappistAI backend URL</li>
      </ul>

      <h2>Step 1: Request a generation</h2>
      <p>Send a POST request without payment to receive the 402 challenge:</p>
      <pre><code>curl -i -X POST https://trappist.land/api/v1/agent/generate/image \\
  -H "Content-Type: application/json" \\
  -d '{"prompt":"a futuristic city","wallet":"YOUR_WALLET_PUBKEY"}'</code></pre>

      <p>The response will be <code>402 Payment Required</code> with a base64 <code>PAYMENT-REQUIRED</code> header.</p>

      <h2>Step 2: Decode the challenge</h2>
      <p>Decode the header to get the amount in motes, the receiver wallet and the resource URL.</p>

      <h2>Step 3: Sign the transfer</h2>
      <p>Use the Casper JS SDK to create and sign a native transfer deploy from your wallet to the receiver.</p>

      <h2>Step 4: Send the proof</h2>
      <p>Base64-encode the signed deploy and resend the request with the <code>PAYMENT-SIGNATURE</code> header.</p>
      <pre><code>curl -X POST https://trappist.land/api/v1/agent/generate/image \\
  -H "Content-Type: application/json" \\
  -H "PAYMENT-SIGNATURE: BASE64_ENCODED_DEPLOY" \\
  -d '{"prompt":"a futuristic city","wallet":"YOUR_WALLET_PUBKEY"}'</code></pre>

      <h2>Step 5: Receive the result</h2>
      <p>If the payment is valid, the server settles it on-chain and returns the generated image URL in the response body.</p>

      <h2>Next steps</h2>
      <p>Automate this flow in your agent, handle retries, and cache receipts for idempotency. Read the <a href="https://github.com/UnrealNFT/TrappistAI/blob/main/docs/API_AGENT_X402.md">full API reference</a> for details.</p>
    `,
  },
  'ai-generation-casper-blockchain': {
    title: 'AI Generation on Casper Blockchain: A Complete Guide',
    description:
      'Learn how TrappistAI combines multi-modal AI generation with Casper blockchain payments to create a decentralized creative platform.',
    keywords:
      'AI generation Casper, blockchain AI generator, CSPR AI, decentralized AI, crypto image generator',
    content: `
      <h1>AI Generation on Casper Blockchain: A Complete Guide</h1>

      <p>Artificial intelligence and blockchain are two of the most transformative technologies of the decade. TrappistAI brings them together by offering multi-modal AI generation — images, music, 3D models and chat — paid for with CSPR on the Casper blockchain.</p>

      <h2>What is TrappistAI?</h2>
      <p>TrappistAI is a creative platform where users generate AI content and pay with crypto. It supports image generation with FLUX.1-schnell, music with HeartMuLa and MiniMax, 3D models with Hunyuan and Tripo3D, and conversational AI with Groq.</p>

      <h2>Why Casper?</h2>
      <p>Casper is a proof-of-stake blockchain designed for enterprise and developer adoption. It offers predictable fees, upgradable smart contracts and a robust account model. These features make it ideal for micropayments and AI agent workflows.</p>

      <h2>Payment options</h2>
      <ul>
        <li><strong>Direct transfer</strong> — send CSPR to the receiver wallet and get credited automatically via WebSocket.</li>
        <li><strong>x402 protocol</strong> — programmable HTTP 402 payments for agents and APIs.</li>
      </ul>

      <h2>From generation to NFT</h2>
      <p>TrappistAI also lets users mint their AI-generated assets as RWA (real-world asset) tokens. Each asset gets an IPFS hash, metadata and fractional shares, turning creations into tradeable digital goods.</p>

      <h2>Conclusion</h2>
      <p>By combining AI generation with Casper payments, TrappistAI creates a permissionless creative economy. Developers can build agents, creators can monetize content, and users keep full control of their wallets.</p>

      <p>Start generating today at <a href="/generate">trappist.land/generate</a>.</p>
    `,
  },
}

export default function BlogPost() {
  const { slug } = useParams()
  const post = POSTS[slug]

  if (!post) {
    return (
      <div className="container mx-auto px-4 py-16 text-center">
        <h1 className="text-3xl font-bold text-green-400 mb-4">Article not found</h1>
        <Link to="/blog" className="text-green-400 hover:text-green-300">
          ← Back to blog
        </Link>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-12 max-w-4xl">
      <SEO title={`${post.title} | TrappistAI`} description={post.description} keywords={post.keywords} />

      <Link to="/blog" className="text-green-400 hover:text-green-300 mb-6 inline-block">
        ← Back to blog
      </Link>

      <article
        className="prose prose-invert max-w-none"
        dangerouslySetInnerHTML={{ __html: post.content }}
      />
    </div>
  )
}
