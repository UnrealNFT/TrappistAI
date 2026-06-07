import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { useClickRef } from '@make-software/csprclick-ui'
import Home from './pages/Home'
import Generate from './pages/Generate'
import BuyCredits from './pages/BuyCredits'
import Navbar from './components/Navbar'
import WalletDebug from './components/WalletDebug'
import { getBalance } from './services/api'

function App() {
  const clickRef = useClickRef()
  const [wallet, setWallet] = useState(null)
  const [balance, setBalance] = useState(0)

  // Listen to CSPR.click events
  useEffect(() => {
    if (!clickRef) return

    // When user signs in
    clickRef.on('csprclick:signed_in', async (evt) => {
      const publicKey = evt.account.public_key
      setWallet(publicKey)
      localStorage.setItem('wallet', publicKey)
      
      // Fetch balance
      try {
        const bal = await getBalance(publicKey)
        setBalance(bal)
      } catch (error) {
        console.error('Failed to fetch balance:', error)
      }
    })

    // When user switches account
    clickRef.on('csprclick:switched_account', async (evt) => {
      const publicKey = evt.account.public_key
      setWallet(publicKey)
      localStorage.setItem('wallet', publicKey)
      
      try {
        const bal = await getBalance(publicKey)
        setBalance(bal)
      } catch (error) {
        console.error('Failed to fetch balance:', error)
      }
    })

    // When user signs out
    clickRef.on('csprclick:signed_out', () => {
      setWallet(null)
      setBalance(0)
      localStorage.removeItem('wallet')
    })
  }, [clickRef])

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
