import { Link } from 'react-router-dom'
import { Image, Music, Box, MessageSquare, Sparkles } from 'lucide-react'
import SEO from '../components/SEO'

export default function Home() {
  return (
    <div className="container mx-auto px-4 py-16">
      <SEO
        title="TrappistAI - AI Image, Music & 3D Generator on Casper Blockchain"
        description="Generate images, music, 3D models and chat with AI on TrappistAI. Pay with CSPR tokens on Casper blockchain or via the x402 payment protocol."
        keywords="AI generator, image generator, music generator, 3D model generator, Casper blockchain, CSPR, crypto AI, x402, TrappistAI"
      />

      {/* Hero */}
      <div className="text-center mb-16">
        <h1 className="text-6xl font-bold text-green-400 mb-4">
          Create with <span className="gradient-text">AI</span>
        </h1>
        <p className="text-green-300/80 text-xl mb-8">
          Generate images, music, 3D models, and chat with AI
        </p>
        <p className="text-green-300/60 mb-8">
          Powered by Casper blockchain • Pay with CSPR
        </p>
        
        <div className="flex justify-center space-x-4">
          <Link
            to="/generate"
            className="bg-green-500 text-black px-8 py-3 rounded-lg font-semibold hover:scale-105 transition hover:bg-green-400 hover:shadow-lg hover:shadow-green-500/50"
          >
            Start Creating
          </Link>
          <Link
            to="/buy-credits"
            className="glass border border-green-500/30 px-8 py-3 rounded-lg text-green-300 font-semibold hover:border-green-400/50 transition"
          >
            Buy Credits
          </Link>
        </div>
      </div>

      {/* Features */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          {
            icon: <Image className="w-10 h-10" />,
            title: "Image Generation",
            description: "FLUX.1-schnell • 1024x1024",
            cost: "1 token"
          },
          {
            icon: <Music className="w-10 h-10" />,
            title: "Music Creation",
            description: "HeartMuLa & MiniMax HD",
            cost: "10-15 tokens"
          },
          {
            icon: <Box className="w-10 h-10" />,
            title: "3D Models",
            description: "Hunyuan & Tripo3D",
            cost: "20-30 tokens"
          },
          {
            icon: <MessageSquare className="w-10 h-10" />,
            title: "AI Chat",
            description: "Groq LLM • Free",
            cost: "0 tokens"
          }
        ].map((feature, i) => (
          <div
            key={i}
            className="glass p-6 rounded-xl border border-green-500/30 hover:border-green-400/50 transition"
          >
            <div className="text-green-400 mb-4">{feature.icon}</div>
            <h3 className="text-green-300 font-semibold text-lg mb-2">{feature.title}</h3>
            <p className="text-green-300/70 text-sm mb-3">{feature.description}</p>
            <div className="flex items-center space-x-1 text-yellow-300 text-sm">
              <Sparkles className="w-4 h-4" />
              <span>{feature.cost}</span>
            </div>
          </div>
        ))}
      </div>

      {/* SEO / x402 section */}
      <section className="mt-20 max-w-3xl mx-auto text-center">
        <h2 className="text-3xl font-bold text-green-400 mb-6">
          Programmable AI Payments with x402
        </h2>
        <p className="text-green-200/70 mb-6">
          TrappistAI integrates the x402 protocol so developers can pay for AI image, music and 3D
          generation programmatically with native CSPR. No subscription, no custody — just standard
          HTTP 402 payments settled on the Casper blockchain.
        </p>
        <Link
          to="/x402"
          className="inline-block glass border border-green-500/30 px-8 py-3 rounded-lg text-green-300 font-semibold hover:border-green-400/50 transition"
        >
          Learn about x402 AI generation
        </Link>
      </section>

      {/* Package Starter Only */}
      <div className="mt-16 text-center">
        <h2 className="text-3xl font-bold text-green-400 mb-8">Simple Pricing</h2>
        <div className="flex justify-center">
          <div className="glass border border-green-400 shadow-lg shadow-green-500/50 p-8 rounded-xl max-w-sm">
            <div className="text-green-400 text-sm font-semibold mb-2 animate-blink">✨ PACKAGE UNIQUE</div>
            <h3 className="text-green-300 font-bold text-3xl mb-4">Starter</h3>
            <p className="text-green-400 text-5xl font-bold mb-2">100</p>
            <p className="text-green-300/60 text-lg mb-6">tokens</p>
            <div className="border-t border-green-500/30 pt-6">
              <p className="text-green-400 font-bold text-4xl">1000 CSPR</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
