import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Download, ExternalLink, Music, Box, Loader2, Calendar, User } from 'lucide-react'

// Loads the Google <model-viewer> web component once, for 3D assets.
let modelViewerPromise = null
function ensureModelViewer() {
  if (modelViewerPromise) return modelViewerPromise
  modelViewerPromise = new Promise((resolve) => {
    if (typeof window !== 'undefined' && window.customElements?.get('model-viewer')) {
      resolve()
      return
    }
    const script = document.createElement('script')
    script.type = 'module'
    script.src = 'https://unpkg.com/@google/model-viewer@3.5.0/dist/model-viewer.min.js'
    script.onload = () => resolve()
    script.onerror = () => resolve()
    document.head.appendChild(script)
  })
  return modelViewerPromise
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  const diff = Date.now() - date.getTime()
  const hours = Math.floor(diff / (1000 * 60 * 60))
  const days = Math.floor(hours / 24)
  if (days > 0) return `${days}d ago`
  if (hours > 0) return `${hours}h ago`
  return 'Just now'
}

/**
 * Unified in-site media player / viewer.
 * Renders images, an audio player for music, and an interactive 3D viewer.
 *
 * Props:
 *   item:    { assetType, assetUrl, prompt, walletAddress, createdAt, tokenId }
 *   onClose: () => void
 */
const MediaViewer = ({ item, onClose }) => {
  const [modelReady, setModelReady] = useState(false)

  // Close on Escape
  useEffect(() => {
    if (!item) return
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [item, onClose])

  // Load model-viewer when a 3D item is opened
  useEffect(() => {
    if (item?.assetType === '3d') {
      setModelReady(false)
      ensureModelViewer().then(() => setModelReady(true))
    }
  }, [item])

  if (!item) return null

  const { assetType, assetUrl, prompt, walletAddress, createdAt } = item

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 z-[100] flex items-center justify-center bg-black/85 backdrop-blur-sm p-4"
      >
        <motion.div
          initial={{ scale: 0.92, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.92, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 28 }}
          onClick={(e) => e.stopPropagation()}
          className="relative w-full max-w-4xl bg-gray-950 border border-gray-800 rounded-2xl overflow-hidden shadow-2xl"
        >
          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-3 right-3 z-10 p-2 bg-black/60 hover:bg-black/90 rounded-full text-white transition"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>

          {/* ---- MEDIA AREA ---- */}
          <div className="bg-black flex items-center justify-center min-h-[320px] max-h-[70vh]">
            {assetType === 'image' && (
              <img
                src={assetUrl}
                alt={prompt || 'Creation'}
                className="max-h-[70vh] w-auto object-contain"
              />
            )}

            {assetType === 'music' && (
              <div className="w-full flex flex-col items-center justify-center gap-6 py-12 px-6 bg-gradient-to-br from-green-900/40 via-gray-900 to-gray-950">
                <div className="w-28 h-28 rounded-full bg-green-500/10 border border-green-500/30 flex items-center justify-center">
                  <Music className="w-14 h-14 text-green-400" />
                </div>
                <audio
                  src={assetUrl}
                  controls
                  autoPlay
                  className="w-full max-w-md"
                />
              </div>
            )}

            {assetType === '3d' && (
              <div className="w-full h-[60vh] bg-gradient-to-br from-blue-900/30 to-cyan-900/20 flex items-center justify-center">
                {!modelReady ? (
                  <div className="flex flex-col items-center gap-3 text-cyan-300">
                    <Loader2 className="w-8 h-8 animate-spin" />
                    <span className="text-sm">Loading 3D viewer…</span>
                  </div>
                ) : (
                  // eslint-disable-next-line react/no-unknown-property
                  <model-viewer
                    src={assetUrl}
                    camera-controls="true"
                    auto-rotate="true"
                    shadow-intensity="1"
                    exposure="1"
                    style={{ width: '100%', height: '100%' }}
                  />
                )}
              </div>
            )}
          </div>

          {/* ---- INFO BAR ---- */}
          <div className="p-4 border-t border-gray-800">
            <div className="flex items-center gap-3 mb-2 text-sm text-gray-400">
              <span className="px-2 py-0.5 rounded-full bg-gray-800 capitalize flex items-center gap-1">
                {assetType === 'music' ? <Music className="w-3 h-3" /> : assetType === '3d' ? <Box className="w-3 h-3" /> : null}
                {assetType}
              </span>
              {walletAddress && (
                <span className="flex items-center gap-1">
                  <User className="w-3 h-3" />
                  {walletAddress.substring(0, 8)}…
                </span>
              )}
              {createdAt && (
                <span className="flex items-center gap-1">
                  <Calendar className="w-3 h-3" />
                  {formatDate(createdAt)}
                </span>
              )}
            </div>

            {prompt && (
              <p className="text-sm text-gray-300 mb-3">{prompt}</p>
            )}

            <div className="flex gap-2">
              <a
                href={assetUrl}
                download
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition flex items-center gap-2"
              >
                <Download className="w-4 h-4" />
                Download
              </a>
              <a
                href={assetUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg text-sm font-medium transition flex items-center gap-2"
              >
                <ExternalLink className="w-4 h-4" />
                Open original
              </a>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

export default MediaViewer
