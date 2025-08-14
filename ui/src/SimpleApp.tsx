import React, { useState, useEffect } from 'react'

function SimpleApp() {
  const [status, setStatus] = useState<any>(null)
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    // Test API connection
    const fetchStatus = async () => {
      try {
        const response = await fetch('http://localhost:8000/status')
        if (response.ok) {
          const data = await response.json()
          setStatus(data)
        }
      } catch (error) {
        console.error('Failed to fetch status:', error)
      }
    }

    fetchStatus()

    // Test WebSocket connection
    const ws = new WebSocket('ws://localhost:8000/ws')
    
    ws.onopen = () => {
      console.log('WebSocket connected')
      setConnected(true)
    }

    ws.onmessage = (event) => {
      console.log('WebSocket message:', event.data)
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
      setConnected(false)
    }

    return () => {
      ws.close()
    }
  }, [])

  return (
    <div style={{ 
      padding: '20px', 
      fontFamily: 'monospace', 
      backgroundColor: '#1f2937', 
      color: '#f9fafb', 
      minHeight: '100vh' 
    }}>
      <h1 style={{ color: '#10b981', marginBottom: '20px' }}>
        🚀 KALSHI TERMINAL - SIMPLE TEST
      </h1>
      
      <div style={{ marginBottom: '20px' }}>
        <h2>Connection Status:</h2>
        <p>WebSocket: <span style={{ color: connected ? '#10b981' : '#ef4444' }}>
          {connected ? '✅ Connected' : '❌ Disconnected'}
        </span></p>
      </div>

      {status && (
        <div>
          <h2>API Status:</h2>
          <pre style={{ 
            backgroundColor: '#374151', 
            padding: '10px', 
            borderRadius: '4px',
            overflow: 'auto'
          }}>
            {JSON.stringify(status, null, 2)}
          </pre>
        </div>
      )}

      <div style={{ marginTop: '20px' }}>
        <h2>Next Steps:</h2>
        <p>1. ✅ Vite dev server running</p>
        <p>2. ✅ React app loading</p>
        <p>3. {status ? '✅' : '❌'} API connection</p>
        <p>4. {connected ? '✅' : '❌'} WebSocket connection</p>
        <p>5. Ready for full terminal UI!</p>
      </div>
    </div>
  )
}

export default SimpleApp