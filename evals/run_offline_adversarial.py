"""CLI entry point: python evals/run_offline_adversarial.py (offline, no keys, throwaway DB)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from offline_adversarial import main
if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
