import { useState } from 'react'
import { Image, Music, Box, MessageSquare, Loader2, Download } from 'lucide-react'
import { generateImage, generateMusic, generate3D, chat } from '../services/api'

export default function Generate({ wallet, balance, onBalanceUpdate }) {
  const [tab, setTab] = useState('image')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  // Form states
  const [imagePrompt, setImagePrompt] = useState('')
  const [musicLyrics, setMusicLyrics] = useState('')
  const [musicTags, setMusicTags] = useState('electronic, dark, cinematic')
  const [musicQuality, setMusicQuality] = useState('hm')
  const [chatMessage, setChatMessage] = useState('')
  const [chatHistory, setChatHistory] = useState([])

  const handleGenerate = async () => {
    // TEMPORARY: Use test wallet if not connected
    const walletToUse = wallet || 'test_wallet_01234567890abcdef'
    
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      let res
      
      switch (tab) {
        case 'image':
          if (!imagePrompt.trim()) {
            throw new Error('Please enter a prompt')
          }
          res = await generateImage(walletToUse, imagePrompt)
          setResult({ type: 'image', url: res.url, tokensUsed: res.tokensUsed })
          break

        case 'music':
          if (!musicTags.trim()) {
            throw new Error('Please enter music tags/style')
          }
          res = await generateMusic(walletToUse, musicLyrics, musicTags, musicQuality)
          setResult({ type: 'music', url: res.url, tokensUsed: res.tokensUsed })
          break

        case '3d':
          alert('3D generation coming soon!')
          break

        case 'chat':
          if (!chatMessage.trim()) {
            throw new Error('Please enter a message')
          }
          res = await chat(walletToUse, chatMessage)
          const newHistory = [...chatHistory, 
            { role: 'user', content: chatMessage },
            { role: 'assistant', content: res.response }
          ]
          setChatHistory(newHistory)
          setChatMessage('')
          break
      }

      // Refresh balance
      await onBalanceUpdate()

    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold text-white mb-8 text-center">Generate</h1>

      {/* Tabs */}
      <div className="flex justify-center space-x-2 mb-8">
        {[
          { id: 'image', icon: <Image className="w-5 h-5" />, label: 'Image' },
          { id: 'music', icon: <Music className="w-5 h-5" />, label: 'Music' },
          { id: '3d', icon: <Box className="w-5 h-5" />, label: '3D' },
          { id: 'chat', icon: <MessageSquare className="w-5 h-5" />, label: 'Chat' }
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center space-x-2 px-6 py-3 rounded-lg transition ${
              tab === t.id
                ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white'
                : 'bg-white/10 text-white/70 hover:bg-white/20'
            }`}
          >
            {t.icon}
            <span>{t.label}</span>
          </button>
        ))}
      </div>

      {/* Generator */}
      <div className="max-w-3xl mx-auto bg-white/10 backdrop-blur-md p-8 rounded-xl border border-white/20">
        
        {/* Image */}
        {tab === 'image' && (
          <div className="space-y-4">
            <div>
              <label className="block text-white mb-2 font-semibold">Prompt</label>
              <textarea
                value={imagePrompt}
                onChange={(e) => setImagePrompt(e.target.value)}
                placeholder="A beautiful sunset over mountains..."
                className="w-full p-3 rounded-lg bg-white/10 border border-white/20 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-purple-500"
                rows={4}
              />
            </div>
            <p className="text-white/60 text-sm">Cost: 1 token • FLUX.1-schnell • 1024x1024</p>
          </div>
        )}

        {/* Music */}
        {tab === 'music' && (
          <div className="space-y-4">
            <div>
              <label className="block text-white mb-2 font-semibold">Style / Tags</label>
              <input
                value={musicTags}
                onChange={(e) => setMusicTags(e.target.value)}
                placeholder="electronic, dark, cinematic"
                className="w-full p-3 rounded-lg bg-white/10 border border-white/20 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
            <div>
              <label className="block text-white mb-2 font-semibold">Lyrics (optional)</label>
              <textarea
                value={musicLyrics}
                onChange={(e) => setMusicLyrics(e.target.value)}
                placeholder="Leave empty for instrumental..."
                className="w-full p-3 rounded-lg bg-white/10 border border-white/20 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-purple-500"
                rows={6}
              />
            </div>
            <div>
              <label className="block text-white mb-2 font-semibold">Quality</label>
              <select
                value={musicQuality}
                onChange={(e) => setMusicQuality(e.target.value)}
                className="w-full p-3 rounded-lg bg-white/10 border border-white/20 text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                <option value="hm">HeartMuLa (10 tokens)</option>
                <option value="minimax">MiniMax HD (15 tokens)</option>
              </select>
            </div>
          </div>
        )}

        {/* Chat */}
        {tab === 'chat' && (
          <div className="space-y-4">
            {/* Chat history */}
            <div className="h-64 overflow-y-auto space-y-2 mb-4">
              {chatHistory.length === 0 ? (
                <p className="text-white/50 text-center">Start a conversation...</p>
              ) : (
                chatHistory.map((msg, i) => (
                  <div
                    key={i}
                    className={`p-3 rounded-lg ${
                      msg.role === 'user'
                        ? 'bg-purple-500/20 text-white ml-8'
                        : 'bg-white/10 text-white/90 mr-8'
                    }`}
                  >
                    {msg.content}
                  </div>
                ))
              )}
            </div>
            
            {/* Input */}
            <div>
              <input
                value={chatMessage}
                onChange={(e) => setChatMessage(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleGenerate()}
                placeholder="Type your message..."
                className="w-full p-3 rounded-lg bg-white/10 border border-white/20 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
            <p className="text-white/60 text-sm">Free chat • No tokens consumed</p>
          </div>
        )}

        {/* Generate Button */}
        {tab !== 'chat' && (
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="w-full mt-6 bg-gradient-to-r from-purple-500 to-pink-500 px-8 py-3 rounded-lg text-white font-semibold hover:scale-105 transition disabled:opacity-50 disabled:hover:scale-100 flex items-center justify-center space-x-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Generating...</span>
              </>
            ) : (
              <span>Generate</span>
            )}
          </button>
        )}

        {tab === 'chat' && (
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="w-full mt-6 bg-gradient-to-r from-purple-500 to-pink-500 px-8 py-3 rounded-lg text-white font-semibold hover:scale-105 transition disabled:opacity-50 disabled:hover:scale-100 flex items-center justify-center space-x-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Thinking...</span>
              </>
            ) : (
              <span>Send</span>
            )}
          </button>
        )}

        {/* Error */}
        {error && (
          <div className="mt-4 p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-white">
            {error}
          </div>
        )}

        {/* Result */}
        {result && tab !== 'chat' && (
          <div className="mt-6 space-y-4">
            <div className="text-white/70 text-sm text-center">
              ✨ Generated! Used {result.tokensUsed} tokens
            </div>
            
            {result.type === 'image' && (
              <div>
                <img src={result.url} alt="Generated" className="w-full rounded-lg" />
                <a
                  href={result.url}
                  download
                  className="mt-3 flex items-center justify-center space-x-2 w-full bg-white/10 hover:bg-white/20 px-4 py-2 rounded-lg text-white transition"
                >
                  <Download className="w-4 h-4" />
                  <span>Download</span>
                </a>
              </div>
            )}

            {result.type === 'music' && (
              <div>
                <audio controls className="w-full">
                  <source src={result.url} type="audio/mpeg" />
                </audio>
                <a
                  href={result.url}
                  download
                  className="mt-3 flex items-center justify-center space-x-2 w-full bg-white/10 hover:bg-white/20 px-4 py-2 rounded-lg text-white transition"
                >
                  <Download className="w-4 h-4" />
                  <span>Download</span>
                </a>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
