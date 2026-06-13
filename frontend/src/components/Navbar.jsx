import { Link } from 'react-router-dom'
import { RefreshCw, Coins, Wallet, LogOut } from 'lucide-react'

export default function Navbar({ wallet, balance, onConnect, onDisconnect, onRefreshBalance }) {
  return (
    <nav className="glass backdrop-blur-md border-b border-green-500/30 sticky top-0 z-50">
      <div className="container mx-auto px-2 md:px-4 py-2 md:py-3 flex justify-between items-center">
        {/* Logo */}
        <Link to="/" className="flex items-center space-x-2">
          <img src="/trappist1.png" alt="TrappistAI" className="w-10 h-10 md:w-14 md:h-14 rounded-lg" />
          <span className="font-bold text-lg md:text-xl hidden sm:block">
            <span className="text-green-400">TR</span>
            <span className="text-yellow-400">A</span>
            <span className="text-green-400">PP</span>
            <span className="text-yellow-400">I</span>
            <span className="text-green-400">ST</span>
          </span>
        </Link>

        {/* Navigation - Hidden on mobile, visible on desktop */}
        <div className="hidden md:flex items-center space-x-6">
          <Link to="/" className="text-green-300/90 hover:text-green-400 transition">
            Home
          </Link>
          <Link to="/generate" className="text-green-300/90 hover:text-green-400 transition">
            Generate
          </Link>
          <Link to="/my-rwa" className="text-green-300/90 hover:text-green-400 transition">
            💎 My RWA
          </Link>
          <Link to="/marketplace" className="text-green-300/90 hover:text-green-400 transition">
            🏪 Marketplace
          </Link>
          <Link to="/profile" className="text-green-300/90 hover:text-green-400 transition">
            Profile
          </Link>
          <Link to="/buy-credits" className="text-green-300/90 hover:text-green-400 transition">
            Buy Credits
          </Link>
        </div>

        {/* Wallet */}
        <div className="flex items-center space-x-2 md:space-x-3">
          {wallet ? (
            <>
              {/* Balance */}
              <div className="flex items-center space-x-1 md:space-x-2 glass border border-green-500/30 px-2 md:px-4 py-1.5 md:py-2 rounded-lg">
                <Coins className="w-4 h-4 md:w-5 md:h-5 text-green-400" />
                <span className="text-green-300 font-semibold text-sm md:text-base">{balance}</span>
                <button
                  onClick={onRefreshBalance}
                  className="ml-1 p-1 hover:bg-green-500/20 rounded transition"
                >
                  <RefreshCw className="w-3 h-3 md:w-4 md:h-4 text-green-400" />
                </button>
              </div>

              {/* Wallet Address - Hidden on mobile */}
              <div className="hidden sm:flex glass border border-green-500/30 px-3 md:px-4 py-1.5 md:py-2 rounded-lg">
                <span className="text-green-300 font-mono text-xs md:text-sm">
                  {wallet.slice(0, 6)}...{wallet.slice(-4)}
                </span>
              </div>

              {/* Disconnect Button */}
              <button
                onClick={onDisconnect}
                className="p-1.5 md:p-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/50 rounded-lg transition"
                title="Disconnect Wallet"
              >
                <LogOut className="w-4 h-4 md:w-5 md:h-5 text-red-400" />
              </button>
            </>
          ) : (
            /* Connect Button */
            <button
              onClick={onConnect}
              className="flex items-center space-x-2 bg-green-500 text-black px-3 md:px-6 py-1.5 md:py-2 rounded-lg hover:scale-105 hover:bg-green-400 hover:shadow-lg hover:shadow-green-500/50 transition text-sm md:text-base"
            >
              <Wallet className="w-4 h-4 md:w-5 md:h-5" />
              <span className="font-semibold hidden sm:inline">Connect Wallet</span>
              <span className="font-semibold sm:hidden">Connect</span>
            </button>
          )}
        </div>
      </div>
    </nav>
  )
}
