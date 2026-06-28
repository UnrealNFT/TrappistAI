import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Shield, Trash2, Loader2, Lock, LogOut, Image, Music, Box, Calendar, RefreshCw } from 'lucide-react'
import MediaViewer from '../components/MediaViewer'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const STORAGE_KEY = 'trappist_admin_secret'

const Admin = () => {
  const [secret, setSecret] = useState(() => sessionStorage.getItem(STORAGE_KEY) || '')
  const [authed, setAuthed] = useState(false)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState('')

  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [deletingId, setDeletingId] = useState(null)
  const [selected, setSelected] = useState(null)

  // Try to auto-login if a secret is stored
  useEffect(() => {
    if (secret) verify(secret, true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const verify = async (value, silent = false) => {
    setChecking(true)
    setError('')
    try {
      const res = await fetch(`${API_URL}/api/admin/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ secret: value }),
      })
      if (res.ok) {
        sessionStorage.setItem(STORAGE_KEY, value)
        setSecret(value)
        setAuthed(true)
        fetchItems(value)
      } else {
        if (!silent) setError('Invalid admin secret')
        setAuthed(false)
        sessionStorage.removeItem(STORAGE_KEY)
      }
    } catch (e) {
      if (!silent) setError('Connection error')
    } finally {
      setChecking(false)
    }
  }

  const fetchItems = async (value = secret) => {
    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/admin/community`, {
        headers: { 'X-Admin-Secret': value },
      })
      const data = await res.json()
      if (data.success) setItems(data.items || [])
    } catch (e) {
      console.error('fetch items error', e)
    } finally {
      setLoading(false)
    }
  }

  const deleteItem = async (tokenId) => {
    if (!window.confirm(`Delete item #${tokenId} permanently? This removes it from Explore and from storage.`)) return
    setDeletingId(tokenId)
    try {
      const res = await fetch(`${API_URL}/api/admin/community/${tokenId}`, {
        method: 'DELETE',
        headers: { 'X-Admin-Secret': secret },
      })
      if (res.ok) {
        setItems((prev) => prev.filter((it) => it.tokenId !== tokenId))
        if (selected?.tokenId === tokenId) setSelected(null)
      } else {
        alert('Delete failed')
      }
    } catch (e) {
      alert('Connection error')
    } finally {
      setDeletingId(null)
    }
  }

  const logout = () => {
    sessionStorage.removeItem(STORAGE_KEY)
    setSecret('')
    setAuthed(false)
    setItems([])
  }

  const formatDate = (d) => {
    if (!d) return ''
    return new Date(d).toLocaleString()
  }

  // ---- LOGIN SCREEN ----
  if (!authed) {
    return (
      <div className="min-h-screen pt-24 px-4 flex justify-center">
        <div className="w-full max-w-sm">
          <div className="flex items-center gap-3 mb-6 text-white">
            <Shield className="w-8 h-8 text-green-400" />
            <h1 className="text-2xl font-bold">Admin</h1>
          </div>
          <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-6">
            <label className="block text-sm text-gray-400 mb-2 flex items-center gap-2">
              <Lock className="w-4 h-4" /> Admin secret
            </label>
            <input
              type="password"
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && verify(secret)}
              placeholder="Enter admin secret"
              className="w-full px-4 py-2 bg-black/50 border border-gray-700 rounded-lg text-white mb-3 focus:border-green-500 outline-none"
            />
            {error && <p className="text-red-400 text-sm mb-3">{error}</p>}
            <button
              onClick={() => verify(secret)}
              disabled={checking || !secret}
              className="w-full px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white rounded-lg font-medium flex items-center justify-center gap-2"
            >
              {checking ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
              Unlock
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ---- DASHBOARD ----
  return (
    <div className="min-h-screen pt-20 px-4 pb-20">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <Shield className="w-8 h-8 text-green-400" />
            Moderation — Explore
          </h1>
          <div className="flex gap-2">
            <button
              onClick={() => fetchItems()}
              className="px-3 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg flex items-center gap-2 text-sm"
            >
              <RefreshCw className="w-4 h-4" /> Refresh
            </button>
            <button
              onClick={logout}
              className="px-3 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg flex items-center gap-2 text-sm"
            >
              <LogOut className="w-4 h-4" /> Logout
            </button>
          </div>
        </div>

        <p className="text-gray-400 mb-6 text-sm">{items.length} public item(s)</p>

        {loading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-green-400" />
          </div>
        ) : items.length === 0 ? (
          <p className="text-gray-500 text-center py-20">No public items.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {items.map((item) => (
              <motion.div
                key={item.tokenId}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-gray-900/50 border border-gray-800 rounded-lg overflow-hidden group"
              >
                <div className="relative cursor-pointer" onClick={() => setSelected(item)}>
                  {item.assetType === 'image' && (
                    <img src={item.assetUrl} alt="" className="w-full h-48 object-cover" />
                  )}
                  {item.assetType === 'music' && (
                    <div className="w-full h-48 bg-gradient-to-br from-green-900/50 to-gray-900/50 flex items-center justify-center">
                      <Music className="w-16 h-16 text-green-400" />
                    </div>
                  )}
                  {item.assetType === '3d' && (
                    <div className="w-full h-48 bg-gradient-to-br from-blue-900/50 to-cyan-900/50 flex items-center justify-center">
                      <Box className="w-16 h-16 text-cyan-400" />
                    </div>
                  )}
                  <div className="absolute top-2 left-2 px-2 py-0.5 bg-black/70 rounded-full text-xs text-white capitalize">
                    #{item.tokenId} · {item.assetType}
                  </div>
                </div>

                <div className="p-4">
                  <div className="text-xs text-gray-500 mb-2 flex items-center gap-1">
                    <Calendar className="w-3 h-3" /> {formatDate(item.createdAt)}
                  </div>
                  {item.prompt && (
                    <p className="text-xs text-gray-400 mb-3 line-clamp-2">{item.prompt}</p>
                  )}
                  <button
                    onClick={() => deleteItem(item.tokenId)}
                    disabled={deletingId === item.tokenId}
                    className="w-full px-3 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white rounded text-sm flex items-center justify-center gap-2"
                  >
                    {deletingId === item.tokenId ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                    Delete
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      <MediaViewer item={selected} onClose={() => setSelected(null)} />
    </div>
  )
}

export default Admin
