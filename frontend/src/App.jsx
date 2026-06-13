import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { AnimatePresence } from 'framer-motion'
import { Toaster } from 'react-hot-toast'
import Home from './pages/Home'
import Generate from './pages/Generate'
import Profile from './pages/Profile'
import BuyCredits from './pages/BuyCredits'
import MyRWA from './pages/MyRWA'
import Navbar from './components/Navbar'
import BottomNav from './components/BottomNav'
import { getBalance } from './services/api'

// Component to restart scan animation on route change
function ScanlineAnimationTrigger() {
  const location = useLocation()
  
  useEffect(() => {
    // Remove class
    document.body.classList.remove('scan-active')
    
    // Add it back after a tiny delay to retrigger animation
    const timer = setTimeout(() => {
      document.body.classList.add('scan-active')
    }, 50)
    
    return () => clearTimeout(timer)
  }, [location.pathname])
  
  return null
}

function App() {
  const [wallet, setWallet] = useState(null)
  const [balance, setBalance] = useState(0)
  const [provider, setProvider] = useState(null)
  const [isMobile, setIsMobile] = useState(false)

  // Check if Casper Wallet is installed
  const isCasperWalletAvailable = () => {
    return typeof window !== 'undefined' && typeof window.CasperWalletProvider === 'function'
  }
  
  // Detect mobile
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768)
    }
    
    checkMobile()
    window.addEventListener('resize', checkMobile)
    
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

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
      const normalizedKey = publicKey.toLowerCase().trim()
      setWallet(normalizedKey)
      localStorage.setItem('wallet', normalizedKey)
      
      console.log('✅ Wallet connected:', normalizedKey)

      // Fetch balance
      try {
        const bal = await getBalance(normalizedKey)
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
      <ScanlineAnimationTrigger />
      <AnimatePresence mode="wait">
        <div className="min-h-screen bg-dark-bg">
          <Navbar 
            wallet={wallet}
            balance={balance}
            onConnect={connectWallet}
            onDisconnect={disconnectWallet}
            onRefreshBalance={refreshBalance}
          />
          
          <main className={`${isMobile ? 'pb-36' : 'pb-8'}`}>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/generate" element={
                <Generate 
                  wallet={wallet} 
                  balance={balance}
                  onBalanceUpdate={refreshBalance}
                />
              } />
              <Route path="/profile" element={
                <Profile 
                  wallet={wallet}
                />
              } />
              <Route path="/buy-credits" element={
                <BuyCredits 
                  wallet={wallet}
                  balance={balance}
                  provider={provider}
                  onPurchaseComplete={refreshBalance}
                />
              } />
              <Route path="/my-rwa" element={
                <MyRWA 
                  wallet={wallet}
                />
              } />
            </Routes>
          </main>
          
          {/* Bottom navigation - mobile only */}
          {isMobile && <BottomNav wallet={wallet} balance={balance} />}
          
          {/* Toast notifications */}
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 3000,
              style: {
                background: '#1A1A1A',
                color: '#fff',
                border: '1px solid #2A2A2A',
              },
              success: {
                iconTheme: {
                  primary: '#00D084',
                  secondary: '#fff',
                },
              },
              error: {
                iconTheme: {
                  primary: '#FF6B6B',
                  secondary: '#fff',
                },
              },
            }}
          />
        </div>
      </AnimatePresence>
    </Router>
  )
}

export default App
