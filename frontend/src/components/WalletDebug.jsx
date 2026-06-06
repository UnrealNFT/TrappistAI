import { useState, useEffect } from 'react'

export default function WalletDebug() {
  const [info, setInfo] = useState({
    hasExtension: false,
    extensionInfo: null,
    error: null
  })

  useEffect(() => {
    const checkWallet = async () => {
      try {
        // Check if extension exists
        const hasExt = typeof window.casperlabsHelper !== 'undefined'
        
        let extInfo = null
        if (hasExt) {
          try {
            const isConnected = await window.casperlabsHelper.isConnected()
            const publicKey = isConnected ? await window.casperlabsHelper.getActivePublicKey() : null
            extInfo = {
              isConnected,
              publicKey,
              methods: Object.keys(window.casperlabsHelper)
            }
          } catch (e) {
            extInfo = { error: e.message }
          }
        }

        setInfo({
          hasExtension: hasExt,
          extensionInfo: extInfo,
          error: null,
          allWindowKeys: Object.keys(window).filter(k => k.toLowerCase().includes('casper'))
        })
      } catch (error) {
        setInfo({ hasExtension: false, extensionInfo: null, error: error.message })
      }
    }

    checkWallet()
    
    // Recheck every 2 seconds
    const interval = setInterval(checkWallet, 2000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="fixed bottom-4 right-4 bg-black/80 text-white p-4 rounded-lg text-xs max-w-md z-50">
      <div className="font-bold mb-2">🔍 Casper Wallet Debug</div>
      
      <div className="space-y-2">
        <div>
          <span className={info.hasExtension ? 'text-green-400' : 'text-red-400'}>
            {info.hasExtension ? '✅' : '❌'} Extension detected: {info.hasExtension.toString()}
          </span>
        </div>

        {info.extensionInfo && (
          <div className="bg-gray-800 p-2 rounded">
            <div>Connected: {info.extensionInfo.isConnected ? '✅' : '❌'}</div>
            {info.extensionInfo.publicKey && (
              <div>Wallet: {info.extensionInfo.publicKey.slice(0, 20)}...</div>
            )}
            {info.extensionInfo.methods && (
              <div>Methods: {info.extensionInfo.methods.join(', ')}</div>
            )}
            {info.extensionInfo.error && (
              <div className="text-red-400">Error: {info.extensionInfo.error}</div>
            )}
          </div>
        )}

        {info.allWindowKeys && info.allWindowKeys.length > 0 && (
          <div className="text-yellow-400">
            Window keys: {info.allWindowKeys.join(', ')}
          </div>
        )}

        {info.error && (
          <div className="text-red-400">Error: {info.error}</div>
        )}

        <div className="text-gray-400 mt-2">
          💡 Si ❌: Allez dans l'extension → Paramètres → Activer pour localhost
        </div>
      </div>
    </div>
  )
}
