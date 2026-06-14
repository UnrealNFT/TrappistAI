import { Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FaHouse, FaWandMagicSparkles, FaWallet, FaUser, FaGem, FaStore } from 'react-icons/fa6'

export default function BottomNav({ wallet, balance }) {
  const location = useLocation()
  
  const navItems = [
    { path: '/', label: 'Home', icon: FaHouse },
    { path: '/generate', label: 'Generate', icon: FaWandMagicSparkles },
    { path: '/marketplace', label: 'Market', icon: FaStore },
    { path: '/profile', label: 'Profile', icon: FaUser },
    { path: '/buy-credits', label: 'Buy', icon: FaWallet },
  ]
  
  return (
    <motion.div
      initial={{ y: 100 }}
      animate={{ y: 0 }}
      className="fixed bottom-0 left-0 right-0 z-50 glass border-t border-green-500/30 safe-area-bottom"
    >
      {/* Balance bar on top of bottom nav */}
      {wallet && (
        <div className="px-4 py-2 bg-green-500/10 border-b border-green-500/30">
          <div className="flex items-center justify-between text-xs">
            <span className="text-green-300/60">Your Balance</span>
            <span className="font-bold text-green-400 animate-glow">{balance} tokens</span>
          </div>
        </div>
      )}
      
      <div className="flex items-center justify-around h-16 px-2">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = location.pathname === item.path
          
          return (
            <Link
              key={item.path}
              to={item.path}
              className="flex flex-col items-center justify-center flex-1 h-full group relative"
            >
              <motion.div
                whileTap={{ scale: 0.9 }}
                className={`flex flex-col items-center ${
                  isActive ? 'text-green-400' : 'text-green-300/50'
                }`}
              >
                <Icon className={`text-xl mb-1 transition-all duration-300 ${
                  isActive ? 'scale-110' : 'group-hover:scale-105'
                }`} />
                <span className={`text-xs font-medium ${
                  isActive ? 'font-semibold' : ''
                }`}>
                  {item.label}
                </span>
                
                {isActive && (
                  <motion.div
                    layoutId="bottom-nav-indicator"
                    className="absolute top-0 w-12 h-1 bg-green-500 rounded-b-full shadow-lg shadow-green-500/50"
                    transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                  />
                )}
              </motion.div>
            </Link>
          )
        })}
      </div>
    </motion.div>
  )
}
