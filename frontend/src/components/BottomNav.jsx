import { Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FaHome, FaWandMagicSparkles, FaWallet, FaUser } from 'react-icons/fa6'

export default function BottomNav({ wallet, balance }) {
  const location = useLocation()
  
  const navItems = [
    { path: '/', label: 'Home', icon: FaHome },
    { path: '/generate', label: 'Generate', icon: FaWandMagicSparkles },
    { path: '/buy-credits', label: 'Buy', icon: FaWallet },
    { path: '/profile', label: 'Profile', icon: FaUser },
  ]
  
  return (
    <motion.div
      initial={{ y: 100 }}
      animate={{ y: 0 }}
      className="fixed bottom-0 left-0 right-0 z-50 glass border-t border-white/10 safe-area-bottom"
    >
      {/* Balance bar on top of bottom nav */}
      {wallet && (
        <div className="px-4 py-2 bg-gradient-to-r from-purple-500/20 to-pink-500/20 border-b border-white/10">
          <div className="flex items-center justify-between text-xs">
            <span className="text-white/60">Your Balance</span>
            <span className="font-bold gradient-text">{balance} tokens</span>
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
                  isActive ? 'text-purple-500' : 'text-gray-400'
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
                    className="absolute top-0 w-12 h-1 bg-gradient-to-r from-purple-500 to-pink-500 rounded-b-full"
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
