import React, { useState, useEffect, useRef } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, BarChart, Bar } from 'recharts'

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

interface TickerData {
  market_ticker: string
  last_price?: number
  volume?: number
  open_interest?: number
  high_24h?: number
  low_24h?: number
  change_24h?: number
}

interface TradeData {
  market_ticker: string
  price: number
  quantity: number
  side: 'yes' | 'no'
  timestamp: number
}

interface MarketInfo {
  ticker: string
  title: string
  subtitle?: string
  open_time: string
  close_time: string
  status: string
  volume_24h?: number
  liquidity?: number
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
  searchContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px'
  },
  searchInput: {
    backgroundColor: '#334155',
    border: '1px solid #475569',
    borderRadius: '6px',
    padding: '8px 12px',
    color: '#f1f5f9',
    fontSize: '14px',
    width: '300px'
  },
  searchButton: {
    backgroundColor: '#0ea5e9',
    color: '#f1f5f9',
    border: 'none',
    borderRadius: '6px',
    padding: '8px 16px',
    cursor: 'pointer',
    fontSize: '14px'
  },
  title: {
    fontSize: '20px',
    fontWeight: 'bold',
    color: '#f1f5f9',
    margin: 0
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
    gap: '24px',
    marginBottom: '24px'
  },
  chartContainer: {
    height: '300px',
    width: '100%'
  },
  marketDetails: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
    gap: '12px',
    marginBottom: '16px'
  },
  statCard: {
    backgroundColor: '#334155',
    padding: '12px',
    borderRadius: '6px',
    textAlign: 'center' as const
  },
  statLabel: {
    fontSize: '11px',
    color: '#94a3b8',
    marginBottom: '4px'
  },
  statValue: {
    fontSize: '16px',
    fontWeight: 'bold'
  },
  tradesFeed: {
    maxHeight: '400px',
    overflowY: 'auto' as const
  },
  tradeItem: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '8px',
    borderBottom: '1px solid #334155',
    fontSize: '12px'
  },
  orderbook: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '16px'
  },
  orderbookSide: {
    backgroundColor: '#334155',
    borderRadius: '6px',
    padding: '12px'
  },
  orderbookHeader: {
    fontWeight: 'bold',
    marginBottom: '8px',
    textAlign: 'center' as const
  },
  orderbookLevel: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '4px 8px',
    fontSize: '12px',
    borderRadius: '3px',
    marginBottom: '2px'
  }
}

function EnhancedTerminal() {
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [books, setBooks] = useState<Record<string, BookData>>({})
  const [tickers, setTickers] = useState<Record<string, TickerData>>({})
  const [trades, setTrades] = useState<TradeData[]>([])
  const [connected, setConnected] = useState(false)
  const [events, setEvents] = useState<Array<any>>([])
  const [selectedMarket, setSelectedMarket] = useState<string | null>(null)
  const [searchTicker, setSearchTicker] = useState('')
  const [marketInfo, setMarketInfo] = useState<MarketInfo | null>(null)
  const [priceHistory, setPriceHistory] = useState<Array<{time: string, price: number}>>([])
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    // Connect to WebSocket
    const connectWebSocket = () => {
      const ws = new WebSocket('ws://localhost:8000/ws')
      wsRef.current = ws

      ws.onopen = () => {
        console.log('Connected to WebSocket')
        setConnected(true)
        
        // Subscribe to all channels
        ws.send(JSON.stringify({
          type: 'subscribe',
          channels: ['books', 'health', 'events', 'tickers', 'trades']
        }))
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          
          if (message.type === 'status') {
            setStatus(message.data)
          } else if (message.type === 'event') {
            const eventData = message.data
            setEvents(prev => [eventData, ...prev.slice(0, 49)])
            
            // Process different event types
            if (eventData.type === 'book_snapshot') {
              const newBooks: Record<string, BookData> = {}
              for (const book of eventData.data) {
                const key = `${book.market_id}_${book.outcome_id}`
                newBooks[key] = {
                  ...book,
                  stored_at: Date.now()
                }
              }
              setBooks(prev => ({ ...prev, ...newBooks }))
            } else if (eventData.type === 'ticker_update') {
              setTickers(prev => ({
                ...prev,
                [eventData.data.market_ticker]: eventData.data
              }))
              
              // Update price history for selected market
              if (eventData.data.market_ticker === selectedMarket) {
                setPriceHistory(prev => [
                  ...prev.slice(-99), // Keep last 100 points
                  {
                    time: new Date().toLocaleTimeString(),
                    price: eventData.data.last_price || 0
                  }
                ])
              }
            } else if (eventData.type === 'trade') {
              setTrades(prev => [
                eventData.data,
                ...prev.slice(0, 99) // Keep last 100 trades
              ])
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
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [selectedMarket])

  // Fetch initial data
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const statusResponse = await fetch('http://localhost:8000/status')
        if (statusResponse.ok) {
          setStatus(await statusResponse.json())
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

  const searchMarket = async () => {
    if (!searchTicker.trim()) return
    
    try {
      const response = await fetch(`http://localhost:8000/market/${searchTicker}`)
      if (response.ok) {
        const marketData = await response.json()
        setMarketInfo(marketData)
        setSelectedMarket(searchTicker)
        setPriceHistory([]) // Reset price history for new market
      }
    } catch (error) {
      console.error('Error searching market:', error)
    }
  }

  const formatPrice = (cents?: number) => {
    return cents ? `${cents}¢` : '--'
  }

  const getMarketId = (key: string) => {
    return key.split('_')[0].replace('book:kalshi:', '')
  }

  const getOutcome = (key: string) => {
    return key.split('_')[1] || key.split(':').pop()
  }

  // Get unique markets from books
  const uniqueMarkets = Array.from(new Set(Object.keys(books).map(key => {
    const parts = key.split(':')
    return parts.length > 2 ? parts[2] : key.split('_')[0]
  }))).slice(0, 20) // Limit to 20 for performance

  // Get selected market data
  const selectedBooks = Object.entries(books).filter(([key]) => 
    !selectedMarket || key.includes(selectedMarket)
  )

  const selectedTicker = selectedMarket ? tickers[selectedMarket] : null
  const selectedTrades = trades.filter(trade => 
    !selectedMarket || trade.market_ticker === selectedMarket
  ).slice(0, 20)

  return (
    <div style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerContent}>
          <div>
            <h1 style={styles.title}>📈 KALSHI PRO TERMINAL</h1>
            <div style={{fontSize: '12px', color: '#94a3b8', marginTop: '4px'}}>
              Advanced Prediction Markets Analysis
            </div>
          </div>
          
          <div style={styles.searchContainer}>
            <input
              type="text"
              placeholder="Enter market ticker (e.g., KXNOBELPEACE-25-EMM)"
              value={searchTicker}
              onChange={(e) => setSearchTicker(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && searchMarket()}
              style={styles.searchInput}
            />
            <button onClick={searchMarket} style={styles.searchButton}>
              Search
            </button>
            <div style={{fontSize: '14px'}}>
              <span style={{color: connected ? '#10b981' : '#ef4444'}}>
                📶 {connected ? 'LIVE' : 'DISCONNECTED'}
              </span>
            </div>
          </div>
        </div>
      </header>

      <div style={styles.main}>
        {/* Sidebar */}
        <div style={styles.sidebar}>
          <div style={{padding: '16px', borderBottom: '1px solid #334155'}}>
            <h2 style={{margin: 0, fontSize: '14px', fontWeight: 'bold'}}>ACTIVE MARKETS</h2>
            <div style={{fontSize: '12px', color: '#94a3b8', marginTop: '4px'}}>
              {uniqueMarkets.length} markets • Click to analyze
            </div>
          </div>
          
          {uniqueMarkets.map(marketId => {
            const yesKey = Object.keys(books).find(k => k.includes(marketId) && k.includes('yes'))
            const noKey = Object.keys(books).find(k => k.includes(marketId) && k.includes('no'))
            const yesBook = yesKey ? books[yesKey] : null
            const noBook = noKey ? books[noKey] : null
            const ticker = tickers[marketId]
            
            return (
              <div
                key={marketId}
                style={{
                  padding: '16px',
                  borderBottom: '1px solid #334155',
                  cursor: 'pointer',
                  backgroundColor: selectedMarket === marketId ? '#334155' : 'transparent'
                }}
                onClick={() => setSelectedMarket(selectedMarket === marketId ? null : marketId)}
              >
                <div style={{fontSize: '13px', fontWeight: 'bold', marginBottom: '8px'}}>
                  {marketId}
                </div>
                
                {ticker && (
                  <div style={{fontSize: '11px', color: '#94a3b8', marginBottom: '8px'}}>
                    Vol: {ticker.volume || 0} • OI: {ticker.open_interest || 0}
                  </div>
                )}
                
                <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px'}}>
                  <div style={{backgroundColor: '#065f46', padding: '8px', borderRadius: '4px'}}>
                    <div style={{color: '#10b981', fontSize: '12px', fontWeight: 'bold'}}>YES</div>
                    <div style={{color: '#f1f5f9'}}>{formatPrice(yesBook?.best_bid)}</div>
                  </div>
                  <div style={{backgroundColor: '#7f1d1d', padding: '8px', borderRadius: '4px'}}>
                    <div style={{color: '#ef4444', fontSize: '12px', fontWeight: 'bold'}}>NO</div>
                    <div style={{color: '#f1f5f9'}}>{formatPrice(noBook?.best_bid)}</div>
                  </div>
                </div>
                
                {ticker?.change_24h && (
                  <div style={{
                    marginTop: '8px',
                    fontSize: '11px',
                    color: ticker.change_24h > 0 ? '#10b981' : '#ef4444'
                  }}>
                    24h: {ticker.change_24h > 0 ? '+' : ''}{ticker.change_24h.toFixed(1)}%
                  </div>
                )}
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
              <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '16px'}}>
                <div>API: <span style={{color: '#10b981'}}>{status?.api_status || 'Unknown'}</span></div>
                <div>Redis: <span style={{color: status?.redis_connected ? '#10b981' : '#ef4444'}}>
                  {status?.redis_connected ? 'Connected' : 'Down'}</span></div>
                {status?.venues?.kalshi && (
                  <>
                    <div>Kalshi: <span style={{
                      color: status.venues.kalshi.status === 'healthy' ? '#10b981' : 
                             status.venues.kalshi.status === 'degraded' ? '#f59e0b' : '#ef4444'
                    }}>{status.venues.kalshi.status}</span></div>
                    <div>🕒 {status.venues.kalshi.latency_p95_ms ? 
                      `${Math.round(status.venues.kalshi.latency_p95_ms)}ms` : 'N/A'}</div>
                    <div>Markets: {status.venues.kalshi.subscribed_markets || 0}</div>
                    <div>Stale: {status.venues.kalshi.stale_markets || 0}</div>
                  </>
                )}
              </div>
              {status?.venues?.kalshi?.reason && (
                <div style={{marginTop: '12px', fontSize: '12px', color: '#f59e0b'}}>
                  ⚠️ {status.venues.kalshi.reason}
                </div>
              )}
            </div>
          </div>

          {selectedMarket ? (
            <>
              {/* Market Details */}
              {marketInfo && (
                <div style={styles.card}>
                  <div style={styles.cardHeader}>{selectedMarket} - MARKET DETAILS</div>
                  <div style={styles.cardContent}>
                    <h3 style={{margin: '0 0 8px 0', fontSize: '16px'}}>{marketInfo.title}</h3>
                    {marketInfo.subtitle && (
                      <p style={{margin: '0 0 16px 0', color: '#94a3b8', fontSize: '14px'}}>
                        {marketInfo.subtitle}
                      </p>
                    )}
                    <div style={styles.marketDetails}>
                      <div style={styles.statCard}>
                        <div style={styles.statLabel}>STATUS</div>
                        <div style={{...styles.statValue, color: marketInfo.status === 'open' ? '#10b981' : '#f59e0b'}}>
                          {marketInfo.status.toUpperCase()}
                        </div>
                      </div>
                      <div style={styles.statCard}>
                        <div style={styles.statLabel}>CLOSES</div>
                        <div style={styles.statValue}>
                          {new Date(marketInfo.close_time).toLocaleDateString()}
                        </div>
                      </div>
                      {selectedTicker && (
                        <>
                          <div style={styles.statCard}>
                            <div style={styles.statLabel}>LAST PRICE</div>
                            <div style={styles.statValue}>{formatPrice(selectedTicker.last_price)}</div>
                          </div>
                          <div style={styles.statCard}>
                            <div style={styles.statLabel}>VOLUME 24H</div>
                            <div style={styles.statValue}>{selectedTicker.volume || 0}</div>
                          </div>
                          <div style={styles.statCard}>
                            <div style={styles.statLabel}>OPEN INTEREST</div>
                            <div style={styles.statValue}>{selectedTicker.open_interest || 0}</div>
                          </div>
                          <div style={styles.statCard}>
                            <div style={styles.statLabel}>24H CHANGE</div>
                            <div style={{
                              ...styles.statValue,
                              color: (selectedTicker.change_24h || 0) >= 0 ? '#10b981' : '#ef4444'
                            }}>
                              {selectedTicker.change_24h ? 
                                `${selectedTicker.change_24h > 0 ? '+' : ''}${selectedTicker.change_24h.toFixed(1)}%` : 
                                'N/A'
                              }
                            </div>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Price Chart */}
              {priceHistory.length > 0 && (
                <div style={styles.card}>
                  <div style={styles.cardHeader}>PRICE CHART - {selectedMarket}</div>
                  <div style={styles.cardContent}>
                    <div style={styles.chartContainer}>
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={priceHistory}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                          <XAxis dataKey="time" stroke="#94a3b8" />
                          <YAxis stroke="#94a3b8" />
                          <Tooltip 
                            contentStyle={{backgroundColor: '#1e293b', border: '1px solid #334155'}}
                            labelStyle={{color: '#f1f5f9'}}
                          />
                          <Area type="monotone" dataKey="price" stroke="#0ea5e9" fill="#0ea5e9" fillOpacity={0.3} />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
              )}

              {/* Order Book Visualization */}
              <div style={styles.grid}>
                <div style={styles.card}>
                  <div style={styles.cardHeader}>ORDER BOOK - {selectedMarket}</div>
                  <div style={styles.cardContent}>
                    {selectedBooks.length > 0 ? (
                      <div style={styles.orderbook}>
                        {selectedBooks.map(([key, book]) => {
                          const outcome = getOutcome(key)
                          const isYes = outcome === 'yes'
                          
                          return (
                            <div key={key} style={styles.orderbookSide}>
                              <div style={{
                                ...styles.orderbookHeader,
                                color: isYes ? '#10b981' : '#ef4444'
                              }}>
                                {outcome?.toUpperCase()} ORDERS
                              </div>
                              
                              <div style={{marginBottom: '12px'}}>
                                <div style={{fontSize: '11px', color: '#94a3b8'}}>Best {isYes ? 'Bid' : 'Ask'}</div>
                                <div style={{fontSize: '18px', fontWeight: 'bold', color: isYes ? '#10b981' : '#ef4444'}}>
                                  {formatPrice(isYes ? book.best_bid : book.best_ask)}
                                </div>
                              </div>
                              
                              {(isYes ? book.bids : book.asks).slice(0, 5).map((level, idx) => (
                                <div key={idx} style={{
                                  ...styles.orderbookLevel,
                                  backgroundColor: isYes ? '#065f4620' : '#7f1d1d20'
                                }}>
                                  <span>{formatPrice(level.px_cents)}</span>
                                  <span>{level.qty}</span>
                                </div>
                              ))}
                            </div>
                          )
                        })}
                      </div>
                    ) : (
                      <div style={{textAlign: 'center', color: '#94a3b8', padding: '40px'}}>
                        No orderbook data available
                      </div>
                    )}
                  </div>
                </div>

                {/* Recent Trades */}
                <div style={styles.card}>
                  <div style={styles.cardHeader}>RECENT TRADES - {selectedMarket}</div>
                  <div style={styles.cardContent}>
                    <div style={styles.tradesFeed}>
                      {selectedTrades.length > 0 ? selectedTrades.map((trade, idx) => (
                        <div key={idx} style={styles.tradeItem}>
                          <span style={{color: trade.side === 'yes' ? '#10b981' : '#ef4444'}}>
                            {trade.side.toUpperCase()}
                          </span>
                          <span>{formatPrice(trade.price)}</span>
                          <span>{trade.quantity}</span>
                          <span style={{color: '#94a3b8'}}>
                            {new Date(trade.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                      )) : (
                        <div style={{textAlign: 'center', color: '#94a3b8', padding: '40px'}}>
                          No recent trades
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div style={styles.card}>
              <div style={styles.cardContent}>
                <div style={{textAlign: 'center', color: '#94a3b8', padding: '60px'}}>
                  <div style={{fontSize: '48px', marginBottom: '16px'}}>📊</div>
                  <div style={{fontSize: '18px', marginBottom: '8px'}}>Select a market to view advanced analytics</div>
                  <div style={{fontSize: '14px'}}>
                    Click on any market from the sidebar or search for a specific ticker above
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Event Stream */}
          <div style={styles.card}>
            <div style={styles.cardHeader}>LIVE EVENT STREAM</div>
            <div style={styles.cardContent}>
              <div style={{maxHeight: '300px', overflowY: 'auto'}}>
                {events.length === 0 ? (
                  <div style={{textAlign: 'center', color: '#94a3b8', padding: '40px'}}>
                    No events received yet...
                  </div>
                ) : (
                  events.map((event, index) => {
                    const getEventColor = (type: string) => {
                      switch (type) {
                        case 'health': return '#3b82f6'
                        case 'book_snapshot': return '#10b981'
                        case 'book_delta': return '#f59e0b'
                        case 'ticker_update': return '#8b5cf6'
                        case 'trade': return '#06b6d4'
                        case 'error': return '#ef4444'
                        default: return '#94a3b8'
                      }
                    }
                    
                    return (
                      <div key={index} style={{
                        backgroundColor: '#1e293b',
                        padding: '8px',
                        borderRadius: '4px',
                        marginBottom: '4px',
                        fontSize: '11px'
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
  )
}

export default EnhancedTerminal