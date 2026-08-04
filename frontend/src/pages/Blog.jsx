import { Link } from 'react-router-dom'
import SEO from '../components/SEO'

const POSTS = [
  {
    slug: 'what-is-x402-ai-payments',
    title: 'What is x402 and How to Pay for AI with CSPR',
    description:
      'Discover the x402 payment protocol and how TrappistAI uses it to let developers pay for AI image, music and 3D generation with native CSPR tokens.',
    keywords: 'x402 protocol, pay for AI with crypto, CSPR payments, AI agent payments, Casper blockchain',
  },
  {
    slug: 'build-ai-agent-x402',
    title: 'How to Build an AI Agent with x402 Payments',
    description:
      'A step-by-step guide to building an AI agent that requests resources, pays with CSPR, and receives generated content using the x402 protocol.',
    keywords: 'build AI agent, x402 tutorial, crypto AI agent, CSPR API payments, autonomous AI payments',
  },
  {
    slug: 'ai-generation-casper-blockchain',
    title: 'AI Generation on Casper Blockchain: A Complete Guide',
    description:
      'Learn how TrappistAI combines multi-modal AI generation with Casper blockchain payments to create a decentralized creative platform.',
    keywords: 'AI generation Casper, blockchain AI generator, CSPR AI, decentralized AI, crypto image generator',
  },
]

export default function Blog() {
  return (
    <div className="container mx-auto px-4 py-16 max-w-4xl">
      <SEO
        title="TrappistAI Blog - AI, x402 and Casper Blockchain Guides"
        description="Read guides about the x402 payment protocol, AI agent development, and AI generation on the Casper blockchain."
        keywords="AI blog, x402 guide, Casper blockchain AI, crypto AI tutorials, TrappistAI blog"
      />

      <h1 className="text-4xl md:text-5xl font-bold text-green-400 mb-8 text-center">
        TrappistAI Blog
      </h1>
      <p className="text-green-200/70 text-center mb-12 text-lg">
        Guides and tutorials about AI generation, the x402 payment protocol and Casper blockchain.
      </p>

      <div className="grid gap-8">
        {POSTS.map((post) => (
          <article
            key={post.slug}
            className="glass p-6 rounded-xl border border-green-500/30 hover:border-green-400/50 transition"
          >
            <Link to={`/blog/${post.slug}`}>
              <h2 className="text-2xl font-bold text-green-300 mb-3 hover:text-green-400 transition">
                {post.title}
              </h2>
            </Link>
            <p className="text-green-200/60 mb-4">{post.description}</p>
            <Link
              to={`/blog/${post.slug}`}
              className="text-green-400 font-semibold hover:text-green-300 transition"
            >
              Read more →
            </Link>
          </article>
        ))}
      </div>
    </div>
  )
}
