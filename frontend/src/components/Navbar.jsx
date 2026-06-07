import { Link } from 'react-router-dom'
import { RefreshCw, Coins, Wallet, LogOut } from 'lucide-react'

export default function Navbar({ wallet, balance, onConnect, onDisconnect, onRefreshBalance }) {
  return (
    <nav className="glass backdrop-blur-md border-b border-green-500/30 sticky top-0 z-50">
      <div className="container mx-auto px-4 py-3 flex justify-between items-center">
        {/* Logo */}
        <Link to="/" className="flex items-center space-x-2">
          <img src="/trappist1.png" alt="TrappistAI" className="w-10 h-10 rounded-lg" />
          <span className="text-green-400 font-bold text-xl">TrappistAI</span>
        </Link>

        {/* Navigation */}
        <div className="flex items-center space-x-6">
          <Link to="/" className="text-green-300/90 hover:text-green-400 transition">
            Home
          </Link>
          <Link to="/generate" className="text-green-300/90 hover:text-green-400 transition">
            Generate
          </Link>
          <Link to="/buy-credits" className="text-green-300/90 hover:text-green-400 transition">
            Buy Credits
          </Link>
        </div>

        {/* Wallet */}
        <div className="flex items-center space-x-3">
          {wallet ? (
            <>
              {/* Balance */}
              <div className="flex items-center space-x-2 glass border border-green-500/30 px-4 py-2 rounded-lg">
                <Coins className="w-5 h-5 text-green-400" />
                <span className="text-green-300 font-semibold">{balance}</span>
                <button
                  onClick={onRefreshBalance}
                  className="ml-1 p-1 hover:bg-green-500/20 rounded transition"
                >
                  <RefreshCw className="w-4 h-4 text-green-400" />
                </button>
              </div>

              {/* Wallet Address */}
              <div className="glass border border-green-500/30 px-4 py-2 rounded-lg">
                <span className="text-green-300 font-mono text-sm">
                  {wallet.slice(0, 6)}...{wallet.slice(-4)}
                </span>
              </div>

              {/* Disconnect Button */}
              <button
                onClick={onDisconnect}
                className="p-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/50 rounded-lg transition"
                title="Disconnect Wallet"
              >
                <LogOut className="w-5 h-5 text-red-400" />
              </button>
            </>
          ) : (
            /* Connect Button */
            <button
              onClick={onConnect}
              className="flex items-center space-x-2 bg-green-500 text-black px-6 py-2 rounded-lg hover:scale-105 hover:bg-green-400 hover:shadow-lg hover:shadow-green-500/50 transition"
            >
              <Wallet className="w-5 h-5" />
              <span className="font-semibold">Connect Wallet</span>
            </button>
          )}
        </div>
      </div>
    </nav>
  )
}
