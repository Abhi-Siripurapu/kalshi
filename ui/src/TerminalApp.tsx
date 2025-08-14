import React, { useState, useEffect, useRef } from 'react'

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

const styles = {
  container: {
    minHeight: '100vh',
    backgroundColor: '#0f172a',
    color: '#f1f5f9',
    fontFamily: 'ui-monospace, "Cascadia Code", "Source Code Pro", Menlo, Consolas, "DejaVu Sans Mono", monospace',
    margin: 0,
    padding: 0
  },
  header: {
    backgroundColor: '#1e293b',
    borderBottom: '1px solid #334155',
    padding: '16px 24px'
  },
  headerContent: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  title: {
    fontSize: '20px',
    fontWeight: 'bold',
    color: '#f1f5f9',
    margin: 0
  },
  status: {
    fontSize: '14px'
  },
  connected: {
    color: '#10b981'
  },
  disconnected: {
    color: '#ef4444'
  },
  main: {
    display: 'flex',
    height: 'calc(100vh - 80px)'
  },
  sidebar: {
    width: '320px',
    backgroundColor: '#1e293b',
    borderRight: '1px solid #334155',
    overflowY: 'auto' as const
  },
  sidebarHeader: {
    padding: '16px',
    borderBottom: '1px solid #334155'
  },
  marketItem: {
    padding: '16px',
    borderBottom: '1px solid #334155',
    cursor: 'pointer'
  },
  marketItemHover: {
    backgroundColor: '#334155'
  },
  content: {
    flex: 1,
    padding: '24px',
    overflowY: 'auto' as const
  },
  card: {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '8px',
    marginBottom: '24px'
  },
  cardHeader: {
    padding: '12px 16px',
    borderBottom: '1px solid #334155',
    fontWeight: 'bold',
    fontSize: '14px'
  },
  cardContent: {
    padding: '16px'
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '24px'
  },
  statusGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '16px'
  },
  bookItem: {
    backgroundColor: '#334155',
    borderRadius: '8px',
    padding: '16px',
    marginBottom: '16px'
  },
  priceGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr 1fr',
    gap: '16px',
    marginBottom: '12px'
  },
  bid: {
    color: '#10b981'
  },
  ask: {
    color: '#ef4444'
  },
  mid: {
    color: '#f1f5f9'
  }
}

function TerminalApp() {
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [books, setBooks] = useState<Record<string, BookData>>({})
  const [connected, setConnected] = useState(false)
  const [events, setEvents] = useState<Array<any>>([])
  const [selectedMarket, setSelectedMarket] = useState<string | null>(null)
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
            setEvents(prev => [eventData, ...prev.slice(0, 19)])
            
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
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      ws.onclose = () => {
        console.log('WebSocket disconnected')
        setConnected(false)
        setTimeout(connectWebSocket, 2000)
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
        const statusResponse = await fetch('http://localhost:8000/status')
        if (statusResponse.ok) {
          const statusData = await statusResponse.json()
          setStatus(statusData)
        }

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

  const formatPrice = (cents?: number) => {
    return cents ? `${cents}¢` : '--'
  }

  const getMarketId = (key: string) => {
    return key.split('_')[0].replace('book:kalshi:', '')
  }

  const getOutcome = (key: string) => {
    return key.split('_')[1] || key.split(':').pop()
  }

  // Get unique markets
  const uniqueMarkets = Array.from(new Set(Object.keys(books).map(key => {
    const parts = key.split(':')
    return parts.length > 2 ? parts[2] : key.split('_')[0]
  })))

  return (
    <div style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerContent}>
          <div>
            <h1 style={styles.title}>📈 KALSHI TERMINAL</h1>
            <div style={{fontSize: '12px', color: '#94a3b8', marginTop: '4px'}}>
              Prediction Markets • Live Data Stream
            </div>
          </div>
          
          <div style={styles.status}>
            <span style={connected ? styles.connected : styles.disconnected}>
              📶 {connected ? 'LIVE' : 'DISCONNECTED'}
            </span>
          </div>
        </div>
      </header>

      <div style={styles.main}>
        {/* Sidebar */}
        <div style={styles.sidebar}>
          <div style={styles.sidebarHeader}>
            <h2 style={{margin: 0, fontSize: '14px', fontWeight: 'bold'}}>MARKETS</h2>
            <div style={{fontSize: '12px', color: '#94a3b8', marginTop: '4px'}}>
              {Object.keys(books).length} active books
            </div>
          </div>
          
          {uniqueMarkets.map(marketId => {
            const yesKey = Object.keys(books).find(k => k.includes(marketId) && k.includes('yes'))
            const noKey = Object.keys(books).find(k => k.includes(marketId) && k.includes('no'))
            const yesBook = yesKey ? books[yesKey] : null
            const noBook = noKey ? books[noKey] : null
            
            return (
              <div
                key={marketId}
                style={{
                  ...styles.marketItem,
                  ...(selectedMarket === marketId ? styles.marketItemHover : {})
                }}
                onClick={() => setSelectedMarket(selectedMarket === marketId ? null : marketId)}
              >
                <div style={{fontSize: '13px', fontWeight: 'bold', marginBottom: '8px'}}>
                  {marketId}
                </div>
                
                <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px'}}>
                  <div style={{backgroundColor: '#065f46', padding: '8px', borderRadius: '4px'}}>
                    <div style={{...styles.bid, fontSize: '12px', fontWeight: 'bold'}}>YES</div>
                    <div style={{color: '#f1f5f9'}}>{formatPrice(yesBook?.best_bid)}</div>
                  </div>
                  <div style={{backgroundColor: '#7f1d1d', padding: '8px', borderRadius: '4px'}}>
                    <div style={{...styles.ask, fontSize: '12px', fontWeight: 'bold'}}>NO</div>
                    <div style={{color: '#f1f5f9'}}>{formatPrice(noBook?.best_bid)}</div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Main Content */}
        <div style={styles.content}>
          {/* System Status */}
          <div style={styles.card}>
            <div style={styles.cardHeader}>SYSTEM STATUS</div>
            <div style={styles.cardContent}>
              <div style={styles.statusGrid}>
                <div>
                  API: <span style={{color: '#10b981'}}>
                    {status?.api_status || 'Unknown'}
                  </span>
                </div>
                <div>
                  Redis: <span style={{color: status?.redis_connected ? '#10b981' : '#ef4444'}}>
                    {status?.redis_connected ? 'Connected' : 'Down'}
                  </span>
                </div>
                {status?.venues?.kalshi && (
                  <>
                    <div>
                      Kalshi: <span style={{
                        color: status.venues.kalshi.status === 'healthy' ? '#10b981' : 
                               status.venues.kalshi.status === 'degraded' ? '#f59e0b' : '#ef4444'
                      }}>
                        {status.venues.kalshi.status}
                      </span>
                    </div>
                    <div>
                      🕒 Latency: {status.venues.kalshi.latency_p95_ms ? 
                        `${Math.round(status.venues.kalshi.latency_p95_ms)}ms` : 'N/A'}
                    </div>
                  </>
                )}
              </div>
              
              {status?.venues?.kalshi?.reason && (
                <div style={{marginTop: '12px', fontSize: '12px', color: '#f59e0b'}}>
                  {status.venues.kalshi.reason}
                </div>
              )}
            </div>
          </div>

          {/* Order Books */}
          <div style={styles.grid}>
            <div style={styles.card}>
              <div style={styles.cardHeader}>
                ORDER BOOKS {selectedMarket && `- ${selectedMarket}`}
              </div>
              
              <div style={styles.cardContent}>
                {Object.keys(books).length === 0 ? (
                  <div style={{textAlign: 'center', color: '#94a3b8', padding: '40px'}}>
                    <div style={{fontSize: '32px', marginBottom: '8px'}}>📊</div>
                    <div>Waiting for market data...</div>
                    <div style={{fontSize: '12px', marginTop: '4px'}}>Check adapter connection</div>
                  </div>
                ) : (
                  <div style={{maxHeight: '400px', overflowY: 'auto'}}>
                    {Object.entries(books)
                      .filter(([key]) => !selectedMarket || key.includes(selectedMarket))
                      .slice(0, 10)
                      .map(([key, book]) => {
                        const marketId = getMarketId(key)
                        const outcome = getOutcome(key)
                        const isStale = (Date.now() - book.stored_at) > 5000
                        
                        return (
                          <div key={key} style={{
                            ...styles.bookItem,
                            ...(isStale ? {borderLeft: '3px solid #ef4444'} : {})
                          }}>
                            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px'}}>
                              <div>
                                <div style={{fontSize: '13px', fontWeight: 'bold'}}>
                                  {marketId}
                                </div>
                              </div>
                              <span style={{
                                padding: '2px 8px',
                                fontSize: '11px',
                                fontWeight: 'bold',
                                borderRadius: '4px',
                                backgroundColor: outcome === 'yes' ? '#065f46' : '#7f1d1d',
                                color: '#f1f5f9'
                              }}>
                                {outcome?.toUpperCase()}
                              </span>
                            </div>
                            
                            <div style={styles.priceGrid}>
                              <div>
                                <div style={{fontSize: '11px', color: '#94a3b8', marginBottom: '4px'}}>BID</div>
                                <div style={{...styles.bid, fontWeight: 'bold'}}>
                                  {formatPrice(book.best_bid)}
                                </div>
                              </div>
                              <div>
                                <div style={{fontSize: '11px', color: '#94a3b8', marginBottom: '4px'}}>MID</div>
                                <div style={{...styles.mid, fontWeight: 'bold'}}>
                                  {book.mid_px ? `${book.mid_px.toFixed(1)}¢` : '--'}
                                </div>
                              </div>
                              <div>
                                <div style={{fontSize: '11px', color: '#94a3b8', marginBottom: '4px'}}>ASK</div>
                                <div style={{...styles.ask, fontWeight: 'bold'}}>
                                  {formatPrice(book.best_ask)}
                                </div>
                              </div>
                            </div>
                            
                            {isStale && (
                              <div style={{fontSize: '11px', color: '#ef4444', marginTop: '8px'}}>
                                ⚠️ Stale data ({Math.round((Date.now() - book.stored_at) / 1000)}s ago)
                              </div>
                            )}
                          </div>
                        )
                      })}
                  </div>
                )}
              </div>
            </div>

            {/* Event Stream */}
            <div style={styles.card}>
              <div style={styles.cardHeader}>EVENT STREAM</div>
              
              <div style={styles.cardContent}>
                <div style={{maxHeight: '400px', overflowY: 'auto'}}>
                  {events.length === 0 ? (
                    <div style={{textAlign: 'center', color: '#94a3b8', padding: '40px'}}>
                      <div>No events received</div>
                      <div style={{fontSize: '12px', marginTop: '4px'}}>Waiting for adapter...</div>
                    </div>
                  ) : (
                    events.map((event, index) => {
                      const getEventColor = (type: string) => {
                        switch (type) {
                          case 'health': return '#3b82f6'
                          case 'book_snapshot': return '#10b981'
                          case 'book_delta': return '#f59e0b'
                          case 'market_info': return '#8b5cf6'
                          case 'error': return '#ef4444'
                          default: return '#94a3b8'
                        }
                      }
                      
                      return (
                        <div key={index} style={{
                          backgroundColor: '#1e293b', 
                          padding: '8px', 
                          borderRadius: '4px',
                          marginBottom: '8px',
                          fontSize: '12px'
                        }}>
                          <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '4px'}}>
                            <span style={{color: getEventColor(event.type), fontWeight: 'bold'}}>
                              [{event.type?.toUpperCase()}]
                            </span>
                            <span style={{color: '#94a3b8'}}>
                              {new Date(event.ts_received_ns / 1000000).toLocaleTimeString()}
                            </span>
                          </div>
                          <div style={{color: '#e2e8f0'}}>
                            <span style={{color: '#94a3b8'}}>{event.venue_id}:</span> {
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

export default TerminalApp