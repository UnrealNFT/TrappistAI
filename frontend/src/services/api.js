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

export default api
