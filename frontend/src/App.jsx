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

  // Connect wallet
  const connectWallet = async () => {
    if (!window.casperlabsHelper) {
      alert('Casper Wallet not found! Please install Casper Wallet extension.')
      window.open('https://www.casperwallet.io/', '_blank')
      return
    }

    try {
      const connected = await window.casperlabsHelper.requestConnection()
      if (connected) {
        const publicKey = await window.casperlabsHelper.getActivePublicKey()
        setWallet(publicKey)
        localStorage.setItem('wallet', publicKey)
        
        // Fetch balance
        const bal = await getBalance(publicKey)
        setBalance(bal)
      }
    } catch (error) {
      console.error('Wallet connection failed:', error)
      alert('Failed to connect wallet')
    }
  }

  // Disconnect wallet
  const disconnectWallet = () => {
    setWallet(null)
    setBalance(0)
    localStorage.removeItem('wallet')
    window.casperlabsHelper?.disconnectFromSite()
  }

  // Auto-connect on mount
  useEffect(() => {
    const savedWallet = localStorage.getItem('wallet')
    if (savedWallet && window.casperlabsHelper) {
      window.casperlabsHelper.isConnected().then(connected => {
        if (connected) {
          setWallet(savedWallet)
          getBalance(savedWallet).then(setBalance).catch(console.error)
        }
      })
    }
  }, [])

  // Refresh balance
  const refreshBalance = async () => {
    if (wallet) {
      const bal = await getBalance(wallet)
      setBalance(bal)
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
