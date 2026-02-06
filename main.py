from __future__ import annotations

"""
Repo entrypoint: launch the MuJoCo + FastAPI robot server.

Planner entrypoint was moved to `planner_main.py`.
"""

import runpy
import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    robot_dir = repo_root / "with-robot-5th" / "robot"

    # Ensure `simulator.py`, `camera.py`, ... are importable as top-level modules.
    if str(robot_dir) not in sys.path:
        sys.path.insert(0, str(robot_dir))

    try:
        runpy.run_path(str(robot_dir / "main.py"), run_name="__main__")
    except ModuleNotFoundError as e:
        # Common failure mode: user runs with system python instead of the conda env.
        if e.name in {"mujoco", "fastapi", "uvicorn"}:
            msg = (
                f"Missing dependency '{e.name}'.\n\n"
                "You are probably not running inside the conda env.\n"
                "Try one of:\n"
                "  conda activate robot\n"
                "  python main.py\n\n"
                "or (no-activate):\n"
                "  conda run -n robot python main.py\n"
            )
            raise SystemExit(msg) from e
        raise


if __name__ == "__main__":
    main()
