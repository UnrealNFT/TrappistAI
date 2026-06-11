import { useState, useEffect, useRef } from 'react'
import { Image, Music, Box, MessageSquare, Loader2, Upload, Send, X, Download } from 'lucide-react'
import { generateImage, generateMusic, generate3D, chat } from '../services/api'

export default function Generate({ wallet, balance, onBalanceUpdate }) {
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState([
    {
      id: Date.now(),
      role: 'assistant',
      content: '🎨 **TrappistAI Generator**\n\nWhat would you like to create today?',
      buttons: [
        { label: '🖼️ Generate Image', action: 'start_image' },
        { label: '🎵 Generate Music', action: 'start_music' },
        { label: '🎨 Generate 3D', action: 'start_3d' },
        { label: '💬 Chat', action: 'start_chat' }
      ]
    }
  ])
  
  const [inputValue, setInputValue] = useState('')
  const [currentFlow, setCurrentFlow] = useState(null) // 'image', 'music', '3d', 'chat'
  const [flowData, setFlowData] = useState({}) // Store flow-specific data
  const [uploadedImage, setUploadedImage] = useState(null)
  const [imagePreview, setImagePreview] = useState(null)
  const [showUploadPrompt, setShowUploadPrompt] = useState(false)
  
  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)

  // Auto scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Add message helper
  const addMessage = (role, content, buttons = null, result = null) => {
    setMessages(prev => [...prev, {
      id: Date.now(),
      role,
      content,
      buttons,
      result
    }])
  }

  // Handle button click (inline keyboard)
  const handleButtonClick = async (action) => {
    setLoading(true)

    try {
      switch (action) {
        case 'start_image':
          setCurrentFlow('image')
          addMessage('user', 'Generate Image')
          addMessage('assistant', '📸 **Image Generation**\n\nDescribe what you want to create:', null)
          setShowUploadPrompt(false)
          break

        case 'start_music':
          setCurrentFlow('music')
          addMessage('user', 'Generate Music')
          addMessage('assistant', '🎵 **Music Generation**\n\nChoose quality:', [
            { label: '🎵 HeartMuLa (14 tokens)', action: 'music_hm' },
            { label: '🎶 MiniMax HD (10 tokens)', action: 'music_minimax' }
          ])
          break

        case 'start_3d':
          setCurrentFlow('3d')
          addMessage('user', 'Generate 3D')
          addMessage('assistant', '🎨 **3D Generation**\n\nHow do you want to create?', [
            { label: '🖼️ From Image', action: '3d_from_image' },
            { label: '✍️ From Text (Coming Soon)', action: '3d_from_text' }
          ])
          break

        case 'start_chat':
          setCurrentFlow('chat')
          addMessage('user', 'Chat')
          addMessage('assistant', '💬 **Chat Mode**\n\nAsk me anything! (Free, no tokens)')
          break

        case '3d_from_image':
          setShowUploadPrompt(true)
          addMessage('assistant', '📷 **Upload an Image**\n\nClick the button below to select an image from your device.')
          break

        case '3d_from_text':
          addMessage('assistant', '✍️ Text-to-3D is coming soon! Use "From Image" for now.')
          setTimeout(() => {
            setCurrentFlow(null)
            addMessage('assistant', 'What would you like to create?', [
              { label: '🖼️ Generate Image', action: 'start_image' },
              { label: '🎵 Generate Music', action: 'start_music' },
              { label: '🎨 Generate 3D', action: 'start_3d' },
              { label: '💬 Chat', action: 'start_chat' }
            ])
          }, 2000)
          break

        case 'music_hm':
          setFlowData({ ...flowData, musicQuality: 'hm' })
          addMessage('assistant', '🎵 **HeartMuLa Selected** (14 tokens)\n\nEnter music style/tags:\n_(Example: electronic, dark, cinematic)_')
          break

        case 'music_minimax':
          setFlowData({ ...flowData, musicQuality: 'minimax' })
          addMessage('assistant', '🎶 **MiniMax HD Selected** (10 tokens)\n\nEnter music style/tags:\n_(Example: pop, happy, upbeat)_')
          break

        case '3d_quality_notex':
          await handle3DGeneration(false)
          break

        case '3d_quality_tex':
          await handle3DGeneration(true)
          break

        case 'back_to_menu':
          setCurrentFlow(null)
          setFlowData({})
          setUploadedImage(null)
          setImagePreview(null)
          setShowUploadPrompt(false)
          addMessage('assistant', 'What would you like to create?', [
            { label: '🖼️ Generate Image', action: 'start_image' },
            { label: '🎵 Generate Music', action: 'start_music' },
            { label: '🎨 Generate 3D', action: 'start_3d' },
            { label: '💬 Chat', action: 'start_chat' }
          ])
          break
      }
    } catch (err) {
      addMessage('assistant', `❌ Error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  // Handle image upload
  const handleImageUpload = (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploadedImage(file)
    const reader = new FileReader()
    reader.onload = (e) => {
      setImagePreview(e.target.result)
      setShowUploadPrompt(false)
      
      addMessage('user', '📷 Image uploaded')
      addMessage('assistant', '🎨 **Choose 3D Quality:**\n\n⚡ **Sans texture** — 2 tokens (~2 min)\n   └ Géométrie pure, monochrome\n\n🎨 **Avec texture** — 30 tokens (~5 min)\n   └ Couleurs et textures complètes', [
        { label: '⚡ Sans texture (2 tokens)', action: '3d_quality_notex' },
        { label: '🎨 Avec texture (30 tokens)', action: '3d_quality_tex' },
        { label: '❌ Cancel', action: 'back_to_menu' }
      ])
    }
    reader.readAsDataURL(file)
  }

  // Handle 3D generation
  const handle3DGeneration = async (withTexture) => {
    const walletToUse = wallet || 'test_wallet_01234567890abcdef'
    const cost = withTexture ? 30 : 2
    
    setLoading(true)
    addMessage('user', withTexture ? 'With Texture' : 'Without Texture')
    addMessage('assistant', `🎨 **Génération 3D en cours...**\n_Cost: ${cost} tokens_\n⏳ Peut prendre jusqu'à 5 min`)

    try {
      // TODO: Upload image to backend first
      // For now, use image preview as placeholder
      const res = await generate3D(walletToUse, imagePreview, withTexture)
      
      addMessage('assistant', '✅ **3D Model Generated!**', null, {
        type: '3d',
        url: res.url,
        tokensUsed: res.tokensUsed
      })

      await onBalanceUpdate()

      // Back to menu
      setTimeout(() => {
        setCurrentFlow(null)
        setFlowData({})
        setUploadedImage(null)
        setImagePreview(null)
        addMessage('assistant', 'What would you like to create next?', [
          { label: '🖼️ Generate Image', action: 'start_image' },
          { label: '🎵 Generate Music', action: 'start_music' },
          { label: '🎨 Generate 3D', action: 'start_3d' },
          { label: '💬 Chat', action: 'start_chat' }
        ])
      }, 2000)

    } catch (err) {
      addMessage('assistant', `❌ Error: ${err.response?.data?.detail || err.message}`)
      setTimeout(() => handleButtonClick('back_to_menu'), 2000)
    } finally {
      setLoading(false)
    }
  }

  // Handle send message
  const handleSend = async () => {
    if (!inputValue.trim() || loading) return

    const walletToUse = wallet || 'test_wallet_01234567890abcdef'
    const userMessage = inputValue
    setInputValue('')
    setLoading(true)

    addMessage('user', userMessage)

    try {
      if (currentFlow === 'chat') {
        // Chat mode
        const res = await chat(walletToUse, userMessage)
        addMessage('assistant', res.response)
        
      } else if (currentFlow === 'image') {
        // Image generation
        addMessage('assistant', '🖼️ **Generating image...**\n_Cost: 1 token_\n⏳ This may take a few seconds')
        const res = await generateImage(walletToUse, userMessage)
        
        addMessage('assistant', '✅ **Image Generated!**', null, {
          type: 'image',
          url: res.url,
          tokensUsed: res.tokensUsed,
          warning: res.warning
        })

        await onBalanceUpdate()

        // Back to menu
        setTimeout(() => {
          setCurrentFlow(null)
          addMessage('assistant', 'What would you like to create next?', [
            { label: '🖼️ Generate Image', action: 'start_image' },
            { label: '🎵 Generate Music', action: 'start_music' },
            { label: '🎨 Generate 3D', action: 'start_3d' },
            { label: '💬 Chat', action: 'start_chat' }
          ])
        }, 2000)

      } else if (currentFlow === 'music') {
        // Music generation
        const quality = flowData.musicQuality || 'hm'
        const cost = quality === 'hm' ? 14 : 10
        
        addMessage('assistant', `🎵 **Generating music...**\n_Cost: ${cost} tokens_\n⏳ This may take 2-3 minutes`)
        
        const res = await generateMusic(walletToUse, '', userMessage, quality)
        
        addMessage('assistant', '✅ **Music Generated!**', null, {
          type: 'music',
          url: res.url,
          tokensUsed: res.tokensUsed,
          warning: res.warning
        })

        await onBalanceUpdate()

        // Back to menu
        setTimeout(() => {
          setCurrentFlow(null)
          setFlowData({})
          addMessage('assistant', 'What would you like to create next?', [
            { label: '🖼️ Generate Image', action: 'start_image' },
            { label: '🎵 Generate Music', action: 'start_music' },
            { label: '🎨 Generate 3D', action: 'start_3d' },
            { label: '💬 Chat', action: 'start_chat' }
          ])
        }, 2000)
      }

    } catch (err) {
      addMessage('assistant', `❌ Error: ${err.response?.data?.detail || err.message}`)
      
      if (currentFlow !== 'chat') {
        setTimeout(() => handleButtonClick('back_to_menu'), 2000)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container mx-auto px-4 py-8 h-screen flex flex-col">
      <h1 className="text-4xl font-bold text-green-400 mb-4 text-center">Generate</h1>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto mb-4 space-y-4 max-w-3xl mx-auto w-full">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-2xl ${msg.role === 'user' ? 'ml-12' : 'mr-12'}`}>
              {/* Message bubble */}
              <div className={`p-4 rounded-xl ${
                msg.role === 'user'
                  ? 'bg-green-500/20 border border-green-500/40 text-green-300'
                  : 'glass border border-green-500/20 text-green-300'
              }`}>
                <div className="whitespace-pre-wrap">{msg.content}</div>

                {/* Result (image/music/3d) */}
                {msg.result && (
                  <div className="mt-4">
                    {msg.result.type === 'image' && (
                      <div>
                        <img 
                          src={msg.result.url} 
                          alt="Generated" 
                          className="w-full rounded-lg border border-green-500/30"
                        />
                        <div className="mt-2 flex items-center justify-between text-sm">
                          <span className="text-green-400">Tokens used: {msg.result.tokensUsed}</span>
                          <a 
                            href={msg.result.url} 
                            download 
                            className="flex items-center space-x-1 text-green-400 hover:text-green-300"
                          >
                            <Download className="w-4 h-4" />
                            <span>Download</span>
                          </a>
                        </div>
                        {msg.result.warning && (
                          <p className="mt-2 text-yellow-400 text-sm">⚠️ {msg.result.warning}</p>
                        )}
                      </div>
                    )}

                    {msg.result.type === 'music' && (
                      <div>
                        <audio 
                          controls 
                          className="w-full mt-2"
                          style={{ filter: 'hue-rotate(120deg)' }}
                        >
                          <source src={msg.result.url} type="audio/mpeg" />
                        </audio>
                        <div className="mt-2 flex items-center justify-between text-sm">
                          <span className="text-green-400">Tokens used: {msg.result.tokensUsed}</span>
                          <a 
                            href={msg.result.url} 
                            download 
                            className="flex items-center space-x-1 text-green-400 hover:text-green-300"
                          >
                            <Download className="w-4 h-4" />
                            <span>Download</span>
                          </a>
                        </div>
                        {msg.result.warning && (
                          <p className="mt-2 text-yellow-400 text-sm">⚠️ {msg.result.warning}</p>
                        )}
                      </div>
                    )}

                    {msg.result.type === '3d' && (
                      <div>
                        <div className="w-full h-64 bg-black/50 rounded-lg flex items-center justify-center border border-green-500/30">
                          <div className="text-center">
                            <Box className="w-16 h-16 mx-auto text-green-400 mb-2" />
                            <p className="text-green-300">3D Model Ready</p>
                          </div>
                        </div>
                        <div className="mt-2 flex items-center justify-between text-sm">
                          <span className="text-green-400">Tokens used: {msg.result.tokensUsed}</span>
                          <a 
                            href={msg.result.url} 
                            download 
                            className="flex items-center space-x-1 text-green-400 hover:text-green-300"
                          >
                            <Download className="w-4 h-4" />
                            <span>Download GLB</span>
                          </a>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Inline buttons (like Telegram) */}
              {msg.buttons && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {msg.buttons.map((btn, i) => (
                    <button
                      key={i}
                      onClick={() => handleButtonClick(btn.action)}
                      disabled={loading}
                      className="px-4 py-2 rounded-lg glass border border-green-500/30 text-green-300 hover:bg-green-500/10 hover:border-green-400/50 transition disabled:opacity-50 text-sm font-medium"
                    >
                      {btn.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {loading && (
          <div className="flex justify-start">
            <div className="glass border border-green-500/20 p-4 rounded-xl flex items-center space-x-2 text-green-300">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>Processing...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Upload prompt for 3D */}
      {showUploadPrompt && (
        <div className="max-w-3xl mx-auto w-full mb-4">
          <div className="glass border border-green-500/30 p-4 rounded-xl">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleImageUpload}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="w-full flex items-center justify-center space-x-2 bg-green-500/20 border border-green-500/40 text-green-300 px-6 py-3 rounded-lg hover:bg-green-500/30 transition"
            >
              <Upload className="w-5 h-5" />
              <span>Select Image from Device</span>
            </button>
            
            {imagePreview && (
              <div className="mt-4 relative">
                <img src={imagePreview} alt="Preview" className="w-full rounded-lg border border-green-500/30" />
                <button
                  onClick={() => {
                    setUploadedImage(null)
                    setImagePreview(null)
                  }}
                  className="absolute top-2 right-2 bg-red-500 text-white p-1 rounded-full hover:bg-red-600 transition"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Input area */}
      <div className="max-w-3xl mx-auto w-full">
        <div className="glass border border-green-500/30 rounded-xl p-4">
          <div className="flex items-center space-x-2">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
              placeholder={
                currentFlow === 'chat' ? 'Type your message...' :
                currentFlow === 'image' ? 'Describe the image you want...' :
                currentFlow === 'music' ? 'Enter music style/tags...' :
                'Choose an option above...'
              }
              disabled={loading || !currentFlow || showUploadPrompt}
              className="flex-1 bg-black/50 border border-green-500/30 text-green-400 placeholder-gray-500 px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50"
            />
            <button
              onClick={handleSend}
              disabled={loading || !inputValue.trim() || !currentFlow || showUploadPrompt}
              className="bg-green-500 text-black p-3 rounded-lg hover:bg-green-400 transition disabled:opacity-50 disabled:hover:bg-green-500"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>

          {/* Current balance */}
          <div className="mt-2 text-center">
            <span className="text-green-400/60 text-sm">
              Balance: <span className="font-semibold text-green-400">{balance}</span> tokens
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
