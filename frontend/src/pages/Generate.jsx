import { useState, useEffect, useRef } from 'react'
import { Image, Music, Box, MessageSquare, Loader2, Upload, Send, X, Download } from 'lucide-react'
import { generateImage, generateMusic, generate3D, chat, generateLyrics, getJobStatus, mintRWAToken, shareAsset } from '../services/api'

// Music styles (from PiranAI bot)
const MUSIC_STYLES = {
  trap: { emoji: '💰', label: 'Trap' },
  drill: { emoji: '🔫', label: 'Drill' },
  pop: { emoji: '🎤', label: 'Pop' },
  rnb: { emoji: '💕', label: 'R&B' },
  rock: { emoji: '🎸', label: 'Rock' },
  afrobeat: { emoji: '🌍', label: 'Afrobeat' }
}

export default function Generate({ wallet, balance, onBalanceUpdate }) {
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState([]) // Empty by default - like Telegram
  
  const [inputValue, setInputValue] = useState('')
  const [currentFlow, setCurrentFlow] = useState('chat') // Chat active by default
  const [flowData, setFlowData] = useState({}) // Store flow-specific data
  const [uploadedImage, setUploadedImage] = useState(null)
  const [imagePreview, setImagePreview] = useState(null)
  const [showUploadPrompt, setShowUploadPrompt] = useState(false)
  const [activeJobs, setActiveJobs] = useState({}) // Track background jobs (music, 3D)
  
  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)

  // Load messages from localStorage on mount (persist like Telegram)
  useEffect(() => {
    const saved = localStorage.getItem('trappist_chat_history')
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        setMessages(parsed)
      } catch (e) {
        console.error('Failed to load chat history:', e)
      }
    }
  }, [])

  // Save messages to localStorage whenever they change
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem('trappist_chat_history', JSON.stringify(messages))
    }
  }, [messages])

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

  // Job polling helpers
  const startJobPolling = (jobId, messageId, jobType) => {
    console.log(`⏳ Starting polling for job: ${jobId} (${jobType})`)
    
    // Save job to localStorage
    const jobs = JSON.parse(localStorage.getItem('trappist_active_jobs') || '{}')
    jobs[jobId] = { messageId, jobType, startedAt: Date.now() }
    localStorage.setItem('trappist_active_jobs', JSON.stringify(jobs))
    setActiveJobs(jobs)
    
    // Start polling
    const interval = setInterval(async () => {
      try {
        const job = await getJobStatus(jobId)
        console.log(`📊 Job ${jobId} status:`, job.status)
        
        if (job.status === 'completed') {
          clearInterval(interval)
          
          // Remove from active jobs
          const updatedJobs = { ...activeJobs }
          delete updatedJobs[jobId]
          localStorage.setItem('trappist_active_jobs', JSON.stringify(updatedJobs))
          setActiveJobs(updatedJobs)
          
          // Update message AND add regenerate buttons in ONE atomic operation
          setMessages(prev => {
            // First, update the generating message with result
            const updated = prev.map(msg => 
              msg.id === messageId
                ? {
                    ...msg,
                    content: `✅ **${jobType === 'music' ? 'Music' : '3D Model'} Generated!**`,
                    result: {
                      type: jobType,
                      url: job.result.url,
                      tokensUsed: job.result.tokensUsed,
                      warning: job.result.warning
                    }
                  }
                : msg
            )
            
            // Then, add regenerate buttons for music (in same state update!)
            if (jobType === 'music') {
              return [...updated, 
                {
                  id: Date.now(),
                  role: 'assistant',
                  content: '🎵 **Want to try different lyrics?**',
                  buttons: [
                    { label: '🔄 Regenerate Lyrics', action: 'music_preview_redo' },
                    { label: '✏️ Write Own Lyrics', action: 'music_lyrics_own' }
                  ],
                  result: null
                },
                {
                  id: Date.now() + 1,
                  role: 'assistant',
                  content: '💾 **Save your creation:**',
                  buttons: [
                    { label: '💾 Save to Gallery (Private)', action: `save_music:${job.result.url}` },
                    { label: '📤 Save & Share (Public)', action: `share_music:${job.result.url}` }
                  ],
                  result: null
                }
              ]
            }
            
            // Add save/share buttons for 3D
            if (jobType === '3d') {
              return [...updated, 
                {
                  id: Date.now(),
                  role: 'assistant',
                  content: '💾 **Save your 3D model:**',
                  buttons: [
                    { label: '💾 Save to Gallery (Private)', action: `save_3d:${job.result.url}` },
                    { label: '📤 Save & Share (Public)', action: `share_3d:${job.result.url}` }
                  ],
                  result: null
                }
              ]
            }
            
            return updated
          })
          
          await onBalanceUpdate()
        } else if (job.status === 'failed') {
          clearInterval(interval)
          
          // Remove from active jobs
          const updatedJobs = { ...activeJobs }
          delete updatedJobs[jobId]
          localStorage.setItem('trappist_active_jobs', JSON.stringify(updatedJobs))
          setActiveJobs(updatedJobs)
          
          // Update message with error
          setMessages(prev => prev.map(msg => 
            msg.id === messageId
              ? { ...msg, content: `❌ **Error:** ${job.error}` }
              : msg
          ))
        } else {
          // Still processing - update message
          const elapsed = Math.floor((Date.now() - jobs[jobId].startedAt) / 1000)
          const minutes = Math.floor(elapsed / 60)
          const seconds = elapsed % 60
          const timeStr = minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`
          
          setMessages(prev => prev.map(msg => 
            msg.id === messageId
              ? { 
                  ...msg, 
                  content: `⏳ **Generating ${jobType === 'music' ? 'music' : '3D model'}...**\n_Time elapsed: ${timeStr}_\n\n💡 **You can close this page!** Generation continues in background. Come back anytime to check.` 
                }
              : msg
          ))
        }
      } catch (err) {
        console.error(`❌ Error polling job ${jobId}:`, err)
      }
    }, 5000) // Poll every 5 seconds
    
    // Clean up on unmount
    return () => clearInterval(interval)
  }

  // Restore active jobs on mount
  useEffect(() => {
    const savedJobs = localStorage.getItem('trappist_active_jobs')
    if (savedJobs) {
      try {
        const jobs = JSON.parse(savedJobs)
        setActiveJobs(jobs)
        
        // Resume polling for each job
        Object.keys(jobs).forEach(jobId => {
          const { messageId, jobType } = jobs[jobId]
          startJobPolling(jobId, messageId, jobType)
        })
      } catch (e) {
        console.error('Failed to restore active jobs:', e)
      }
    }
  }, [])

  // Handle button click (inline keyboard) - EXACTLY like Telegram
  const handleButtonClick = async (action) => {
    setLoading(true)

    try {
      // ===== MUSIC FLOW =====
      if (action === 'music_hm' || action === 'music_minimax') {
        const quality = action === 'music_hm' ? 'hm' : 'minimax'
        const cost = quality === 'hm' ? 14 : 10
        const qualityLabel = quality === 'hm' ? 'HeartMuLa' : 'MiniMax 2.5 HD'
        
        setCurrentFlow('music_style')
        setFlowData({ ...flowData, musicQuality: quality })
        
        addMessage('assistant', `✅ **${qualityLabel}** selected (${cost} tokens)\n\n🎼 **Step 2/4 — Choose your style:**`, 
          Object.keys(MUSIC_STYLES).map(key => ({
            label: `${MUSIC_STYLES[key].emoji} ${MUSIC_STYLES[key].label}`,
            action: `music_style_${key}`
          }))
        )
        setLoading(false)
        return
      }

      // Style selection
      if (action.startsWith('music_style_')) {
        const style = action.replace('music_style_', '')
        const styleLabel = MUSIC_STYLES[style]?.label || style
        
        setCurrentFlow('music_voice')
        setFlowData({ ...flowData, musicStyle: style })
        
        addMessage('assistant', `✅ Style: **${styleLabel}**\n\n🎤 **Step 3/4 — Voice:**`, [
          { label: '🗣️ Male', action: 'music_voice_male' },
          { label: '🗣️ Female', action: 'music_voice_female' }
        ])
        setLoading(false)
        return
      }

      // Voice selection
      if (action === 'music_voice_male' || action === 'music_voice_female') {
        const voice = action === 'music_voice_male' ? 'male' : 'female'
        const voiceIcon = voice === 'male' ? '👨' : '👩'
        const styleLabel = MUSIC_STYLES[flowData.musicStyle]?.label
        
        setCurrentFlow('music_type')
        setFlowData({ ...flowData, musicVoice: voice })
        
        addMessage('assistant', `✅ **${styleLabel}** ${voiceIcon}\n\n🎵 **Step 4/4 — Lyrics or Instrumental?**`, [
          { label: '🎤 With Lyrics', action: 'music_type_paroles' },
          { label: '🎸 Instrumental Only', action: 'music_type_instrumental' }
        ])
        setLoading(false)
        return
      }

      // Type selection: Paroles
      if (action === 'music_type_paroles') {
        setCurrentFlow('music_lyrics_choice')
        setFlowData({ ...flowData, musicType: 'paroles' })
        
        addMessage('assistant', '🎤 **How do you want to create the lyrics?**', [
          { label: '✍️ I write my own lyrics', action: 'music_lyrics_own' },
          { label: '🤖 AI generates lyrics', action: 'music_lyrics_ai' },
          { label: '❌ Cancel', action: 'music_cancel' }
        ])
        setLoading(false)
        return
      }

      // Type selection: Instrumental
      if (action === 'music_type_instrumental') {
        setCurrentFlow('music_tags')
        setFlowData({ ...flowData, musicType: 'instrumental', musicLyrics: '' })
        
        addMessage('assistant', '🎸 **Instrumental Mode**\n\nEnter music tags/mood:\n_(Example: dark, cinematic, powerful)_')
        setLoading(false)
        return
      }

      // Lyrics choice: Own
      if (action === 'music_lyrics_own') {
        setCurrentFlow('music_own_lyrics')
        setFlowData({ ...flowData, musicLyricsType: 'own' })
        
        addMessage('assistant', '✍️ **Send your lyrics now:**\n_(You can use `[Verse]`, `[Chorus]`, `[Bridge]` or free text)_\n_(or /cancel)_')
        setLoading(false)
        return
      }

      // Lyrics choice: AI
      if (action === 'music_lyrics_ai') {
        setCurrentFlow('music_subject')
        setFlowData({ ...flowData, musicLyricsType: 'ai' })
        
        const styleLabel = MUSIC_STYLES[flowData.musicStyle]?.label
        const voiceIcon = flowData.musicVoice === 'male' ? '👨' : '👩'
        
        addMessage('assistant', 
          `🤖 **AI Lyrics Generator**\n\n` +
          `Style: **${styleLabel}** ${voiceIcon}\n\n` +
          `**CRITICAL: Describe what the song is ABOUT (the subject/topic)**\n\n` +
          `Examples:\n` +
          `• "black dog, great companion, loyalty"\n` +
          `• "lost in the city at 3AM, neon lights"\n` +
          `• "heartbreak but empowered, rising"\n` +
          `• "money and power, dark energy"\n\n` +
          `⚠️ Remember: The STYLE (${styleLabel}) defines HOW you sing.\n` +
          `The SUBJECT below defines WHAT you sing about.`
        )
        setLoading(false)
        return
      }

      // Preview actions
      if (action === 'music_preview_generate') {
        await handleMusicGeneration()
        return
      }

      if (action === 'music_preview_redo') {
        // Regenerate lyrics
        const walletToUse = wallet || 'test_wallet_01234567890abcdef'
        addMessage('assistant', '🔄 **Rewriting lyrics...**')
        
        try {
          const res = await generateLyrics(
            walletToUse,
            flowData.musicStyle,
            flowData.musicVoice,
            flowData.musicSubject
          )
          
          setFlowData({ ...flowData, musicLyrics: res.lyrics })
          
          const preview = res.lyrics.length > 3500 ? res.lyrics.substring(0, 3500) + '…' : res.lyrics
          addMessage('assistant', `📝 **New Lyrics Generated:**\n\n\`\`\`\n${preview}\n\`\`\``, [
            { label: '🎵 Generate Music', action: 'music_preview_generate' },
            { label: '🔄 Rewrite Again', action: 'music_preview_redo' },
            { label: '✏️ Edit Manually', action: 'music_preview_edit' }
          ])
        } catch (err) {
          const errorMsg = err.response?.data?.detail 
            ? (typeof err.response.data.detail === 'string' ? err.response.data.detail : JSON.stringify(err.response.data.detail))
            : err.message
          addMessage('assistant', `❌ Rewrite error: ${errorMsg}`)
        } finally {
          setLoading(false)
        }
        return
      }

      if (action === 'music_preview_edit') {
        setCurrentFlow('music_own_lyrics')
        addMessage('assistant', `✏️ **Edit the lyrics:**\n\n\`\`\`\n${flowData.musicLyrics}\n\`\`\`\n\n_Send your edited version:_`)
        setLoading(false)
        return
      }

      // Save/Share music handlers
      if (action.startsWith('save_music:')) {
        const musicUrl = action.replace('save_music:', '')
        const walletToUse = wallet || 'test_wallet_01234567890abcdef'
        
        try {
          await mintRWAToken(
            walletToUse,
            'music',
            musicUrl,
            flowData.musicSubject || 'Music generation',
            flowData.musicQuality === 'hm' ? 'HeartMuLa' : 'MiniMax 2.5 HD',
            {
              style: flowData.musicStyle,
              voice: flowData.musicVoice,
              lyrics: flowData.musicLyrics || ''
            },
            false // Private
          )
          
          addMessage('assistant', '💾 **Saved to your private gallery!**\n\n_Check your profile to see all your creations._')
        } catch (err) {
          const errorMsg = err.response?.data?.detail || err.message
          addMessage('assistant', `❌ Save error: ${errorMsg}`)
        } finally {
          setLoading(false)
        }
        return
      }

      if (action.startsWith('share_music:')) {
        const musicUrl = action.replace('share_music:', '')
        const walletToUse = wallet || 'test_wallet_01234567890abcdef'
        
        try {
          await shareAsset(
            walletToUse,
            'music',
            musicUrl,
            flowData.musicSubject || 'Music generation',
            flowData.musicQuality === 'hm' ? 'HeartMuLa' : 'MiniMax 2.5 HD',
            {
              style: flowData.musicStyle,
              voice: flowData.musicVoice,
              lyrics: flowData.musicLyrics || ''
            }
          )
          
          addMessage('assistant', '📤 **Shared publicly!**\n\n_Your music is now visible in the community feed._')
        } catch (err) {
          const errorMsg = err.response?.data?.detail || err.message
          addMessage('assistant', `❌ Share error: ${errorMsg}`)
        } finally {
          setLoading(false)
        }
        return
      }

      if (action === 'music_cancel') {
        setCurrentFlow('chat')
        setFlowData({})
        addMessage('assistant', '❌ Music generation cancelled.')
        setLoading(false)
        return
      }

      // Save/Share image handlers
      if (action.startsWith('save_image:')) {
        const parts = action.replace('save_image:', '').split(':')
        const imageUrl = parts[0]
        const description = parts[1] || 'Image generation'
        const walletToUse = wallet || 'test_wallet_01234567890abcdef'
        
        try {
          await mintRWAToken(
            walletToUse,
            'image',
            imageUrl,
            description,
            'FLUX.1 schnell',
            {},
            false // Private
          )
          
          addMessage('assistant', '💾 **Saved to your private gallery!**\n\n_Check your profile to see all your creations._')
        } catch (err) {
          const errorMsg = err.response?.data?.detail || err.message
          addMessage('assistant', `❌ Save error: ${errorMsg}`)
        } finally {
          setLoading(false)
        }
        return
      }

      if (action.startsWith('share_image:')) {
        const parts = action.replace('share_image:', '').split(':')
        const imageUrl = parts[0]
        const description = parts[1] || 'Image generation'
        const walletToUse = wallet || 'test_wallet_01234567890abcdef'
        
        try {
          await shareAsset(
            walletToUse,
            'image',
            imageUrl,
            description,
            'FLUX.1 schnell',
            {}
          )
          
          addMessage('assistant', '📤 **Shared publicly!**\n\n_Your image is now visible in the community feed._')
        } catch (err) {
          const errorMsg = err.response?.data?.detail || err.message
          addMessage('assistant', `❌ Share error: ${errorMsg}`)
        } finally {
          setLoading(false)
        }
        return
      }

      // Save/Share 3D handlers
      if (action.startsWith('save_3d:')) {
        const modelUrl = action.replace('save_3d:', '')
        const walletToUse = wallet || 'test_wallet_01234567890abcdef'
        
        try {
          await mintRWAToken(
            walletToUse,
            '3d',
            modelUrl,
            '3D Model generation',
            'Hunyuan-3D V3.1',
            {},
            false // Private
          )
          
          addMessage('assistant', '💾 **Saved to your private gallery!**\n\n_Check your profile to see all your creations._')
        } catch (err) {
          const errorMsg = err.response?.data?.detail || err.message
          addMessage('assistant', `❌ Save error: ${errorMsg}`)
        } finally {
          setLoading(false)
        }
        return
      }

      if (action.startsWith('share_3d:')) {
        const modelUrl = action.replace('share_3d:', '')
        const walletToUse = wallet || 'test_wallet_01234567890abcdef'
        
        try {
          await shareAsset(
            walletToUse,
            '3d',
            modelUrl,
            '3D Model generation',
            'Hunyuan-3D V3.1',
            {}
          )
          
          addMessage('assistant', '📤 **Shared publicly!**\n\n_Your 3D model is now visible in the community feed._')
        } catch (err) {
          const errorMsg = err.response?.data?.detail || err.message
          addMessage('assistant', `❌ Share error: ${errorMsg}`)
        } finally {
          setLoading(false)
        }
        return
      }

      // ===== 3D FLOW =====
      if (action === '3d_from_image') {
        setShowUploadPrompt(true)
        addMessage('assistant', '📷 **Upload an Image**\n\nClick the button below to select an image from your device.')
        setLoading(false)
        return
      }

      if (action === '3d_from_text') {
        addMessage('assistant', '✍️ Text-to-3D is coming soon! Use "From Image" for now.')
        setLoading(false)
        return
      }

      if (action === '3d_quality_notex') {
        await handle3DGeneration(false)
        return
      }

      if (action === '3d_quality_tex') {
        await handle3DGeneration(true)
        return
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
      
      // NO user message for upload (like Telegram - inline action)
      addMessage('assistant', '🎨 **Choose 3D Quality:**\n\n⚡ **Sans texture** — 2 tokens (~5 min)\n   └ Géométrie pure, monochrome\n\n🎨 **Avec texture** — 30 tokens (~10 min)\n   └ Couleurs et textures complètes', [
        { label: '⚡ Sans texture (2 tokens)', action: '3d_quality_notex' },
        { label: '🎨 Avec texture (30 tokens)', action: '3d_quality_tex' }
      ])
    }
    reader.readAsDataURL(file)
  }

  // Handle 3D generation
  const handle3DGeneration = async (withTexture) => {
    const walletToUse = wallet || 'test_wallet_01234567890abcdef'
    const cost = withTexture ? 30 : 2
    
    setLoading(true)
    // NO user message for inline button click (like Telegram)
    
    // Create message for this generation
    const messageId = Date.now()
    addMessage('assistant', `🎨 **Starting 3D generation...**\n_Cost: ${cost} tokens_\n⏳ Estimated time: 5-10 minutes\n\n💡 **You can close this page!** Generation continues in background.`)

    try {
      // Use image preview as data URL
      const res = await generate3D(walletToUse, imagePreview, withTexture)
      
      // Start job polling
      const lastMessage = messages[messages.length - 1]
      startJobPolling(res.job_id, lastMessage.id, '3d')
      
      // Clean up uploaded image
      setUploadedImage(null)
      setImagePreview(null)
      setShowUploadPrompt(false)
      setCurrentFlow('chat')

    } catch (err) {
      addMessage('assistant', `❌ Error: ${err.response?.data?.detail || err.message}`)
    } finally {
      setLoading(false)
    }
  }

  // Handle music generation
  const handleMusicGeneration = async () => {
    const walletToUse = wallet || 'test_wallet_01234567890abcdef'
    const quality = flowData.musicQuality
    const cost = quality === 'hm' ? 14 : 10
    const lyrics = flowData.musicLyrics || ''
    const styleLabel = MUSIC_STYLES[flowData.musicStyle]?.label || flowData.musicStyle
    
    // Generate tags from style
    const tags = `${styleLabel}, ${flowData.musicVoice} vocals, modern, high quality`
    
    setLoading(true)
    
    // Create message for this generation
    const messageId = Date.now()
    addMessage('assistant', `🎵 **Starting music generation...**\n_Cost: ${cost} tokens_\n⏳ Estimated time: 2-10 minutes\n\n💡 **You can close this page!** Generation continues in background.`)

    try {
      const res = await generateMusic(walletToUse, lyrics, tags, quality)
      
      // Start job polling
      const lastMessage = messages[messages.length - 1]
      startJobPolling(res.job_id, lastMessage.id, 'music')
      
      // Keep flowData for regeneration - don't clean up!
      // User can regenerate lyrics infinite times
      setCurrentFlow('chat')

    } catch (err) {
      addMessage('assistant', `❌ Error: ${err.response?.data?.detail || err.message}`)
    } finally {
      setLoading(false)
    }
  }

  // Handle send message - EXACTLY like Telegram with command parsing
  const handleSend = async () => {
    if (!inputValue.trim() || loading) return

    const walletToUse = wallet || 'test_wallet_01234567890abcdef'
    const userMessage = inputValue.trim()
    setInputValue('')

    // Detect commands (like Telegram)
    if (userMessage.startsWith('/')) {
      const parts = userMessage.split(' ')
      const command = parts[0].toLowerCase()
      const args = parts.slice(1).join(' ')

      // /image <prompt>
      if (command === '/image') {
        if (!args) {
          addMessage('user', userMessage)
          addMessage('assistant', '📸 **Usage:** `/image <description>`\n\nExample: `/image sunset over mountains`')
          return
        }
        
        setLoading(true)
        addMessage('user', userMessage)
        addMessage('assistant', '🖼️ **Generating image...**\n_Cost: 1 token_\n⏳ This may take a few seconds')
        
        try {
          const res = await generateImage(walletToUse, args)
          addMessage('assistant', '✅ **Image Generated!**', null, {
            type: 'image',
            url: res.url,
            tokensUsed: res.tokensUsed,
            warning: res.warning
          })
          
          // Add save/share buttons for image
          addMessage('assistant', '💾 **Save your creation:**', [
            { label: '💾 Save to Gallery (Private)', action: `save_image:${res.url}:${args}` },
            { label: '📤 Save & Share (Public)', action: `share_image:${res.url}:${args}` }
          ])
          
          await onBalanceUpdate()
        } catch (err) {
          addMessage('assistant', `❌ Error: ${err.response?.data?.detail || err.message}`)
        } finally {
          setLoading(false)
        }
        return
      }

      // /music
      if (command === '/music') {
        addMessage('user', userMessage)
        addMessage('assistant', '🎵 **Music Generation**\n\nChoose quality:', [
          { label: '🎵 HeartMuLa (14 tokens)', action: 'music_hm' },
          { label: '🎶 MiniMax HD (10 tokens)', action: 'music_minimax' }
        ])
        return
      }

      // /3d
      if (command === '/3d') {
        addMessage('user', userMessage)
        addMessage('assistant', '🎨 **3D Generation**\n\nHow do you want to create?', [
          { label: '🖼️ From Image', action: '3d_from_image' },
          { label: '✍️ From Text (Coming Soon)', action: '3d_from_text' }
        ])
        return
      }

      // Unknown command - treat as chat
    }

    // ===== MUSIC FLOW INPUTS =====
    
    // Subject input (AI lyrics generation)
    if (currentFlow === 'music_subject') {
      setLoading(true)
      addMessage('user', userMessage)
      addMessage('assistant', '🤖 **AI Lyrics Generator working...**\n⏳ ~15 seconds')
      
      try {
        const res = await generateLyrics(
          walletToUse,
          flowData.musicStyle,
          flowData.musicVoice,
          userMessage
        )
        
        setFlowData({ ...flowData, musicSubject: userMessage, musicLyrics: res.lyrics })
        setCurrentFlow('music_preview')
        
        const preview = res.lyrics.length > 3500 ? res.lyrics.substring(0, 3500) + '…' : res.lyrics
        addMessage('assistant', `📝 **Lyrics Generated by AI:**\n\n\`\`\`\n${preview}\n\`\`\``, [
          { label: '🎵 Generate Music', action: 'music_preview_generate' },
          { label: '🔄 Rewrite', action: 'music_preview_redo' },
          { label: '✏️ Edit Manually', action: 'music_preview_edit' }
        ])
      } catch (err) {
        const errorMsg = err.response?.data?.detail 
          ? (typeof err.response.data.detail === 'string' ? err.response.data.detail : JSON.stringify(err.response.data.detail))
          : err.message
        addMessage('assistant', `❌ Lyrics generation error: ${errorMsg}`)
      } finally {
        setLoading(false)
      }
      return
    }

    // Own lyrics input
    if (currentFlow === 'music_own_lyrics') {
      setLoading(true)
      addMessage('user', userMessage)
      setFlowData({ ...flowData, musicLyrics: userMessage })
      
      await handleMusicGeneration()
      return
    }

    // Instrumental tags input
    if (currentFlow === 'music_tags') {
      setLoading(true)
      addMessage('user', userMessage)
      
      const quality = flowData.musicQuality
      const cost = quality === 'hm' ? 14 : 10
      
      // Create message for this generation
      const messageId = Date.now()
      addMessage('assistant', `🎸 **Starting instrumental generation...**\n_Cost: ${cost} tokens_\n⏳ Estimated time: 2-10 minutes\n\n💡 **You can close this page!** Generation continues in background.`)
      
      try {
        const res = await generateMusic(walletToUse, '', userMessage, quality)
        
        // Start job polling
        const lastMessage = messages[messages.length - 1]
        startJobPolling(res.job_id, lastMessage.id, 'music')
        
        setCurrentFlow('chat')
        // Keep flowData for potential regeneration
      } catch (err) {
        addMessage('assistant', `❌ Error: ${err.response?.data?.detail || err.message}`)
      } finally {
        setLoading(false)
      }
      return
    }

    // Default: Free chat with Groq (like Telegram on_free_message)
    setLoading(true)
    addMessage('user', userMessage)
    
    try {
      const res = await chat(walletToUse, userMessage)
      addMessage('assistant', res.response)
    } catch (err) {
      addMessage('assistant', `❌ Error: ${err.response?.data?.detail || err.message}`)
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
                showUploadPrompt ? 'Upload an image first...' :
                currentFlow === 'music' && flowData.musicQuality ? 'Enter music style/tags...' :
                'Type a message or command (/image, /music, /3d)...'
              }
              disabled={loading || showUploadPrompt}
              className="flex-1 bg-black/50 border border-green-500/30 text-green-400 placeholder-gray-500 px-4 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50"
            />
            <button
              onClick={handleSend}
              disabled={loading || !inputValue.trim() || showUploadPrompt}
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
