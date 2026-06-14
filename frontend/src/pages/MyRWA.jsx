import { useState, useEffect } from 'react';
import { Gem, Image, Music, Box, ExternalLink, Calendar, Hash, Store, X } from 'lucide-react';

const MyRWA = ({ wallet }) => {
  const [tokens, setTokens] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showListModal, setShowListModal] = useState(false);
  const [selectedToken, setSelectedToken] = useState(null);
  const [listForm, setListForm] = useState({
    partsForSale: 50,
    pricePerPart: 10
  });
  const [listLoading, setListLoading] = useState(false);

  useEffect(() => {
    if (wallet) {
      fetchTokens();
    }
  }, [wallet]);

  const fetchTokens = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(
        `${API_URL}/api/rwa/my-tokens/${wallet}`
      );
      
      if (!response.ok) {
        throw new Error('Failed to fetch RWA tokens');
      }
      
      const data = await response.json();
      setTokens(data.tokens || []);
    } catch (err) {
      console.error('Error fetching RWA tokens:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getAssetIcon = (assetType) => {
    switch (assetType) {
      case 'image':
        return <Image className="w-6 h-6" />;
      case 'music':
        return <Music className="w-6 h-6" />;
      case '3d':
        return <Box className="w-6 h-6" />;
      default:
        return <Gem className="w-6 h-6" />;
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleListClick = (token) => {
    setSelectedToken(token);
    setShowListModal(true);
  };

  const handleListSubmit = async () => {
    if (!selectedToken || !wallet) return;

    try {
      setListLoading(true);
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      
      const response = await fetch(`${API_URL}/api/marketplace/list`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tokenId: selectedToken.tokenId,
          sellerWallet: wallet,
          partsForSale: listForm.partsForSale,
          pricePerPart: listForm.pricePerPart
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to create listing');
      }

      alert(`✅ Listed successfully! Listing ID: #${data.listingId}`);
      setShowListModal(false);
      
      // Redirect to marketplace
      window.location.href = '/marketplace';

    } catch (err) {
      console.error('List error:', err);
      alert('❌ ' + err.message);
    } finally {
      setListLoading(false);
    }
  };

  if (!wallet) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-900 via-black to-blue-900 pt-20 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center py-20">
            <Gem className="w-16 h-16 mx-auto mb-4 text-purple-400" />
            <h2 className="text-2xl font-bold text-white mb-2">Connect Your Wallet</h2>
            <p className="text-gray-400">Please connect your Casper wallet to view your RWA tokens</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-black to-blue-900 pt-20 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <Gem className="w-8 h-8 text-purple-400" />
            <h1 className="text-4xl font-bold text-white">My RWA Tokens</h1>
          </div>
          <p className="text-gray-400">
            Your AI-generated assets tokenized as NFTs on Casper blockchain
          </p>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="text-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto mb-4"></div>
            <p className="text-gray-400">Loading your RWA tokens...</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-6 mb-6">
            <p className="text-red-400">❌ {error}</p>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && tokens.length === 0 && (
          <div className="text-center py-20">
            <Gem className="w-16 h-16 mx-auto mb-4 text-gray-600" />
            <h2 className="text-2xl font-bold text-white mb-2">No RWA Tokens Yet</h2>
            <p className="text-gray-400 mb-6">
              Generate AI content on Telegram and tokenize it as RWA NFT!
            </p>
            <a
              href="https://t.me/PiraAi_bot"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
            >
              Open Telegram Bot
            </a>
          </div>
        )}

        {/* Tokens Grid */}
        {!loading && !error && tokens.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {tokens.map((token) => (
              <div
                key={token.tokenId}
                className="bg-gray-900/50 border border-purple-500/30 rounded-lg overflow-hidden hover:border-purple-500/60 transition-all duration-300 group"
              >
                {/* Asset Preview */}
                <div className="aspect-square bg-gray-800/50 relative overflow-hidden">
                  {token.assetType === 'image' && token.assetUrl && (
                    <img
                      src={token.assetUrl}
                      alt={token.prompt || 'AI Generated'}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                  )}
                  
                  {token.assetType === 'music' && (
                    <div className="flex items-center justify-center h-full">
                      <Music className="w-24 h-24 text-purple-400" />
                    </div>
                  )}
                  
                  {token.assetType === '3d' && (
                    <div className="flex items-center justify-center h-full">
                      <Box className="w-24 h-24 text-blue-400" />
                    </div>
                  )}

                  {/* Asset Type Badge */}
                  <div className="absolute top-2 left-2 px-3 py-1 bg-black/70 rounded-full flex items-center gap-2">
                    {getAssetIcon(token.assetType)}
                    <span className="text-sm font-medium capitalize">{token.assetType}</span>
                  </div>

                  {/* Token ID Badge */}
                  <div className="absolute top-2 right-2 px-3 py-1 bg-purple-600/80 rounded-full">
                    <span className="text-sm font-bold">#{token.tokenId}</span>
                  </div>
                </div>

                {/* Token Info */}
                <div className="p-4">
                  {/* Prompt */}
                  {token.prompt && (
                    <p className="text-white text-sm mb-3 line-clamp-2">
                      "{token.prompt}"
                    </p>
                  )}

                  {/* Model */}
                  {token.model && (
                    <div className="flex items-center gap-2 text-xs text-gray-400 mb-2">
                      <Hash className="w-3 h-3" />
                      <span>{token.model}</span>
                    </div>
                  )}

                  {/* Created Date */}
                  <div className="flex items-center gap-2 text-xs text-gray-400 mb-4">
                    <Calendar className="w-3 h-3" />
                    <span>{formatDate(token.createdAt)}</span>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2">
                    {token.assetUrl && (
                      <a
                        href={token.assetUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex-1 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-white text-sm rounded-lg transition-colors flex items-center justify-center gap-2"
                      >
                        <ExternalLink className="w-4 h-4" />
                        View
                      </a>
                    )}
                    
                    <button
                      onClick={() => handleListClick(token)}
                      className="flex-1 px-3 py-2 bg-green-600 hover:bg-green-700 text-white text-sm rounded-lg transition-colors flex items-center justify-center gap-2"
                    >
                      <Store className="w-4 h-4" />
                      List
                    </button>
                    
                    {token.csprTxHash && (
                      <a
                        href={`https://cspr.live/deploy/${token.csprTxHash}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex-1 px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm rounded-lg transition-colors flex items-center justify-center gap-2"
                      >
                        <Gem className="w-4 h-4" />
                        Explorer
                      </a>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* List Modal */}
      {showListModal && selectedToken && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-purple-500/50 rounded-lg max-w-md w-full p-6 relative">
            {/* Close button */}
            <button
              onClick={() => setShowListModal(false)}
              className="absolute top-4 right-4 text-gray-400 hover:text-white transition"
            >
              <X className="w-5 h-5" />
            </button>

            {/* Header */}
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-white mb-2">List on Marketplace</h2>
              <p className="text-gray-400 text-sm">
                Token #{selectedToken.tokenId}: {selectedToken.prompt}
              </p>
              <p className="text-purple-400 text-xs mt-1">
                Total: {selectedToken.totalShares?.toLocaleString() || 100} parts (1 part = {((100 / (selectedToken.totalShares || 100)).toFixed(4))}%)
              </p>
            </div>

            {/* Form */}
            <div className="space-y-4">
              {/* Parts for Sale */}
              <div>
                <label className="block text-white font-medium mb-2">
                  Parts to Sell (1-{selectedToken.totalShares?.toLocaleString() || 100})
                </label>
                <input
                  type="number"
                  min="1"
                  max={selectedToken.totalShares || 100}
                  value={listForm.partsForSale}
                  onChange={(e) => setListForm({ ...listForm, partsForSale: parseInt(e.target.value) || 1 })}
                  className="w-full bg-gray-800 border border-gray-700 text-white px-4 py-2 rounded-lg focus:outline-none focus:border-purple-500"
                />
                <p className="text-gray-500 text-xs mt-1">
                  You'll keep {((selectedToken.totalShares || 100) - listForm.partsForSale).toLocaleString()} parts ({(((selectedToken.totalShares || 100) - listForm.partsForSale) / (selectedToken.totalShares || 100) * 100).toFixed(2)}% ownership)
                </p>
              </div>

              {/* Price per Part */}
              <div>
                <label className="block text-white font-medium mb-2">
                  Price per Part (CSPR)
                </label>
                <input
                  type="number"
                  min="0.1"
                  step="0.1"
                  value={listForm.pricePerPart}
                  onChange={(e) => setListForm({ ...listForm, pricePerPart: parseFloat(e.target.value) || 0.1 })}
                  className="w-full bg-gray-800 border border-gray-700 text-white px-4 py-2 rounded-lg focus:outline-none focus:border-purple-500"
                />
                <p className="text-gray-500 text-xs mt-1">
                  Total: {(listForm.partsForSale * listForm.pricePerPart).toFixed(2)} CSPR for all parts
                </p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowListModal(false)}
                className="flex-1 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition"
              >
                Cancel
              </button>
              <button
                onClick={handleListSubmit}
                disabled={listLoading}
                className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {listLoading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Listing...
                  </>
                ) : (
                  <>
                    <Store className="w-4 h-4" />
                    List for Sale
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MyRWA;
