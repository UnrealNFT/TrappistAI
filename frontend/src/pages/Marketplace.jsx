import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShoppingCart, Image, Music, Box, TrendingUp, Gem, X, Check } from 'lucide-react';

const Marketplace = ({ wallet }) => {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedListing, setSelectedListing] = useState(null);
  const [percentage, setPercentage] = useState(50);
  const [buying, setBuying] = useState(false);

  useEffect(() => {
    fetchListings();
  }, []);

  const fetchListings = async () => {
    try {
      setLoading(true);
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_URL}/api/marketplace/listings?status=active`);
      const data = await response.json();
      
      if (data.success) {
        setListings(data.listings);
      }
    } catch (error) {
      console.error('Error fetching listings:', error);
    } finally {
      setLoading(false);
    }
  };

  const getAssetIcon = (assetType) => {
    switch (assetType) {
      case 'image':
        return <Image className="w-5 h-5" />;
      case 'music':
        return <Music className="w-5 h-5" />;
      case '3d':
        return <Box className="w-5 h-5" />;
      default:
        return <Gem className="w-5 h-5" />;
    }
  };

  const handleBuy = async () => {
    if (!wallet) {
      alert('Please connect your wallet first');
      return;
    }

    const partsToBuy = Math.floor((percentage / 100) * selectedListing.availableParts);
    const totalCost = (partsToBuy * selectedListing.pricePerPart).toFixed(4);

    try {
      setBuying(true);

      // TODO: Integrate real Casper Wallet payment
      // For now, we'll simulate the transaction
      console.log('Buying:', { partsToBuy, totalCost });

      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_URL}/api/marketplace/buy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          listingId: selectedListing.listingId,
          buyerWallet: wallet,
          partsToBuy: partsToBuy,
          csprTxHash: 'mock_tx_hash_' + Date.now()
        })
      });

      const data = await response.json();

      if (data.success) {
        alert(`✅ Success! You now own ${percentage}% of RWDA #${selectedListing.tokenId}`);
        setSelectedListing(null);
        fetchListings();
      } else {
        alert('❌ Purchase failed: ' + data.detail);
      }
    } catch (error) {
      console.error('Buy error:', error);
      alert('❌ Purchase failed');
    } finally {
      setBuying(false);
    }
  };

  if (!wallet) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-900 via-black to-blue-900 pt-20 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center py-20">
            <ShoppingCart className="w-16 h-16 mx-auto mb-4 text-purple-400" />
            <h2 className="text-2xl font-bold text-white mb-2">Connect Your Wallet</h2>
            <p className="text-gray-400">Connect your Casper wallet to browse the marketplace</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-black to-blue-900 pt-20 px-4">
      <div className="max-w-7xl mx-auto pb-20">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <ShoppingCart className="w-8 h-8 text-purple-400" />
            <h1 className="text-4xl font-bold text-white">RWA Marketplace</h1>
          </div>
          <p className="text-gray-400">
            Buy fractional ownership of AI-generated digital assets
          </p>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="text-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto mb-4"></div>
            <p className="text-gray-400">Loading marketplace...</p>
          </div>
        )}

        {/* Empty State */}
        {!loading && listings.length === 0 && (
          <div className="text-center py-20">
            <ShoppingCart className="w-16 h-16 mx-auto mb-4 text-gray-600" />
            <h2 className="text-2xl font-bold text-white mb-2">No Listings Yet</h2>
            <p className="text-gray-400">Be the first to list your RWA token!</p>
          </div>
        )}

        {/* Listings Grid */}
        {!loading && listings.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {listings.map((listing) => (
              <motion.div
                key={listing.listingId}
                whileHover={{ scale: 1.02 }}
                className="bg-gray-900/50 border border-purple-500/30 rounded-lg overflow-hidden hover:border-purple-500/60 transition-all duration-300 cursor-pointer"
                onClick={() => setSelectedListing(listing)}
              >
                {/* Asset Preview */}
                <div className="aspect-square bg-gray-800/50 relative overflow-hidden">
                  {listing.asset.type === 'image' && listing.asset.url && (
                    <img
                      src={listing.asset.url}
                      alt={listing.asset.prompt || 'AI Asset'}
                      className="w-full h-full object-cover"
                    />
                  )}
                  
                  {listing.asset.type === 'music' && (
                    <div className="flex items-center justify-center h-full">
                      <Music className="w-24 h-24 text-purple-400" />
                    </div>
                  )}
                  
                  {listing.asset.type === '3d' && (
                    <div className="flex items-center justify-center h-full">
                      <Box className="w-24 h-24 text-blue-400" />
                    </div>
                  )}

                  {/* Asset Type Badge */}
                  <div className="absolute top-2 left-2 px-3 py-1 bg-black/70 rounded-full flex items-center gap-2">
                    {getAssetIcon(listing.asset.type)}
                    <span className="text-sm font-medium capitalize">{listing.asset.type}</span>
                  </div>

                  {/* Token ID */}
                  <div className="absolute top-2 right-2 px-3 py-1 bg-purple-600/80 rounded-full">
                    <span className="text-sm font-bold">#{listing.tokenId}</span>
                  </div>
                </div>

                {/* Listing Info */}
                <div className="p-4">
                  {/* Prompt */}
                  {listing.asset.prompt && (
                    <p className="text-white text-sm mb-3 line-clamp-2">
                      "{listing.asset.prompt}"
                    </p>
                  )}

                  {/* Price */}
                  <div className="mb-3">
                    <p className="text-xs text-gray-400">Floor Price</p>
                    <p className="text-2xl font-bold text-purple-400">
                      {listing.pricePerPart} CSPR<span className="text-sm text-gray-400">/part</span>
                    </p>
                  </div>

                  {/* Available Parts */}
                  <div className="mb-3">
                    <div className="flex justify-between text-xs text-gray-400 mb-1">
                      <span>Available</span>
                      <span>{listing.availableParts} / {listing.partsForSale} parts</span>
                    </div>
                    <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-green-500 to-green-400"
                        style={{ width: `${(listing.availableParts / listing.partsForSale) * 100}%` }}
                      />
                    </div>
                  </div>

                  {/* Buy Button */}
                  <button className="w-full py-2 bg-purple-600 hover:bg-purple-700 rounded-lg font-bold transition-colors flex items-center justify-center gap-2">
                    <ShoppingCart className="w-4 h-4" />
                    Buy Parts
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        )}

        {/* Buy Modal */}
        <AnimatePresence>
          {selectedListing && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
              onClick={() => setSelectedListing(null)}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="bg-gray-900 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto"
                onClick={(e) => e.stopPropagation()}
              >
                {/* Modal Header */}
                <div className="sticky top-0 bg-gray-900 border-b border-gray-800 p-6 flex items-center justify-between">
                  <h2 className="text-2xl font-bold text-white">Buy RWA Parts</h2>
                  <button
                    onClick={() => setSelectedListing(null)}
                    className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
                  >
                    <X className="w-6 h-6" />
                  </button>
                </div>

                {/* Modal Content */}
                <div className="p-6">
                  {/* Asset Preview */}
                  <div className="mb-6">
                    <div className="aspect-video bg-gray-800 rounded-lg overflow-hidden mb-4">
                      {selectedListing.asset.type === 'image' && (
                        <img
                          src={selectedListing.asset.url}
                          alt={selectedListing.asset.prompt}
                          className="w-full h-full object-cover"
                        />
                      )}
                      {selectedListing.asset.type === 'music' && (
                        <div className="flex items-center justify-center h-full">
                          <Music className="w-32 h-32 text-purple-400" />
                        </div>
                      )}
                      {selectedListing.asset.type === '3d' && (
                        <div className="flex items-center justify-center h-full">
                          <Box className="w-32 h-32 text-blue-400" />
                        </div>
                      )}
                    </div>
                    <h3 className="text-xl font-bold text-white mb-2">
                      {selectedListing.asset.prompt || `RWDA #${selectedListing.tokenId}`}
                    </h3>
                    <p className="text-gray-400 text-sm">Model: {selectedListing.asset.model}</p>
                  </div>

                  {/* Info Grid */}
                  <div className="grid grid-cols-2 gap-4 mb-6">
                    <div className="bg-gray-800 rounded-lg p-4">
                      <p className="text-gray-400 text-sm mb-1">Available Parts</p>
                      <p className="text-2xl font-bold">{selectedListing.availableParts}</p>
                    </div>
                    <div className="bg-gray-800 rounded-lg p-4">
                      <p className="text-gray-400 text-sm mb-1">Price per Part</p>
                      <p className="text-2xl font-bold text-purple-400">{selectedListing.pricePerPart} CSPR</p>
                    </div>
                  </div>

                  {/* Slider Section */}
                  <div className="bg-gray-800 rounded-lg p-6 mb-6">
                    <h3 className="text-lg font-semibold mb-4">Buy Amount</h3>
                    
                    {/* Slider */}
                    <div className="mb-6">
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={percentage}
                        onChange={(e) => setPercentage(parseInt(e.target.value))}
                        className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-purple-600"
                      />
                      
                      {/* Markers */}
                      <div className="flex justify-between text-sm text-gray-400 mt-2">
                        <span>0%</span>
                        <span>25%</span>
                        <span>50%</span>
                        <span>75%</span>
                        <span>100%</span>
                      </div>
                    </div>

                    {/* Quick Buy Buttons */}
                    <div className="grid grid-cols-4 gap-2 mb-6">
                      {[25, 50, 75, 100].map((percent) => (
                        <button
                          key={percent}
                          onClick={() => setPercentage(percent)}
                          className={`py-2 rounded-lg font-semibold transition-colors ${
                            percentage === percent
                              ? 'bg-purple-600 text-white'
                              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                          }`}
                        >
                          {percent}%
                        </button>
                      ))}
                    </div>

                    {/* Ownership Gauge */}
                    <div className="mb-6">
                      <div className="h-12 bg-gray-700 rounded-lg relative overflow-hidden">
                        <motion.div
                          className="absolute h-full bg-gradient-to-r from-green-500 to-green-400 flex items-center justify-end pr-3"
                          animate={{ width: `${percentage}%` }}
                          transition={{ duration: 0.3 }}
                        >
                          {percentage > 15 && (
                            <span className="text-xs font-bold text-white">
                              YOU: {percentage}%
                            </span>
                          )}
                        </motion.div>
                        <div
                          className="absolute h-full bg-gray-600 right-0 flex items-center justify-start pl-3"
                          style={{ width: `${100 - percentage}%` }}
                        >
                          {(100 - percentage) > 15 && (
                            <span className="text-xs text-gray-300">
                              SELLER: {100 - percentage}%
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Purchase Summary */}
                    <div className="bg-gray-900 rounded-lg p-4 mb-4">
                      <div className="flex justify-between mb-2">
                        <span className="text-gray-400">Parts to buy</span>
                        <span className="font-bold">
                          {Math.floor((percentage / 100) * selectedListing.availableParts)} parts ({percentage}%)
                        </span>
                      </div>
                      <div className="flex justify-between mb-2">
                        <span className="text-gray-400">Total cost</span>
                        <motion.span 
                          key={percentage}
                          initial={{ scale: 1.1, color: '#a855f7' }}
                          animate={{ scale: 1, color: '#ffffff' }}
                          className="font-bold text-purple-400 text-xl"
                        >
                          {(Math.floor((percentage / 100) * selectedListing.availableParts) * selectedListing.pricePerPart).toFixed(4)} CSPR
                        </motion.span>
                      </div>
                      <div className="border-t border-gray-700 pt-2 mt-2">
                        <div className="flex items-center gap-2 text-sm text-gray-400 mb-1">
                          <Check className="w-4 h-4 text-green-400" />
                          <span>Full commercial usage rights</span>
                        </div>
                        <div className="flex items-center gap-2 text-sm text-gray-400 mb-1">
                          <Check className="w-4 h-4 text-green-400" />
                          <span>Proportional revenue share ({percentage}%)</span>
                        </div>
                        <div className="flex items-center gap-2 text-sm text-gray-400">
                          <Check className="w-4 h-4 text-green-400" />
                          <span>Voting power: {Math.floor((percentage / 100) * selectedListing.availableParts)} votes</span>
                        </div>
                      </div>
                    </div>

                    {/* Buy Button */}
                    <button 
                      onClick={handleBuy}
                      disabled={buying || percentage === 0}
                      className="w-full py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg font-bold text-lg transition-colors flex items-center justify-center gap-2"
                    >
                      {buying ? (
                        <>
                          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                          Processing...
                        </>
                      ) : (
                        <>
                          <ShoppingCart className="w-5 h-5" />
                          Buy Now - {(Math.floor((percentage / 100) * selectedListing.availableParts) * selectedListing.pricePerPart).toFixed(4)} CSPR
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default Marketplace;
