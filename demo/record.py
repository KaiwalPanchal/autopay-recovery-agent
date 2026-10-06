#!/usr/bin/env python3
"""Record terminal demos by running REAL commands and rendering their captured output.

Nothing is faked: each step is executed in a shell, its stdout/stderr is captured, and the
text is replayed in a terminal-style window (typing effect + line-by-line reveal) and encoded
with ffmpeg to MP4 + GIF.  Re-run to regenerate:  python demo/record.py [scene ...]

Scenes live in demo/scenes.json:
  {"scene-name": {"title": "...", "cwd": "..", "env": {"K": "v" | "gen:token"},
                  "steps": [{"cmd": "...", "max_lines": 24, "pause": 1.5,
                             "bg": false, "wait": 0}]}}
A step with "bg": true starts the command hidden in the background (e.g. a server), waits
`wait` seconds, and is killed when the scene ends.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
W, H = 1280, 720
BAR = 40
PAD = 18
FONT_SIZE = 18
LINE_H = 24
BG, FG, DIM = (22, 24, 30), (214, 218, 228), (120, 128, 148)
PROMPT, OK, BAD = (120, 200, 255), (130, 220, 150), (255, 120, 120)
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
EMOJI = re.compile("[\U0001F000-\U0001FFFF\u2600-\u27BF\uFE0F\u200d]")


def find_font() -> str:
    for p in (r"C:\Windows\Fonts\consola.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
              "/System/Library/Fonts/Menlo.ttc"):
        if Path(p).exists():
            return p
    raise SystemExit("no monospace font found")


FONT = ImageFont.truetype(find_font(), FONT_SIZE)
CHAR_W = FONT.getlength("M")
COLS = int((W - 2 * PAD) // CHAR_W)
ROWS = (H - BAR - 2 * PAD) // LINE_H


def clean(s: str) -> str:
    return EMOJI.sub("", ANSI.sub("", s)).replace("\t", "    ").rstrip("\r")


def wrap(line: str) -> list[str]:
    if len(line) <= COLS:
        return [line]
    return [line[i:i + COLS] for i in range(0, len(line), COLS)]


def color_for(line: str) -> tuple:
    if line.startswith("$ "):
        return PROMPT
    low = line.lower()
    if any(k in low for k in ("passed", "[ok]", "gate passed", "100.0%", "recovered", "healthy")):
        return OK
    if any(k in low for k in ("failed", "gate failed", "error", "401", "403")):
        return BAD
    return FG


def render(lines: list[tuple[str, tuple]], title: str, cursor: bool) -> Image.Image:
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, BAR], fill=(36, 39, 48))
    for i, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        d.ellipse([16 + i * 24, 13, 30 + i * 24, 27], fill=c)
    d.text((W // 2 - FONT.getlength(title) / 2, 9), title, font=FONT, fill=DIM)
    vis = lines[-ROWS:]
    y = BAR + PAD
    for text, col in vis:
        d.text((PAD, y), text, font=FONT, fill=col)
        y += LINE_H
    if cursor and vis:
        last = vis[-1][0]
        x = PAD + FONT.getlength(last)
        d.rectangle([x, y - LINE_H + 3, x + CHAR_W * 0.7, y - 4], fill=FG)
    return im


class Timeline:
    def __init__(self, workdir: Path, title: str):
        self.dir, self.title, self.frames, self.n = workdir, title, [], 0
        self.lines: list[tuple[str, tuple]] = []

    def snap(self, dur: float, cursor: bool = False):
        p = self.dir / f"f{self.n:05d}.png"
        render(self.lines, self.title, cursor).save(p)
        self.frames.append((p, dur))
        self.n += 1

    def type_cmd(self, cmd: str):
        base = len(self.lines)
        shown = "$ "
        self.lines.append((shown, PROMPT))
        self.snap(0.35, True)
        step = max(1, len(cmd) // 45)
        for i in range(0, len(cmd), step):
            shown = "$ " + cmd[: i + step]
            self.lines[base] = (shown[:COLS], PROMPT)
            self.snap(0.035, True)
        self.lines[base] = (("$ " + cmd)[:COLS], PROMPT)
        self.snap(0.4, False)

    def emit(self, out: list[str], max_lines: int):
        if len(out) > max_lines:
            out = out[:max_lines] + [f"... ({len(out) - max_lines} more lines)"]
        per = 0.05 if len(out) <= 40 else 0.03
        batch = max(1, len(out) // 60)
        for i, raw in enumerate(out):
            for ln in wrap(raw):
                self.lines.append((ln, color_for(ln)))
            if i % batch == 0:
                self.snap(per)
        self.snap(0.05)

    def encode(self, out_base: Path, hold: float):
        self.frames[-1] = (self.frames[-1][0], hold)
        lst = self.dir / "list.txt"
        with lst.open("w") as f:
            for p, dur in self.frames:
                f.write(f"file '{p.as_posix()}'\nduration {dur}\n")
            f.write(f"file '{self.frames[-1][0].as_posix()}'\n")
        ff = shutil.which("ffmpeg") or "ffmpeg"
        mp4, gif = out_base.with_suffix(".mp4"), out_base.with_suffix(".gif")
        subprocess.run([ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-vf", "fps=20,format=yuv420p", "-movflags", "+faststart", str(mp4)], check=True)
        pal = self.dir / "pal.png"
        vf = "fps=10,scale=960:-1:flags=lanczos"
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(mp4), "-vf", f"{vf},palettegen=max_colors=64",
                        str(pal)], check=True)
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(mp4), "-i", str(pal), "-lavfi",
                        f"{vf}[x];[x][1:v]paletteuse=dither=none", str(gif)], check=True)
        return mp4, gif


def bash() -> str:
    for c in (shutil.which("bash"), r"C:\Program Files\Git\bin\bash.exe"):
        if c and Path(c).exists():
            return c
    raise SystemExit("bash not found")


def run_scene(name: str, scene: dict, root: Path, outdir: Path):
    cwd = (root / scene.get("cwd", ".")).resolve()
    env = dict(os.environ, NO_COLOR="1", TERM="dumb", PYTHONIOENCODING="utf-8", PYTHONUTF8="1",
               COLUMNS=str(COLS - 2))
    tmp = Path(tempfile.mkdtemp(prefix="demo_"))
    env["DEMO_TMP"] = tmp.as_posix()
    env["DEMO_ROOT"] = root.as_posix()
    for k, v in scene.get("env", {}).items():
        env[k] = secrets.token_urlsafe(16) if v == "gen:token" else v.replace("{tmp}", tmp.as_posix())
    frames = Path(tempfile.mkdtemp(prefix="frames_"))
    tl = Timeline(frames, scene["title"])
    bgs: list[subprocess.Popen] = []
    try:
        for st in scene["steps"]:
            cmd = st["cmd"]
            tl.type_cmd(cmd)
            if st.get("bg"):
                bgs.append(subprocess.Popen([bash(), "-c", cmd], cwd=cwd, env=env,
                                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
                time.sleep(st.get("wait", 3))
                tl.lines.append(("(server running in background)", DIM))
                tl.snap(0.8)
                continue
            r = subprocess.run([bash(), "-c", cmd], cwd=cwd, env=env, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=st.get("timeout", 300))
            out = [clean(x) for x in (r.stdout + r.stderr).splitlines()]
            while out and not out[-1].strip():
                out.pop()
            tl.emit(out, st.get("max_lines", 22))
            if r.returncode != 0 and not st.get("allow_fail"):
                print(f"[{name}] step failed (exit {r.returncode}): {cmd}", file=sys.stderr)
                sys.exit(1)
            tl.snap(st.get("pause", 1.5))
            tl.lines.append(("", FG))
        outdir.mkdir(parents=True, exist_ok=True)
        mp4, gif = tl.encode(outdir / name, hold=3.0)
        print(f"[{name}] {mp4.name} {mp4.stat().st_size // 1024} KB, {gif.name} {gif.stat().st_size // 1024} KB")
    finally:
        for p in bgs:  # kill the whole tree: terminate() only stops the shell wrapper on Windows
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
            else:
                p.terminate()
        shutil.rmtree(frames, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    scenes = json.loads((HERE / "scenes.json").read_text(encoding="utf-8"))
    want = sys.argv[1:] or list(scenes)
    for n in want:
        run_scene(n, scenes[n], HERE.parent, HERE)


if __name__ == "__main__":
    main()
