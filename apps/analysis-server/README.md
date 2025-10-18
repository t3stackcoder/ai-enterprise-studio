# Chess Analysis Service

WebSocket server for chess position analysis using Stockfish and Leela Chess Zero.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Download Chess Engines

#### Stockfish

1. Download from: https://stockfishchess.org/download/
2. Place `stockfish.exe` in `engines/` directory

#### Leela Chess Zero

1. Download engine from: https://lczero.org/play/download/
2. Download weights from: https://lczero.org/play/networks/bestnets/
3. Place `lc0.exe` in `engines/` directory
4. Place weights file (e.g., `best_network.pb.gz`) in `engines/weights/` directory

### Directory Structure

```
ai-enterprise-studio/
├── engines/
│   ├── stockfish.exe
│   ├── lc0.exe
│   └── weights/
│       └── best_network.pb.gz
└── apps/
    └── analysis-server/
        ├── server.py
        ├── engine_manager.py
        ├── requirements.txt
        └── tests/
```

## Run Server

```bash
cd apps/analysis-server
python server.py
```

Server runs on: `ws://localhost:8001`

## WebSocket API

### Request Format

#### Analyze Position

```json
{
  "type": "analyze",
  "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
  "engine": "stockfish",
  "depth": 20,
  "movetime": 2000
}
```

**Parameters:**

- `fen` (required): Position in FEN notation
- `engine` (optional): "stockfish" or "leela" (default: "stockfish")
- `depth` (optional): Search depth in plies (default: 20)
- `movetime` (optional): Max analysis time in milliseconds

#### Check Status

```json
{
  "type": "status"
}
```

#### Ping

```json
{
  "type": "ping",
  "timestamp": 1234567890
}
```

### Response Format

#### Analysis Result

```json
{
  "type": "analysis_result",
  "engine": "stockfish",
  "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
  "result": {
    "best_move": "e7e5",
    "evaluation": 0.3,
    "depth": 20,
    "nodes": 1234567,
    "pv": ["e7e5", "g1f3", "b8c6", "f1c4"]
  }
}
```

**Result Fields:**

- `best_move`: Best move in UCI format (e.g., "e2e4", "e1g1" for castling)
- `evaluation`: Position evaluation in pawns (positive = white advantage) or "mate X"
- `depth`: Actual search depth reached
- `nodes`: Number of positions evaluated
- `pv`: Principal variation (best continuation)

#### Status Response

```json
{
  "type": "status",
  "active_connections": 3,
  "engines": {
    "stockfish": true,
    "leela": true
  }
}
```

#### Error Response

```json
{
  "type": "error",
  "message": "Error description"
}
```

## Example Usage (JavaScript)

```javascript
const ws = new WebSocket("ws://localhost:8001");

ws.onopen = () => {
  // Analyze starting position
  ws.send(
    JSON.stringify({
      type: "analyze",
      fen: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
      engine: "stockfish",
      depth: 20,
    })
  );
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Analysis result:", data);
};
```

## Engine Notes

### Stockfish

- Fast tactical analysis
- Good for precise evaluations
- Supports up to 3 concurrent analyses

### Leela Chess Zero

- Neural network-based evaluation
- Better positional understanding
- Slower, GPU-recommended
- Limited to 1 concurrent analysis (resource intensive)

## Troubleshooting

**Engines not found:**

- Check that executables are in `engines/` directory
- Verify file permissions (executable on Linux/Mac)
- Check server logs for path issues

**Leela not working:**

- Ensure weights file is downloaded and in correct location
- Check GPU/CUDA drivers if using GPU acceleration
- Can run on CPU but will be slower

**Analysis timeout:**

- Reduce depth or movetime parameters
- Check system resources
- Verify engine process isn't hanging
