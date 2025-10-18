import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'

function Home() {
  return (
    <div>
      <h2>Home</h2>
      <p>Welcome to the AI Enterprise Studio shell.</p>
      <p>Module Federation is configured and ready.</p>
    </div>
  )
}

function Analysis() {
  return (
    <div>
      <h2>Analysis</h2>
      <p>Chess analysis remote will be loaded here.</p>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div style={{ padding: '2rem' }}>
        <h1>AI Enterprise Studio</h1>
        <nav style={{ marginTop: '1rem', marginBottom: '2rem' }}>
          <Link to="/" style={{ marginRight: '1rem' }}>Home</Link>
          <Link to="/analysis" style={{ marginRight: '1rem' }}>Analysis</Link>
        </nav>
        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/analysis" element={<Analysis />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
