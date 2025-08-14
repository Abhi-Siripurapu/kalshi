import React, { useState, useEffect, useRef } from 'react'
// import { Activity, TrendingUp, TrendingDown, Wifi, WifiOff, AlertTriangle, Clock, DollarSign } from 'lucide-react'

interface VenueHealth {
  status: string
  latency_p50_ms?: number
  latency_p95_ms?: number
  subscribed_markets?: number
  stale_markets?: number
  reason?: string
}

interface SystemStatus {
  timestamp: number
  venues: Record<string, VenueHealth>
  api_status: string
  redis_connected: boolean
}

interface BookData {
  ts_ns: number
  bids: Array<{px_cents: number, qty: number}>
  asks: Array<{px_cents: number, qty: number}>
  best_bid?: number
  best_ask?: number
  mid_px?: number
  stored_at: number
  market_id?: string
  outcome_id?: string
}

interface MarketInfo {
  market_id: string
  title: string
  subtitle?: string
  ticker: string
  close_time: string
  volume_24h?: number
}

function App() {
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [books, setBooks] = useState<Record<string, BookData>>({})
  const [markets, setMarkets] = useState<Record<string, MarketInfo>>({})
  const [connected, setConnected] = useState(false)
  const [events, setEvents] = useState<Array<any>>([])
  const [selectedMarket, setSelectedMarket] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    // Connect to WebSocket
    const connectWebSocket = () => {
      const ws = new WebSocket('ws://localhost:8000/ws')
      wsRef.current = ws

      ws.onopen = () => {
        console.log('Connected to WebSocket')
        setConnected(true)
        
        // Subscribe to events
        ws.send(JSON.stringify({
          type: 'subscribe',
          channels: ['books', 'health', 'events']
        }))
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          setLastUpdate(new Date())
          
          if (message.type === 'status') {
            setStatus(message.data)
          } else if (message.type === 'event') {
            const eventData = message.data
            setEvents(prev => [eventData, ...prev.slice(0, 49)]) // Keep last 50 events
            
            // Update books if this is a book event
            if (eventData.type === 'book_snapshot') {
              const newBooks: Record<string, BookData> = {}
              for (const book of eventData.data) {
                const key = `${book.market_id}_${book.outcome_id}`
                newBooks[key] = {
                  ts_ns: book.ts_ns,
                  bids: book.bids,
                  asks: book.asks,
                  best_bid: book.best_bid,
                  best_ask: book.best_ask,
                  mid_px: book.mid_px,
                  stored_at: Date.now(),
                  market_id: book.market_id,
                  outcome_id: book.outcome_id
                }
              }
              setBooks(prev => ({ ...prev, ...newBooks }))
            }
            
            // Update market info
            if (eventData.type === 'market_info') {
              const marketData = eventData.data
              setMarkets(prev => ({
                ...prev,
                [marketData.market_id]: marketData
              }))
            }
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      ws.onclose = () => {
        console.log('WebSocket disconnected')
        setConnected(false)
        // Reconnect after 2 seconds
        setTimeout(connectWebSocket, 2000)
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
    }

    connectWebSocket()

    // Cleanup
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  // Fetch initial data
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        // Get status
        const statusResponse = await fetch('http://localhost:8000/status')
        if (statusResponse.ok) {
          const statusData = await statusResponse.json()
          setStatus(statusData)
        }

        // Get books
        const booksResponse = await fetch('http://localhost:8000/books')
        if (booksResponse.ok) {
          const booksData = await booksResponse.json()
          setBooks(booksData.books || {})
        }
      } catch (error) {
        console.error('Error fetching initial data:', error)
      }
    }

    fetchInitialData()
  }, [])

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'healthy': return 'text-green-400'
      case 'degraded': return 'text-yellow-400'  
      case 'down': return 'text-red-400'
      default: return 'text-gray-400'
    }
  }

  const getStatusBg = (status?: string) => {
    switch (status) {
      case 'healthy': return 'bg-green-500'
      case 'degraded': return 'bg-yellow-500'
      case 'down': return 'bg-red-500'
      default: return 'bg-gray-500'
    }
  }

  const formatPrice = (cents?: number) => {
    return cents ? `${cents}¢` : '--'
  }

  const formatSpread = (bid?: number, ask?: number) => {
    if (!bid || !ask) return '--'
    const spread = ask - bid
    return `${spread}¢ (${((spread / ((bid + ask) / 2)) * 100).toFixed(1)}%)`
  }

  const getMarketTitle = (marketId: string) => {
    const market = markets[marketId]
    return market?.title || marketId
  }

  const selectedBooks = selectedMarket 
    ? Object.entries(books).filter(([key]) => key.startsWith(selectedMarket))
    : Object.entries(books)

  return (
    <div 
      className="min-h-screen bg-gray-950 text-gray-100 font-mono" 
      style={{
        minHeight: '100vh', 
        backgroundColor: '#030712', 
        color: '#f9fafb', 
        fontFamily: 'monospace',
        margin: 0,
        padding: 0
      }}
    >
      {/* Header */}
      <header 
        className="bg-gray-900 border-b border-gray-800 px-6 py-4"
        style={{backgroundColor: '#111827', borderBottom: '1px solid #374151', padding: '16px 24px'}}
      >
        <div className="flex justify-between items-center" style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <span className="text-green-400 text-xl">📈</span>
              <h1 className="text-xl font-bold text-white">KALSHI TERMINAL</h1>
            </div>
            <div className="text-sm text-gray-400">
              Prediction Markets • Live Data Stream
            </div>
          </div>
          
          <div className="flex items-center space-x-6">
            <div className="flex items-center space-x-2">
              {connected ? (
                <>
                  <span className="text-green-400 text-sm">📶</span>
                  <span className="text-green-400 text-sm">LIVE</span>
                </>
              ) : (
                <>
                  <span className="text-red-400 text-sm">📶</span>
                  <span className="text-red-400 text-sm">DISCONNECTED</span>
                </>
              )}
            </div>
            <div className="text-sm text-gray-400">
              {lastUpdate.toLocaleTimeString()}
            </div>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar - Market List */}
        <div className="w-80 bg-gray-900 border-r border-gray-800 h-screen overflow-y-auto">
          <div className="p-4 border-b border-gray-800">
            <h2 className="font-semibold text-white mb-2">MARKETS</h2>
            <div className="text-xs text-gray-400">
              {Object.keys(books).length} active books
            </div>
          </div>
          
          <div className="divide-y divide-gray-800">
            {Array.from(new Set(Object.keys(books).map(key => key.split('_')[0]))).map(marketId => {
              const yesBook = books[`${marketId}_yes`]
              const noBook = books[`${marketId}_no`]
              const isSelected = selectedMarket === marketId
              const isStale = yesBook && (Date.now() - yesBook.stored_at) > 5000
              
              return (
                <div
                  key={marketId}
                  onClick={() => setSelectedMarket(selectedMarket === marketId ? null : marketId)}
                  className={`p-4 cursor-pointer hover:bg-gray-800 transition-colors ${
                    isSelected ? 'bg-gray-800 border-l-2 border-blue-500' : ''
                  }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-white truncate">
                        {getMarketTitle(marketId)}
                      </div>
                      <div className="text-xs text-gray-400 truncate mt-1">
                        {markets[marketId]?.ticker || marketId}
                      </div>
                    </div>
                    {isStale && <span className="text-yellow-500 ml-2">⚠️</span>}
                  </div>
                  
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="bg-green-500/10 p-2 rounded">
                      <div className="text-green-400 font-medium">YES</div>
                      <div className="text-white">{formatPrice(yesBook?.best_bid)}</div>
                    </div>
                    <div className="bg-red-500/10 p-2 rounded">
                      <div className="text-red-400 font-medium">NO</div>
                      <div className="text-white">{formatPrice(noBook?.best_bid)}</div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 overflow-y-auto">
          <div className="p-6 space-y-6">
            {/* System Status Bar */}
            <div className="bg-gray-900 rounded-lg border border-gray-800">
              <div className="px-4 py-3 border-b border-gray-800">
                <h2 className="font-semibold text-white">SYSTEM STATUS</h2>
              </div>
              <div className="p-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="flex items-center space-x-2">
                    <div className={`w-2 h-2 rounded-full ${getStatusBg(status?.api_status)}`}></div>
                    <span className="text-sm">API: {status?.api_status || 'Unknown'}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className={`w-2 h-2 rounded-full ${status?.redis_connected ? 'bg-green-500' : 'bg-red-500'}`}></div>
                    <span className="text-sm">Redis: {status?.redis_connected ? 'Connected' : 'Down'}</span>
                  </div>
                  {status?.venues?.kalshi && (
                    <>
                      <div className="flex items-center space-x-2">
                        <div className={`w-2 h-2 rounded-full ${getStatusBg(status.venues.kalshi.status)}`}></div>
                        <span className="text-sm">Kalshi: {status.venues.kalshi.status}</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="text-gray-400 text-xs">🕒</span>
                        <span className="text-sm">
                          {status.venues.kalshi.latency_p95_ms ? `${Math.round(status.venues.kalshi.latency_p95_ms)}ms` : 'N/A'}
                        </span>
                      </div>
                    </>
                  )}
                </div>
                
                {status?.venues?.kalshi?.reason && (
                  <div className="mt-2 text-xs text-yellow-400">
                    {status.venues.kalshi.reason}
                  </div>
                )}
              </div>
            </div>

            {/* Order Books */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-gray-900 rounded-lg border border-gray-800">
                <div className="px-4 py-3 border-b border-gray-800 flex justify-between items-center">
                  <h2 className="font-semibold text-white">ORDER BOOKS</h2>
                  <div className="text-xs text-gray-400">
                    {selectedMarket ? getMarketTitle(selectedMarket) : 'All Markets'}
                  </div>
                </div>
                
                <div className="p-4 space-y-4 max-h-96 overflow-y-auto">
                  {selectedBooks.length === 0 ? (
                    <div className="text-center text-gray-400 py-8">
                      <div className="text-4xl mb-2 opacity-50">📊</div>
                      <div>Waiting for market data...</div>
                      <div className="text-xs mt-1">Check adapter connection</div>
                    </div>
                  ) : (
                    selectedBooks.map(([key, book]) => {
                      const [marketId, outcomeId] = key.split('_')
                      const isStale = (Date.now() - book.stored_at) > 5000
                      const isYes = outcomeId === 'yes'
                      
                      return (
                        <div
                          key={key}
                          className={`bg-gray-800 rounded-lg p-4 border ${
                            isStale ? 'border-red-500/50' : 'border-gray-700'
                          }`}
                        >
                          <div className="flex justify-between items-start mb-3">
                            <div>
                              <div className="font-medium text-white text-sm">
                                {markets[marketId]?.ticker || marketId}
                              </div>
                              <div className="text-xs text-gray-400 mt-1">
                                {getMarketTitle(marketId).slice(0, 40)}...
                              </div>
                            </div>
                            <span className={`px-2 py-1 text-xs font-bold rounded ${
                              isYes 
                                ? 'bg-green-500/20 text-green-400 border border-green-500/30' 
                                : 'bg-red-500/20 text-red-400 border border-red-500/30'
                            }`}>
                              {outcomeId.toUpperCase()}
                            </span>
                          </div>
                          
                          <div className="grid grid-cols-3 gap-4 mb-3">
                            <div>
                              <div className="text-xs text-gray-400 mb-1">BID</div>
                              <div className="text-green-400 font-medium">
                                {formatPrice(book.best_bid)}
                              </div>
                            </div>
                            <div>
                              <div className="text-xs text-gray-400 mb-1">MID</div>
                              <div className="text-white font-medium">
                                {book.mid_px ? `${book.mid_px.toFixed(1)}¢` : '--'}
                              </div>
                            </div>
                            <div>
                              <div className="text-xs text-gray-400 mb-1">ASK</div>
                              <div className="text-red-400 font-medium">
                                {formatPrice(book.best_ask)}
                              </div>
                            </div>
                          </div>
                          
                          <div className="text-xs text-gray-400">
                            Spread: {formatSpread(book.best_bid, book.best_ask)}
                          </div>
                          
                          {isStale && (
                            <div className="text-red-400 text-xs mt-2 flex items-center space-x-1">
                              <span>⚠️</span>
                              <span>Stale data ({Math.round((Date.now() - book.stored_at) / 1000)}s ago)</span>
                            </div>
                          )}
                        </div>
                      )
                    })
                  )}
                </div>
              </div>

              {/* Event Stream */}
              <div className="bg-gray-900 rounded-lg border border-gray-800">
                <div className="px-4 py-3 border-b border-gray-800">
                  <h2 className="font-semibold text-white">EVENT STREAM</h2>
                </div>
                
                <div className="p-4 space-y-2 max-h-96 overflow-y-auto font-mono text-xs">
                  {events.length === 0 ? (
                    <div className="text-center text-gray-400 py-8">
                      <div>No events received</div>
                      <div className="text-xs mt-1">Waiting for adapter...</div>
                    </div>
                  ) : (
                    events.map((event, index) => {
                      const getEventColor = (type: string) => {
                        switch (type) {
                          case 'health': return 'text-blue-400'
                          case 'book_snapshot': return 'text-green-400'
                          case 'book_delta': return 'text-yellow-400'
                          case 'market_info': return 'text-purple-400'
                          case 'error': return 'text-red-400'
                          default: return 'text-gray-300'
                        }
                      }
                      
                      return (
                        <div key={index} className="bg-gray-800 rounded p-2 hover:bg-gray-750 transition-colors">
                          <div className="flex justify-between items-center mb-1">
                            <span className={`font-medium ${getEventColor(event.type)}`}>
                              [{event.type.toUpperCase()}]
                            </span>
                            <span className="text-gray-500">
                              {new Date(event.ts_received_ns / 1000000).toLocaleTimeString()}
                            </span>
                          </div>
                          <div className="text-gray-300">
                            <span className="text-gray-400">{event.venue_id}:</span> {
                              JSON.stringify(event.data, null, 0).substring(0, 80)
                            }...
                          </div>
                        </div>
                      )
                    })
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App