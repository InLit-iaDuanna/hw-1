from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"


def load_rows(path: Path) -> list[dict[str, float]]:
    with path.open("r", encoding="utf-8") as f:
        return [
            {key: float(value) for key, value in row.items()}
            for row in csv.DictReader(f)
        ]


def font(size: int) -> ImageFont.ImageFont:
    for name in ["msyh.ttc", "simhei.ttf", "arial.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def project(
    x: float, z: float, cx: float, cz: float, scale: float, width: int, height: int
) -> tuple[int, int]:
    px = int(width * 0.48 + (x - cx) * scale)
    py = int(height * 0.54 - (z - cz) * scale)
    return px, py


def row_at(
    t: float, rows: list[dict[str, float]], params: dict[str, float]
) -> dict[str, float]:
    times = np.array([r["time"] for r in rows])
    idx = int(np.searchsorted(times, t, side="right") - 1)
    idx = max(0, min(idx, len(rows) - 2))
    a, b = rows[idx], rows[idx + 1]
    u = (t - a["time"]) / max(b["time"] - a["time"], 1e-9)

    step_angle = 2.0 * math.pi / int(params["spoke_count"])
    theta_a = a["theta"] + a["step"] * step_angle
    theta_b = b["theta"] + b["step"] * step_angle
    if theta_b < theta_a:
        theta_b += step_angle

    return {
        "time": t,
        "step": (1.0 - u) * a["step"] + u * b["step"],
        "hub_x": (1.0 - u) * a["hub_x"] + u * b["hub_x"],
        "hub_z": (1.0 - u) * a["hub_z"] + u * b["hub_z"],
        "theta": (1.0 - u) * theta_a + u * theta_b,
        "theta_dot": (1.0 - u) * a["theta_dot"] + u * b["theta_dot"],
    }


def draw_frame(
    row: dict[str, float],
    trail: list[dict[str, float]],
    spoke_count: int,
    leg_length: float,
    slope_deg: float,
    width: int = 1280,
    height: int = 720,
) -> np.ndarray:
    img = Image.new("RGB", (width, height), "#f5f2e8")
    draw = ImageDraw.Draw(img)
    gamma = math.radians(slope_deg)
    hub_x, hub_z = row["hub_x"], row["hub_z"]
    theta = row["theta"]
    scale = 260

    def p(x: float, z: float) -> tuple[int, int]:
        return project(x, z, hub_x, hub_z, scale, width, height)

    ramp = [
        p(float(x), -math.tan(gamma) * float(x))
        for x in np.linspace(hub_x - 2.1, hub_x + 2.5, 80)
    ]
    draw.line(ramp, fill="#6d7d71", width=7)

    for offset in np.linspace(-2.0, 2.5, 10):
        x0 = hub_x + float(offset)
        draw.line(
            [p(x0, -math.tan(gamma) * x0 - 0.5), p(x0, -math.tan(gamma) * x0 + 0.5)],
            fill="#ded8c8",
            width=1,
        )

    if len(trail) > 1:
        pts = [p(r["hub_x"], r["hub_z"]) for r in trail[-260:]]
        draw.line(pts, fill="#143642", width=4)

    step_angle = 2.0 * math.pi / spoke_count
    for i in range(spoke_count):
        q = theta + i * step_angle
        x2 = hub_x - leg_length * math.sin(q)
        z2 = hub_z - leg_length * math.cos(q)
        color = "#d45132" if i == 0 else "#0f7891"
        line_width = 9 if i == 0 else 5
        draw.line([p(hub_x, hub_z), p(x2, z2)], fill=color, width=line_width)
        fx, fz = p(x2, z2)
        r = 10 if i == 0 else 6
        draw.ellipse([fx - r, fz - r, fx + r, fz + r], fill="#20252b")

    hx, hz = p(hub_x, hub_z)
    draw.ellipse([hx - 28, hz - 28, hx + 28, hz + 28], fill="#143642")

    title_font = font(28)
    body_font = font(20)
    draw.text(
        (70, 58), "Rimless passive limit-cycle gait", fill="#143642", font=title_font
    )
    draw.text(
        (70, 100),
        "Gravity-driven Poincare playback, no actuator",
        fill="#4d555b",
        font=body_font,
    )
    draw.text(
        (70, 132),
        f"step {int(row['step'])}   theta_dot {row['theta_dot']:.3f} rad/s",
        fill="#4d555b",
        font=body_font,
    )
    draw.text(
        (70, 164),
        "Downhill direction: +x, wheel angle increases with each step",
        fill="#4d555b",
        font=body_font,
    )

    return np.asarray(img)


def main() -> None:
    rows = load_rows(OUT_DIR / "rimless_limit_cycle_data.csv")
    params = json.loads((OUT_DIR / "rimless_params.json").read_text(encoding="utf-8"))[
        "params"
    ]
    fps = 60
    duration = min(rows[-1]["time"], 18.0)
    frame_count = int(duration * fps)
    frames = []
    trail: list[dict[str, float]] = []

    for i in range(frame_count):
        row = row_at(i / fps, rows, params)
        trail.append(row)
        frames.append(
            draw_frame(
                row,
                trail,
                int(params["spoke_count"]),
                float(params["leg_length"]),
                float(params["slope_deg"]),
            )
        )

    video_path = OUT_DIR / "rimless_limit_cycle.mp4"
    imageio.mimsave(video_path, frames, fps=fps)
    imageio.imwrite(OUT_DIR / "rimless_preview.png", frames[min(180, len(frames) - 1)])
    print(video_path)


if __name__ == "__main__":
    main()
