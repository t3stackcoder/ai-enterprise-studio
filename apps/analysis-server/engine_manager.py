"""
Engine Manager - Handles Stockfish and Leela Chess Zero engines
"""

import asyncio
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class EngineManager:
    """Manages chess engine processes and communication"""

    def __init__(self):
        self.stockfish_path: Path | None = None
        self.leela_path: Path | None = None
        self.leela_weights_path: Path | None = None

        self.stockfish_available = False
        self.leela_available = False

        # Engine process pools (for concurrent analysis)
        self.stockfish_semaphore = asyncio.Semaphore(3)  # Max 3 concurrent Stockfish
        self.leela_semaphore = asyncio.Semaphore(1)  # Max 1 concurrent Leela (GPU intensive)

    async def initialize(self):
        """Find and validate engine executables"""
        # Engines are in the project root: ai-enterprise-studio/engines/
        # This file is in: ai-enterprise-studio/apps/analysis-server/
        project_root = Path(__file__).resolve().parent.parent.parent
        engines_dir = project_root / "engines"

        logger.info(f"Looking for engines in: {engines_dir}")
        logger.info(f"Engines directory exists: {engines_dir.exists()}")

        # Find Stockfish
        stockfish_candidates = [
            engines_dir / "stockfish.exe",
            engines_dir / "stockfish",
            Path("stockfish.exe"),
            Path("stockfish"),
        ]

        for candidate in stockfish_candidates:
            logger.info(f"Checking Stockfish candidate: {candidate} - Exists: {candidate.exists()}")
            if candidate.exists():
                self.stockfish_path = candidate
                self.stockfish_available = True
                logger.info(f"Found Stockfish at: {candidate}")
                break

        if not self.stockfish_available:
            logger.warning("Stockfish not found. Place stockfish.exe in engines/ directory")

        # Find Leela
        leela_candidates = [
            engines_dir / "lc0.exe",
            engines_dir / "lc0",
            Path("lc0.exe"),
            Path("lc0"),
        ]

        for candidate in leela_candidates:
            if candidate.exists():
                self.leela_path = candidate
                logger.info(f"Found Leela at: {candidate}")
                break

        # Find Leela weights
        if self.leela_path:
            weights_candidates = [
                engines_dir / "weights" / "best_network.pb.gz",
                engines_dir / "weights" / "best_network.pb",
                engines_dir / "weights.pb.gz",
                engines_dir / "weights.pb",
                engines_dir / "net.pb.gz",
                engines_dir / "net.pb",
            ]

            for candidate in weights_candidates:
                if candidate.exists():
                    self.leela_weights_path = candidate
                    self.leela_available = True
                    logger.info(f"Found Leela weights at: {candidate}")
                    break

        if self.leela_path and not self.leela_available:
            logger.warning(
                "Leela found but weights file missing. Place weights in engines/weights/"
            )
        elif not self.leela_path:
            logger.warning("Leela not found. Place lc0.exe in engines/ directory")

    async def analyze(
        self,
        fen: str,
        engine: str = "stockfish",
        depth: int = 20,
        movetime: int | None = None,
        multipv: int = 1,
        update_callback: Callable | None = None,
        infinite: bool = False,
    ) -> dict[str, Any]:
        """
        Analyze a position with specified engine

        Args:
            fen: Position in FEN notation
            engine: "stockfish" or "leela"
            depth: Search depth (plies)
            movetime: Max time in milliseconds
            multipv: Number of principal variations (top N moves, Stockfish only)
            update_callback: Optional async function to call with real-time updates
            infinite: If True, analyze indefinitely until stopped (requires external stop)

        Returns:
            Analysis results dictionary
        """
        if engine == "stockfish":
            if not self.stockfish_available:
                raise RuntimeError("Stockfish is not available")
            async with self.stockfish_semaphore:
                return await self._analyze_stockfish(
                    fen, depth, movetime, multipv, update_callback, infinite
                )

        elif engine == "leela":
            if not self.leela_available:
                raise RuntimeError("Leela is not available")
            async with self.leela_semaphore:
                return await self._analyze_leela(fen, depth, movetime, update_callback, infinite)

        else:
            raise ValueError(f"Unknown engine: {engine}")

    async def _analyze_stockfish(
        self,
        fen: str,
        depth: int,
        movetime: int | None,
        multipv: int = 1,
        update_callback: Callable | None = None,
        infinite: bool = False,
    ) -> dict[str, Any]:
        """Run Stockfish analysis"""
        try:
            # Start Stockfish process
            process = await asyncio.create_subprocess_exec(
                str(self.stockfish_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Send UCI commands
            commands = [
                "uci\n",
                "isready\n",
            ]

            # Set optimal Stockfish options
            commands.append("setoption name Hash value 2048\n")  # 2GB hash
            commands.append("setoption name Threads value 8\n")  # 8 threads
            commands.append("setoption name Contempt value 0\n")  # Neutral contempt for analysis
            commands.append("setoption name Ponder value false\n")  # No pondering
            commands.append("setoption name UCI_AnalyseMode value true\n")  # Analysis mode

            # Set MultiPV if requested
            if multipv > 1:
                commands.append(f"setoption name MultiPV value {multipv}\n")

            commands.append(f"position fen {fen}\n")

            # Add analysis command
            if infinite:
                commands.append("go infinite\n")
            elif movetime:
                commands.append(f"go movetime {movetime}\n")
            else:
                commands.append(f"go depth {depth}\n")

            # Send all commands
            for cmd in commands:
                process.stdin.write(cmd.encode())
            await process.stdin.drain()

            # Read output
            output_lines = []
            best_move = None
            evaluation = None
            pv = []
            nodes = 0
            actual_depth = 0

            # For MultiPV support
            multipv_lines = {}  # Store info for each PV line

            # Dynamic timeout: movetime + 30 second buffer for engine overhead
            read_timeout = (movetime / 1000.0) + 30.0 if movetime else 60.0

            while True:
                line = await asyncio.wait_for(process.stdout.readline(), timeout=read_timeout)

                if not line:
                    break

                line = line.decode().strip()
                output_lines.append(line)

                # Parse info lines
                if line.startswith("info"):
                    parts = line.split()

                    # Check if this is a MultiPV line
                    current_multipv = 1
                    if "multipv" in parts:
                        idx = parts.index("multipv")
                        if idx + 1 < len(parts):
                            try:
                                current_multipv = int(parts[idx + 1])
                            except ValueError:
                                pass

                    # Extract depth
                    line_depth = actual_depth
                    if "depth" in parts:
                        idx = parts.index("depth")
                        if idx + 1 < len(parts):
                            try:
                                line_depth = int(parts[idx + 1])
                                if current_multipv == 1:
                                    actual_depth = line_depth
                            except ValueError:
                                pass

                    # Extract evaluation
                    line_eval = None
                    if "score" in parts:
                        idx = parts.index("score")
                        if idx + 2 < len(parts):
                            score_type = parts[idx + 1]
                            score_value = parts[idx + 2]

                            if score_type == "cp":
                                # Centipawns
                                line_eval = int(score_value) / 100.0
                            elif score_type == "mate":
                                # Mate in X moves
                                line_eval = f"mate {score_value}"

                    # Extract nodes (only from first PV)
                    if current_multipv == 1 and "nodes" in parts:
                        idx = parts.index("nodes")
                        if idx + 1 < len(parts):
                            try:
                                nodes = int(parts[idx + 1])
                            except ValueError:
                                pass

                    # Extract principal variation
                    line_pv = []
                    if "pv" in parts:
                        idx = parts.index("pv")
                        line_pv = parts[idx + 1 :]

                    # Store MultiPV line data
                    if line_pv and line_eval is not None:
                        multipv_lines[current_multipv] = {
                            "move": line_pv[0] if line_pv else None,
                            "evaluation": line_eval,
                            "pv": line_pv,  # Keep all moves
                            "depth": line_depth,
                        }

                    # Also keep first PV in old format for backward compatibility
                    if current_multipv == 1:
                        if line_eval is not None:
                            evaluation = line_eval
                        if line_pv:
                            pv = line_pv

                    # Send real-time update if callback provided (send all MultiPV lines)
                    if update_callback and line_eval is not None:
                        # Build list of all current MultiPV lines
                        lines_list = [
                            multipv_lines[i]
                            for i in sorted(multipv_lines.keys())
                            if i in multipv_lines
                        ]

                        # Debug logging
                        logger.info(
                            f"MultiPV={multipv}, lines_list length={len(lines_list)}, current_multipv={current_multipv}"
                        )

                        update_data = {
                            "type": "analysis_update",
                            "depth": actual_depth,
                            "nodes": nodes,
                            "evaluation": line_eval if current_multipv == 1 else evaluation,
                            "pv": line_pv if current_multipv == 1 else pv,  # Keep all moves
                            "best_move": (
                                line_pv[0]
                                if (current_multipv == 1 and line_pv)
                                else (pv[0] if pv else None)
                            ),
                            "lines": (
                                lines_list if multipv > 1 else None
                            ),  # Send lines array when MultiPV is requested
                        }
                        await update_callback(update_data)

                # Parse best move
                if line.startswith("bestmove"):
                    parts = line.split()
                    if len(parts) >= 2:
                        best_move = parts[1]
                    break

            # Quit engine
            process.stdin.write(b"quit\n")
            await process.stdin.drain()
            await process.wait()

            result = {
                "best_move": best_move,
                "evaluation": evaluation,
                "depth": actual_depth,
                "nodes": nodes,
                "pv": pv,  # Keep all moves - let frontend decide how many to display
            }

            # Add MultiPV lines if present
            if len(multipv_lines) > 1:
                result["multipv"] = [multipv_lines[i] for i in sorted(multipv_lines.keys())]

            return result

        except TimeoutError:
            logger.error("Stockfish analysis timeout")
            raise RuntimeError("Analysis timeout") from None
        except Exception as e:
            logger.error(f"Stockfish error: {e}", exc_info=True)
            raise

    async def _analyze_leela(
        self,
        fen: str,
        depth: int,
        movetime: int | None,
        update_callback: Callable | None = None,
        infinite: bool = False,
    ) -> dict[str, Any]:
        """Run Leela Chess Zero analysis"""
        try:
            # Start Leela process with weights - backend auto-detected
            # Note: Remove explicit backend flag to let lc0 choose best available
            process = await asyncio.create_subprocess_exec(
                str(self.leela_path),
                f"--weights={self.leela_weights_path}",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Send UCI commands (same protocol as Stockfish)
            commands = [
                "uci\n",
                "isready\n",
            ]

            # Set optimal Leela options
            commands.append("setoption name Threads value 4\n")  # 4 search threads
            commands.append("setoption name NNCacheSize value 2000000\n")  # 2M cache entries
            commands.append("setoption name MinibatchSize value 256\n")  # Larger batches for GPU
            commands.append("setoption name MaxPrefetch value 32\n")  # More prefetch for GPU
            commands.append(
                "setoption name SmartPruningFactor value 0.0\n"
            )  # No pruning for deep analysis
            commands.append("setoption name VerboseMoveStats value true\n")  # More info

            commands.append(f"position fen {fen}\n")

            # Add analysis command
            if infinite:
                commands.append("go infinite\n")
            elif movetime:
                commands.append(f"go movetime {movetime}\n")
            else:
                # Leela uses nodes instead of depth typically
                nodes_limit = depth * 800  # Approximate conversion
                commands.append(f"go nodes {nodes_limit}\n")

            # Send all commands
            for cmd in commands:
                process.stdin.write(cmd.encode())
            await process.stdin.drain()

            # Read output (similar to Stockfish)
            output_lines = []
            best_move = None
            evaluation = None
            pv = []
            nodes = 0
            actual_depth = 0

            # Dynamic timeout: movetime + 60 second buffer (Leela can be slower)
            read_timeout = (movetime / 1000.0) + 60.0 if movetime else 120.0

            while True:
                line = await asyncio.wait_for(process.stdout.readline(), timeout=read_timeout)

                if not line:
                    break

                line = line.decode().strip()
                output_lines.append(line)

                # Parse info lines (same as Stockfish)
                if line.startswith("info"):
                    parts = line.split()

                    if "depth" in parts:
                        idx = parts.index("depth")
                        if idx + 1 < len(parts):
                            try:
                                actual_depth = int(parts[idx + 1])
                            except ValueError:
                                pass

                    if "score" in parts:
                        idx = parts.index("score")
                        if idx + 2 < len(parts):
                            score_type = parts[idx + 1]
                            score_value = parts[idx + 2]

                            if score_type == "cp":
                                evaluation = int(score_value) / 100.0
                            elif score_type == "mate":
                                evaluation = f"mate {score_value}"

                    if "nodes" in parts:
                        idx = parts.index("nodes")
                        if idx + 1 < len(parts):
                            try:
                                nodes = int(parts[idx + 1])
                            except ValueError:
                                pass

                    if "pv" in parts:
                        idx = parts.index("pv")
                        pv = parts[idx + 1 :]

                    # Send real-time update if callback provided
                    if update_callback and evaluation is not None:
                        update_data = {
                            "type": "analysis_update",
                            "depth": actual_depth,
                            "nodes": nodes,
                            "evaluation": evaluation,
                            "pv": pv,  # Keep all moves
                            "best_move": pv[0] if pv else None,
                        }
                        await update_callback(update_data)

                if line.startswith("bestmove"):
                    parts = line.split()
                    if len(parts) >= 2:
                        best_move = parts[1]
                    break

            # Quit engine
            process.stdin.write(b"quit\n")
            await process.stdin.drain()
            await process.wait()

            return {
                "best_move": best_move,
                "evaluation": evaluation,
                "depth": actual_depth,
                "nodes": nodes,
                "pv": pv,  # Keep all moves
            }

        except TimeoutError:
            logger.error("Leela analysis timeout")
            raise RuntimeError("Analysis timeout") from None
        except Exception as e:
            # Try to get stderr output for debugging
            if "process" in locals():
                try:
                    stderr_output = await process.stderr.read()
                    logger.error(f"Leela stderr: {stderr_output.decode()}")
                except Exception:
                    pass
            logger.error(f"Leela error: {e}", exc_info=True)
            raise
