import { Link } from 'react-router-dom'
import { Image, Music, Box, MessageSquare, Sparkles } from 'lucide-react'

export default function Home() {
  return (
    <div className="container mx-auto px-4 py-16">
      {/* Hero */}
      <div className="text-center mb-16">
        <h1 className="text-6xl font-bold text-white mb-4">
          Create with <span className="gradient-text">AI</span>
        </h1>
        <p className="text-white/80 text-xl mb-8">
          Generate images, music, 3D models, and chat with AI
        </p>
        <p className="text-white/60 mb-8">
          Powered by Casper blockchain • Pay with CSPR
        </p>
        
        <div className="flex justify-center space-x-4">
          <Link
            to="/generate"
            className="bg-gradient-to-r from-purple-500 to-pink-500 px-8 py-3 rounded-lg text-white font-semibold hover:scale-105 transition"
          >
            Start Creating
          </Link>
          <Link
            to="/buy-credits"
            className="bg-white/20 backdrop-blur-md px-8 py-3 rounded-lg text-white font-semibold hover:bg-white/30 transition"
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
            cost: "5-20 tokens"
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
            className="bg-white/10 backdrop-blur-md p-6 rounded-xl border border-white/20 hover:bg-white/20 transition"
          >
            <div className="text-purple-300 mb-4">{feature.icon}</div>
            <h3 className="text-white font-semibold text-lg mb-2">{feature.title}</h3>
            <p className="text-white/70 text-sm mb-3">{feature.description}</p>
            <div className="flex items-center space-x-1 text-yellow-300 text-sm">
              <Sparkles className="w-4 h-4" />
              <span>{feature.cost}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Package Starter Only */}
      <div className="mt-16 text-center">
        <h2 className="text-3xl font-bold text-white mb-8">Simple Pricing</h2>
        <div className="flex justify-center">
          <div className="bg-gradient-to-br from-purple-500/30 to-pink-500/30 border border-purple-400 shadow-lg shadow-purple-500/50 p-8 rounded-xl max-w-sm">
            <div className="text-purple-300 text-sm font-semibold mb-2">✨ PACKAGE UNIQUE</div>
            <h3 className="text-white font-bold text-3xl mb-4">Starter</h3>
            <p className="text-white/70 text-5xl font-bold mb-2">100</p>
            <p className="text-white/60 text-lg mb-6">tokens</p>
            <div className="border-t border-white/20 pt-6">
              <p className="text-purple-300 font-bold text-4xl">10 CSPR</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
