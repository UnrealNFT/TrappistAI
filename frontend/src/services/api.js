import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_URL,
  timeout: 600000, // 10 min for music/lyrics generation
  headers: {
    'Content-Type': 'application/json'
  }
})

// ===== USER =====

export const getBalance = async (walletAddress) => {
  const { data } = await api.get(`/api/user/${walletAddress}/balance`)
  return data.tokens
}

export const getPaymentHistory = async (walletAddress) => {
  const { data } = await api.get(`/api/user/${walletAddress}/payments`)
  return data.payments
}

// ===== PAYMENTS =====

export const verifyPayment = async (walletAddress, txHash) => {
  const { data } = await api.post('/api/payments/verify', {
    walletAddress,
    txHash
  })
  return data
}

// ===== GENERATION =====

export const generateImage = async (walletAddress, prompt) => {
  const { data } = await api.post('/api/generate/image', {
    walletAddress,
    prompt
  })
  return data
}

export const generateMusic = async (walletAddress, lyrics, tags, quality = 'hm') => {
  const { data } = await api.post('/api/generate/music', {
    walletAddress,
    lyrics,
    tags,
    quality
  })
  return data
}

export const generate3D = async (walletAddress, imageUrl, withTexture = false) => {
  const { data } = await api.post('/api/generate/3d', {
    walletAddress,
    imageUrl,
    withTexture
  })
  return data
}

export const chat = async (walletAddress, message) => {
  const { data } = await api.post('/api/chat', {
    walletAddress,
    message
  })
  return data
}

export const generateLyrics = async (walletAddress, style, voice, subject) => {
  const { data } = await api.post('/api/generate/lyrics', {
    walletAddress,
    style,
    voice,
    subject
  })
  return data
}

// ===== JOBS =====

export const getJobStatus = async (jobId) => {
  const { data } = await api.get(`/api/jobs/${jobId}`)
  return data
}

// ===== PROFILE =====

export const getProfileInfo = async (walletAddress) => {
  const { data } = await api.get(`/api/profile/${walletAddress}`)
  return data
}

export const linkTelegram = async (walletAddress, telegramUsername) => {
  const { data } = await api.post('/api/profile/link-telegram', {
    walletAddress,
    telegramUsername
  })
  return data
}

export const verifyTelegramCode = async (walletAddress, code) => {
  const { data } = await api.post('/api/profile/verify-code', {
    walletAddress,
    code
  })
  return data
}

export const unlinkTelegram = async (walletAddress) => {
  const { data } = await api.post('/api/profile/unlink-telegram', {
    walletAddress
  })
  return data
}

// ===== RWA / TOKENIZATION =====

export const mintRWAToken = async (walletAddress, assetType, assetUrl, prompt, model, metadata = {}, isPublic = false) => {
  const { data } = await api.post('/api/rwa/mint', {
    walletAddress,
    assetType,
    assetUrl,
    prompt,
    model,
    metadata,
    isPublic
  })
  return data
}

export const shareAsset = async (walletAddress, assetType, assetUrl, prompt, model, metadata = {}) => {
  const { data } = await api.post('/api/share', {
    walletAddress,
    assetType,
    assetUrl,
    prompt,
    model,
    metadata,
    isPublic: true
  })
  return data
}

export default api
