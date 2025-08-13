import React, { useState, useEffect, useRef } from 'react'

interface VenueHealth {
  status: string
  latency_p50_ms?: number
  latency_p95_ms?: number
  subscribed_markets?: number
  stale_markets?: number
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
}

function App() {
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [books, setBooks] = useState<Record<string, BookData>>({})
  const [connected, setConnected] = useState(false)
  const [events, setEvents] = useState<Array<any>>([])
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
          
          if (message.type === 'status') {
            setStatus(message.data)
          } else if (message.type === 'event') {
            const eventData = message.data
            setEvents(prev => [eventData, ...prev.slice(0, 19)]) // Keep last 20 events
            
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
                  stored_at: Date.now()
                }
              }
              setBooks(prev => ({ ...prev, ...newBooks }))
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

  const getStatusText = (status?: string) => {
    return status || 'Unknown'
  }

  const formatLatency = (latency?: number) => {
    return latency ? `${Math.round(latency)}ms` : 'N/A'
  }

  const formatPrice = (cents?: number) => {
    return cents ? `${cents}¢` : 'N/A'
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <header className="bg-gray-800 border-b border-gray-700 p-4">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold">Kalshi Terminal</h1>
            <p className="text-gray-400 text-sm">Prediction Markets Arbitrage</p>
          </div>
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-400' : 'bg-red-400'}`}></div>
            <span className="text-sm">{connected ? 'Connected' : 'Disconnected'}</span>
          </div>
        </div>
      </header>
      
      <main className="p-6">
        <div className="max-w-6xl mx-auto">
          {/* System Status */}
          <div className="bg-gray-800 rounded-lg p-4 mb-6">
            <h2 className="text-lg font-semibold mb-4">System Status</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                API: <span className={getStatusColor(status?.api_status)}>{getStatusText(status?.api_status)}</span>
              </div>
              <div>
                Redis: <span className={status?.redis_connected ? 'text-green-400' : 'text-red-400'}>
                  {status?.redis_connected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              {status?.venues?.kalshi && (
                <>
                  <div>
                    Kalshi: <span className={getStatusColor(status.venues.kalshi.status)}>
                      {getStatusText(status.venues.kalshi.status)}
                    </span>
                  </div>
                  <div>
                    Latency: <span className="text-gray-300">
                      {formatLatency(status.venues.kalshi.latency_p95_ms)}
                    </span>
                  </div>
                </>
              )}
            </div>
            {status?.venues?.kalshi && (
              <div className="mt-2 text-xs text-gray-400">
                Markets: {status.venues.kalshi.subscribed_markets || 0} subscribed, 
                {status.venues.kalshi.stale_markets || 0} stale
              </div>
            )}
          </div>

          {/* Market Data */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Live Books */}
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-lg font-semibold mb-4">Live Order Books</h2>
              {Object.keys(books).length === 0 ? (
                <div className="text-gray-400 text-center py-8">
                  No market data available. Waiting for adapter connection...
                </div>
              ) : (
                <div className="space-y-4">
                  {Object.entries(books).slice(0, 5).map(([key, book]) => {
                    const [marketId, outcomeId] = key.split('_')
                    const isStale = (Date.now() - book.stored_at) > 5000 // 5 seconds
                    
                    return (
                      <div key={key} className={`border rounded p-3 ${isStale ? 'border-red-500/50' : 'border-gray-600'}`}>
                        <div className="flex justify-between items-center mb-2">
                          <h3 className="font-medium">{marketId}</h3>
                          <span className={`text-xs px-2 py-1 rounded ${
                            outcomeId === 'yes' ? 'bg-green-900/50 text-green-300' : 'bg-red-900/50 text-red-300'
                          }`}>
                            {outcomeId.toUpperCase()}
                          </span>
                        </div>
                        
                        <div className="grid grid-cols-3 gap-4 text-sm">
                          <div>
                            <div className="text-gray-400">Best Bid</div>
                            <div className="text-green-300">{formatPrice(book.best_bid)}</div>
                          </div>
                          <div>
                            <div className="text-gray-400">Mid</div>
                            <div className="text-white">{book.mid_px ? `${book.mid_px.toFixed(1)}¢` : 'N/A'}</div>
                          </div>
                          <div>
                            <div className="text-gray-400">Best Ask</div>
                            <div className="text-red-300">{formatPrice(book.best_ask)}</div>
                          </div>
                        </div>
                        
                        {isStale && (
                          <div className="text-red-400 text-xs mt-2">⚠ Stale data</div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Event Stream */}
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-lg font-semibold mb-4">Event Stream</h2>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {events.length === 0 ? (
                  <div className="text-gray-400 text-center py-8">
                    No events received yet...
                  </div>
                ) : (
                  events.map((event, index) => (
                    <div key={index} className="text-xs bg-gray-700 rounded p-2">
                      <div className="flex justify-between items-center">
                        <span className={`font-medium ${
                          event.type === 'health' ? 'text-blue-300' :
                          event.type === 'book_snapshot' ? 'text-green-300' :
                          event.type === 'market_info' ? 'text-yellow-300' :
                          'text-gray-300'
                        }`}>
                          {event.type}
                        </span>
                        <span className="text-gray-400">
                          {new Date(event.ts_received_ns / 1000000).toLocaleTimeString()}
                        </span>
                      </div>
                      <div className="text-gray-300 mt-1">
                        {event.venue_id} - {JSON.stringify(event.data).substring(0, 100)}...
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default App