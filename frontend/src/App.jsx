import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Home from './pages/Home'
import Generate from './pages/Generate'
import BuyCredits from './pages/BuyCredits'
import Navbar from './components/Navbar'
import WalletDebug from './components/WalletDebug'
import { getBalance } from './services/api'

function App() {
  const [wallet, setWallet] = useState(null)
  const [balance, setBalance] = useState(0)
  const [provider, setProvider] = useState(null)

  // Check if Casper Wallet is installed
  const isCasperWalletAvailable = () => {
    return typeof window !== 'undefined' && typeof window.CasperWalletProvider === 'function'
  }

  // Connect wallet function
  const connectWallet = async () => {
    console.log('🔗 Connecting to Casper Wallet...')
    
    if (!isCasperWalletAvailable()) {
      alert('Casper Wallet not found! Please install Casper Wallet extension.')
      window.open('https://www.casperwallet.io/', '_blank')
      return
    }

    try {
      // Create provider instance
      const walletProvider = window.CasperWalletProvider()
      setProvider(walletProvider)
      console.log('✅ Provider created')

      // Request connection
      const isConnected = await walletProvider.requestConnection()
      
      if (!isConnected) {
        alert('Connection rejected by user')
        return
      }

      // Get active public key
      const publicKey = await walletProvider.getActivePublicKey()
      setWallet(publicKey)
      localStorage.setItem('wallet', publicKey)
      
      console.log('✅ Wallet connected:', publicKey)

      // Fetch balance
      try {
        const bal = await getBalance(publicKey)
        setBalance(bal)
      } catch (error) {
        console.error('Failed to fetch balance:', error)
      }
    } catch (error) {
      console.error('❌ Wallet connection failed:', error)
      alert('Failed to connect wallet: ' + error.message)
    }
  }

  // Disconnect wallet
  const disconnectWallet = () => {
    setWallet(null)
    setBalance(0)
    setProvider(null)
    localStorage.removeItem('wallet')
    console.log('🔌 Wallet disconnected')
  }

  // Auto-connect on mount if previously connected
  useEffect(() => {
    const savedWallet = localStorage.getItem('wallet')
    if (savedWallet && isCasperWalletAvailable()) {
      // Try to reconnect
      connectWallet().catch(() => {
        // Silently fail, user can reconnect manually
        localStorage.removeItem('wallet')
      })
    }
  }, [])

  // Refresh balance
  const refreshBalance = async () => {
    if (wallet) {
      try {
        const bal = await getBalance(wallet)
        setBalance(bal)
      } catch (error) {
        console.error('Failed to refresh balance:', error)
      }
    }
  }

  return (
    <Router>
      <div className="min-h-screen">
        <Navbar 
          wallet={wallet}
          balance={balance}
          onConnect={connectWallet}
          onDisconnect={disconnectWallet}
          onRefreshBalance={refreshBalance}
        />
        
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/generate" element={
            <Generate 
              wallet={wallet} 
              balance={balance}
              onBalanceUpdate={refreshBalance}
            />
          } />
          <Route path="/buy" element={
            <BuyCredits 
              wallet={wallet}
              onPurchaseComplete={refreshBalance}
            />
          } />
        </Routes>
        
        {/* Debug panel */}
        <WalletDebug />
      </div>
    </Router>
  )
}

export default App
