import { useState } from 'react'

export default function App() {
  const [videoUrl, setVideoUrl] = useState('')

  return (
    <div style={{ padding: '2rem' }}>
      <h1>Video Analysis</h1>
      <p>Analyze chess game videos and extract positions and moves.</p>
      
      <div style={{ marginTop: '2rem' }}>
        <input
          type="text"
          value={videoUrl}
          onChange={(e) => setVideoUrl(e.target.value)}
          placeholder="Enter video URL..."
          style={{ width: '300px', padding: '0.5rem' }}
        />
        <button style={{ marginLeft: '1rem', padding: '0.5rem 1rem' }}>
          Analyze
        </button>
      </div>
    </div>
  )
}
