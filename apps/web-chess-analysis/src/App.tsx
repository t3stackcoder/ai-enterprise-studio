import { useState, useEffect, useRef } from 'react'

interface Analysis {
  pv: number
  depth: number
  score: number
  mate?: number
  line: string[]
}

interface AnalysisLine {
  depth?: number
  score?: number
  evaluation?: number | string  // Can be numeric score or "mate X"
  mate?: number
  pv?: string[]
  move?: string
}

export default function App() {
  const [connected, setConnected] = useState(false)
  const [analyses, setAnalyses] = useState<Analysis[]>([])
  const [position, setPosition] = useState('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    // Get WebSocket URL from environment variable or use default
    const wsUrl = import.meta.env.VITE_ANALYSIS_SERVER_WS || 'ws://localhost:8765'
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('Connected to analysis server')
      setConnected(true)
      
      // Start infinite analysis with MultiPV=3 and streaming enabled
      ws.send(JSON.stringify({
        type: 'analyze',
        fen: position,
        engine: 'stockfish',
        multiPV: 3,
        depth: 20,
        stream: true,
        infinite: true
      }))
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        // Debug: Log what we receive
        console.log('Received:', data)
        
        // Handle real-time streaming updates
        if (data.type === 'analysis_update') {
          // If we have multiple lines (MultiPV), use them
          if (data.lines && Array.isArray(data.lines)) {
            console.log('Processing MultiPV lines:', data.lines.length)
            setAnalyses(data.lines.map((line: AnalysisLine, index: number) => ({
              pv: index + 1,
              depth: line.depth || data.depth || 0,
              score: typeof line.evaluation === 'number' ? line.evaluation : 0,
              mate: typeof line.evaluation === 'string' && line.evaluation.includes('mate') 
                ? parseInt(line.evaluation.split(' ')[1]) 
                : undefined,
              line: line.pv || []
            })))
          } else {
            // Single line update
            setAnalyses([{
              pv: 1,
              depth: data.depth || 0,
              score: data.evaluation || 0,
              line: data.pv || []
            }])
          }
        }
        // Handle final analysis result
        else if (data.type === 'analysis_result') {
          console.log('Analysis complete:', data)
        }
        // Handle errors
        else if (data.type === 'error') {
          console.error('Server error:', data.message)
        }
      } catch (err) {
        console.error('Failed to parse message:', err)
      }
    }

    ws.onclose = () => {
      console.log('Disconnected from analysis server')
      setConnected(false)
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    return () => {
      ws.close()
    }
  }, [position])

  const formatScore = (analysis: Analysis) => {
    if (analysis.mate !== undefined) {
      return `M${analysis.mate}`
    }
    return (analysis.score / 100).toFixed(2)
  }

  return (
    <div style={{ padding: '2rem', fontFamily: 'monospace' }}>
      <h1>Chess Analysis</h1>
      
      <div style={{ marginBottom: '1rem' }}>
        <strong>Connection: </strong>
        <span style={{ color: connected ? 'green' : 'red' }}>
          {connected ? '✓ Connected' : '✗ Not Connected'}
        </span>
      </div>

      <div style={{ marginBottom: '2rem' }}>
        <strong>Position: </strong>
        <input 
          type="text" 
          value={position}
          onChange={(e) => setPosition(e.target.value)}
          style={{ width: '100%', padding: '0.5rem', marginTop: '0.5rem' }}
          placeholder="Enter FEN position"
        />
      </div>

      <h2>Live Analysis (MultiPV=3)</h2>
      
      {analyses.length === 0 ? (
        <p style={{ color: '#666' }}>Waiting for analysis...</p>
      ) : (
        <div>
          {analyses.map((analysis) => (
            <div 
              key={analysis.pv}
              style={{
                border: '1px solid #ccc',
                padding: '1rem',
                marginBottom: '1rem',
                borderRadius: '4px',
                backgroundColor: analysis.pv === 1 ? '#f0f8ff' : '#fff'
              }}
            >
              <div style={{ marginBottom: '0.5rem' }}>
                <strong>Variation {analysis.pv}</strong>
                {' | '}
                <span>Depth: {analysis.depth}</span>
                {' | '}
                <span style={{ 
                  fontWeight: 'bold',
                  color: analysis.score > 0 ? 'green' : analysis.score < 0 ? 'red' : 'black'
                }}>
                  Score: {formatScore(analysis)}
                </span>
              </div>
              
              <div style={{ 
                backgroundColor: '#f5f5f5', 
                padding: '0.5rem',
                borderRadius: '3px',
                overflowX: 'auto',
                whiteSpace: 'nowrap'
              }}>
                <strong>Line:</strong> {analysis.line.slice(0, 10).join(' ') || 'Calculating...'}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
