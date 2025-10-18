export default function App() {
  // TODO: Add WebSocket connection
  // const [connected, setConnected] = useState(false)
  // useEffect(() => {
  //   const ws = new WebSocket('ws://localhost:8765')
  //   ws.onopen = () => setConnected(true)
  //   ws.onclose = () => setConnected(false)
  //   return () => ws.close()
  // }, [])

  return (
    <div style={{ padding: '2rem' }}>
      <h1>Chess Analysis</h1>
      <p>� Not connected</p>
      <p>WebSocket connection to analysis server: ws://localhost:8765</p>
      {/* Add your analysis UI here */}
    </div>
  )
}
