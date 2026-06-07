import { Link } from 'react-router-dom'
import { RefreshCw, Coins, Wallet, LogOut } from 'lucide-react'

export default function Navbar({ wallet, balance, onConnect, onDisconnect, onRefreshBalance }) {
  return (
    <nav className="bg-white/10 backdrop-blur-md border-b border-white/20 sticky top-0 z-50">
      <div className="container mx-auto px-4 py-3 flex justify-between items-center">
        {/* Logo */}
        <Link to="/" className="flex items-center space-x-2">
          <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-xl">T</span>
          </div>
          <span className="text-white font-bold text-xl">TrappistAI</span>
        </Link>

        {/* Navigation */}
        <div className="flex items-center space-x-6">
          <Link to="/" className="text-white/90 hover:text-white transition">
            Home
          </Link>
          <Link to="/generate" className="text-white/90 hover:text-white transition">
            Generate
          </Link>
          <Link to="/buy" className="text-white/90 hover:text-white transition">
            Buy Credits
          </Link>
        </div>

        {/* Wallet */}
        <div className="flex items-center space-x-3">
          {wallet ? (
            <>
              {/* Balance */}
              <div className="flex items-center space-x-2 bg-white/20 px-4 py-2 rounded-lg">
                <Coins className="w-5 h-5 text-yellow-300" />
                <span className="text-white font-semibold">{balance}</span>
                <button
                  onClick={onRefreshBalance}
                  className="ml-1 p-1 hover:bg-white/20 rounded transition"
                >
                  <RefreshCw className="w-4 h-4 text-white" />
                </button>
              </div>

              {/* Wallet Address */}
              <div className="bg-white/20 px-4 py-2 rounded-lg">
                <span className="text-white font-mono text-sm">
                  {wallet.slice(0, 6)}...{wallet.slice(-4)}
                </span>
              </div>

              {/* Disconnect Button */}
              <button
                onClick={onDisconnect}
                className="p-2 bg-red-500/20 hover:bg-red-500/30 rounded-lg transition"
                title="Disconnect Wallet"
              >
                <LogOut className="w-5 h-5 text-white" />
              </button>
            </>
          ) : (
            /* Connect Button */
            <button
              onClick={onConnect}
              className="flex items-center space-x-2 bg-gradient-to-r from-purple-500 to-pink-500 px-6 py-2 rounded-lg hover:scale-105 transition"
            >
              <Wallet className="w-5 h-5 text-white" />
              <span className="text-white font-semibold">Connect Wallet</span>
            </button>
          )}
        </div>
      </div>
    </nav>
  )
}
