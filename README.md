# AI Enterprise Studio

A Turborepo monorepo for chess analysis and AI-powered tools, featuring WebSocket-based real-time analysis using Stockfish and Leela Chess Zero engines.

## Project Structure

```
ai-enterprise-studio/
├── apps/
│   └── analysis-server/     # Chess Analysis WebSocket Server
│       ├── server.py
│       ├── engine_manager.py
│       ├── requirements.txt
│       └── tests/
├── packages/
│   └── shared/              # Shared types and utilities
├── engines/                 # Chess engines (gitignored)
├── turbo.json              # Turborepo configuration
└── package.json            # Root package configuration
```

## Tech Stack

- **Turborepo**: Monorepo build system
- **Python 3.11**: Backend runtime
- **FastAPI**: Modern Python web framework
- **WebSockets**: Real-time communication
- **PostgreSQL**: Relational database
- **Redis**: Token blacklist and caching
- **TypeScript**: Shared types and utilities
- **Stockfish**: Traditional chess engine
- **Leela Chess Zero**: Neural network chess engine

## Prerequisites

- Node.js 18+ and npm 9+
- Python 3.11+ (for local development)
- Chess engines (Stockfish, LC0) - see setup below

## Quick Start

### 1. Install Dependencies

```bash
# Install root dependencies
npm install

# Install workspace dependencies
npm install --workspaces
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your API keys
# ANTHROPIC_API_KEY=your_key_here
```

### 3. Run Locally (Development)

```bash
# Install Python dependencies for analysis server
cd apps/analysis-server
pip install -r requirements.txt

# Run the server
npm run dev
```

The analysis server will be available at `ws://localhost:8765`

## Development

### Turborepo Commands

```bash
# Run all dev servers
npm run dev

# Build all apps and packages
npm run build

# Run all tests
npm run test

# Lint all code
npm run lint

# Clean all build outputs
npm run clean
```

## Apps

### Analysis Server

WebSocket server providing real-time chess position analysis.

**Features:**

- Multi-engine support (Stockfish, Leela)
- Real-time streaming analysis
- MultiPV (multiple candidate moves)
- Configurable depth and time limits
- Connection management

**Port:** `8765`  
**API Documentation:** See [apps/analysis-server/README.md](apps/analysis-server/README.md)

## Packages

### @ai-enterprise-studio/shared

Shared TypeScript types and utilities used across applications.

**Contents:**

- Chess analysis types
- WebSocket message types
- Utility functions (FEN validation, evaluation formatting, etc.)

## Engine Setup

### Stockfish

1. Download from [official-stockfish.github.io](https://github.com/official-stockfish/Stockfish)
2. Place executable in `engines/` directory
3. Update `.env` with correct path

### Leela Chess Zero

1. Download from [lczero.org](https://lczero.org)
2. Download neural network weights
3. Place in `engines/` directory
4. Update `.env` with paths

## Adding New Apps

1. Create new app directory in `apps/`:

   ```bash
   mkdir apps/my-new-app
   cd apps/my-new-app
   npm init -y
   ```

2. Add to Turborepo pipeline in `turbo.json`

3. Import shared packages:
   ```json
   {
     "dependencies": {
       "@ai-enterprise-studio/shared": "*"
     }
   }
   ```

## Architecture

This monorepo uses Turborepo for:

- **Parallel execution**: Run tasks across workspaces simultaneously
- **Caching**: Skip redundant builds and tests
- **Dependency awareness**: Build in correct order

Each app is independently deployable, while sharing common utilities from the `packages/` directory.

## Contributing

1. Create a feature branch
2. Make changes in appropriate workspace
3. Run `npm run test` to ensure all tests pass
4. Run `npm run build` to verify builds succeed
5. Submit pull request

## Future Roadmap

- [ ] Web frontend for chess analysis
- [ ] Commentary/ML service for natural language analysis
- [ ] API gateway for REST endpoints
- [ ] Game database integration
- [ ] Opening book explorer
- [ ] Tournament analysis tools
- [ ] Performance analytics dashboard

## License

Private - All Rights Reserved

## Support

For issues or questions, please open an issue in the repository.
