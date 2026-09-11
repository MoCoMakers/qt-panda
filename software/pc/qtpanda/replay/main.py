"""Replay entry point: ``python main.py [day]`` from this folder.

Opens the sweep player on the SAME data the instrument GUI writes
(TeamUpdate/data — both sides resolve it through the one data_paths.py
authority).  No argument = today's folder, i.e. the same thing as the
GUI's Review Day button; or pass a day name / path / .frames file.

(The team-bundle main.py is a sibling of this idea: same command, but
it defaults to the day shipped inside the bundle.)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import data_paths
import sweep_player


def main():
    if len(sys.argv) < 2:
        day = data_paths.day_name()
        print(f"[main] no day given — opening today ({day})")
        sys.argv.append(day)
    sweep_player.main()


if __name__ == "__main__":
    main()
