#!/usr/bin/env python3
"""Draw a year of GitHub contributions as a turning galaxy: the year winds in from the rim to the core along
two spiral arms, every day is a speck of dust, every day you shipped is a star. The year ago sits in the core,
today on the rim, so the galaxy grows outward as you ship.

    python3 galaxy.py --user Firegod1991 --out galaxy.svg       # asks GitHub, needs GITHUB_TOKEN
    python3 galaxy.py --days sample.json --out galaxy.svg       # from a saved calendar

One animated SVG with no script in it, so it plays inside a README. Needs nothing but Python.
"""

import argparse
import json
import math
import os
import random

from starchart import ask_github, streaks

W, H = 880, 300
CX, CY = 300, 152          # the center of the galaxy
TILT = 0.46                # how flat the disc looks: 1 is face on
TURN = 150                 # seconds for one whole turn
STAR = {1: ("#8ec5ff", 2.2), 2: ("#bfe0ff", 2.8), 3: ("#ffe9a8", 3.5), 4: ("#ffb454", 4.4)}


WIND = 2.7 * math.pi      # how far an arm winds from the core to the rim


def arm_point(t, arm):
    """A point on an arm: t is 0 at the core and 1 on the rim."""
    r = 26 + 250 * t ** 0.9
    a = arm * math.pi + t * WIND
    return r, a


def spiral(days):
    """Put every day on one of two arms: a year ago in the core, today on the rim."""
    n = len(days)
    dust = random.Random(7)
    for i, day in enumerate(days):
        t = i / max(1, n - 1)
        r, a = arm_point(t, i % 2)
        a += dust.uniform(-0.08, 0.08)
        r += dust.uniform(-5, 5)
        day["gx"], day["gy"] = r * math.cos(a), r * math.sin(a)
    return days


def arms_dust(sky, count=700):
    """Stars that are not days: they crowd the arms so the disc reads as a galaxy."""
    out = []
    for _ in range(count):
        t = sky.random() ** 0.8
        r, a = arm_point(t, sky.randrange(2))
        a += sky.gauss(0, 0.20)
        r += sky.gauss(0, 9 + 10 * t)
        out.append('<circle cx="%.1f" cy="%.1f" r="%.2f" fill="#cdd7ff" opacity="%.2f"/>'
                   % (r * math.cos(a), r * math.sin(a), sky.uniform(0.3, 1.0), sky.uniform(0.06, 0.38)))
    return "".join(out)


def arm_glow(arm, steps=60):
    """The soft band of light along an arm."""
    pts = []
    for k in range(steps + 1):
        r, a = arm_point(k / steps, arm)
        pts.append("%.1f %.1f" % (r * math.cos(a), r * math.sin(a)))
    return "M" + " L".join(pts)


def build(days, user="you"):
    days = spiral(days)
    total = sum(d["count"] for d in days)
    shipped = [d for d in days if d["count"]]
    best = max((d["count"] for d in days), default=0)
    longest, current = streaks(days)
    sky = random.Random(3)

    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img" '
           'aria-label="A year of GitHub contributions drawn as a turning galaxy: %d contributions on %d days">'
           % (W, H, W, H, total, len(shipped))]
    out.append("""<defs>
  <radialGradient id="bg" cx="34%" cy="50%" r="80%"><stop offset="0" stop-color="#101a3a"/><stop offset="0.55" stop-color="#070b1c"/><stop offset="1" stop-color="#03040b"/></radialGradient>
  <radialGradient id="core" r="50%"><stop offset="0" stop-color="#fff6dc" stop-opacity="1"/><stop offset="0.18" stop-color="#ffd27a" stop-opacity="0.85"/><stop offset="0.5" stop-color="#ff8a3d" stop-opacity="0.22"/><stop offset="1" stop-color="#ff8a3d" stop-opacity="0"/></radialGradient>
  <radialGradient id="haze" r="50%"><stop offset="0" stop-color="#6d7dff" stop-opacity="0.32"/><stop offset="0.6" stop-color="#3b2d8f" stop-opacity="0.12"/><stop offset="1" stop-color="#3b2d8f" stop-opacity="0"/></radialGradient>
  <radialGradient id="neb" r="50%"><stop offset="0" stop-color="#c04bff" stop-opacity="0.22"/><stop offset="1" stop-color="#c04bff" stop-opacity="0"/></radialGradient>
  <linearGradient id="tail" x1="0" x2="1"><stop offset="0" stop-color="#9fe8ff" stop-opacity="0"/><stop offset="1" stop-color="#ffffff" stop-opacity="0.95"/></linearGradient>
  <filter id="glow" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="9"/></filter>
  <clipPath id="card"><rect width="%d" height="%d" rx="14"/></clipPath>
</defs>""".replace("%d\" height=\"%d", "%d\" height=\"%d" % (W, H)))

    css = ["""
    .turn { animation: turn %ss linear infinite; transform-origin: 0px 0px; }
    @keyframes turn { to { transform: rotate(-360deg); } }
    .tw { animation: tw 4.2s ease-in-out infinite; }
    @keyframes tw { 0%%, 100%% { opacity: 1; } 50%% { opacity: 0.35; } }
    .pulse { animation: pulse 5s ease-in-out infinite; transform-box: fill-box; transform-origin: center; }
    @keyframes pulse { 0%%, 100%% { transform: scale(1); opacity: 0.9; } 50%% { transform: scale(1.18); opacity: 1; } }
    .drift { animation: drift 90s linear infinite; }
    @keyframes drift { to { transform: translateX(-%dpx); } }
    .shoot { animation: shoot 11s linear infinite; opacity: 0; }
    @keyframes shoot { 0%%, 72%% { opacity: 0; transform: translate(0, 0); } 74%% { opacity: 1; } 82%% { opacity: 0; transform: translate(-240px, 120px); } 100%% { opacity: 0; transform: translate(-240px, 120px); } }
    .scan { animation: scan 6s ease-in-out infinite; }
    @keyframes scan { 0%%, 100%% { opacity: 0.25; } 50%% { opacity: 1; } }
    .ping { animation: ping 3s ease-out infinite; transform-box: fill-box; transform-origin: center; }
    @keyframes ping { 0%% { transform: scale(0.2); opacity: 0.9; } 100%% { transform: scale(2.6); opacity: 0; } }
    text { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
    .k { fill: #7f93b8; font-size: 9.5px; letter-spacing: 1.6px; }
    .v { fill: #eef4ff; font-size: 20px; font-weight: 700; }
    .t { fill: #f4f8ff; font-size: 14px; font-weight: 700; letter-spacing: 3.2px; }
    .s { fill: #39d0ff; font-size: 9.5px; letter-spacing: 2px; }
    @media (prefers-reduced-motion: reduce) { .turn, .tw, .pulse, .drift, .shoot, .scan, .ping { animation: none; } .shoot { opacity: 0; } }
""" % (TURN, W)]

    out.append('<g clip-path="url(#card)"><rect width="%d" height="%d" fill="url(#bg)"/>' % (W, H))
    # Far stars, two copies side by side so the drift never shows a seam.
    far = "".join('<circle cx="%.1f" cy="%.1f" r="%.2f" fill="#ffffff" opacity="%.2f"/>'
                  % (sky.uniform(0, W), sky.uniform(0, H), sky.uniform(0.3, 1.0), sky.uniform(0.15, 0.7)) for _ in range(110))
    out.append('<g class="drift"><g>%s</g><g transform="translate(%d 0)">%s</g></g>' % (far, W, far))
    out.append('<ellipse cx="%d" cy="%d" rx="150" ry="70" fill="url(#neb)" filter="url(#soft)"/>' % (CX + 330, CY - 70))
    out.append('<g class="shoot"><line x1="%d" y1="24" x2="%d" y2="6" stroke="url(#tail)" stroke-width="1.4" stroke-linecap="round"/></g>' % (W - 150, W - 116))

    # The galaxy: a flat disc seen at an angle, turning slowly.
    out.append('<g transform="translate(%d %d) scale(1 %.2f)">' % (CX, CY, TILT))
    out.append('<circle r="285" fill="url(#haze)"/>')
    out.append('<g class="turn">')
    for arm in (0, 1):
        out.append('<path d="%s" fill="none" stroke="#5b6cff" stroke-width="26" stroke-linecap="round" opacity="0.16" filter="url(#soft)"/>' % arm_glow(arm))
        out.append('<path d="%s" fill="none" stroke="#a6b6ff" stroke-width="7" stroke-linecap="round" opacity="0.10" filter="url(#soft)"/>' % arm_glow(arm))
    out.append('<circle r="278" fill="none" stroke="#3a4f86" stroke-width="0.6" stroke-dasharray="2 7" opacity="0.5"/>')
    out.append("".join('<circle cx="%.1f" cy="%.1f" r="%.2f" fill="#a9b9e8" opacity="%.2f"/>'
                       % (d["gx"], d["gy"], 1.15, 0.35 + 0.3 * sky.random()) for d in days if not d["count"]))
    out.append(arms_dust(sky))
    for i, d in enumerate(shipped):
        colour, size = STAR[max(1, d["level"])]
        flare = ""
        if d["level"] >= 3:
            reach = size * 2.8
            flare = ('<path d="M%.1f %.1f H%.1f M%.1f %.1f V%.1f" stroke="%s" stroke-width="0.9" stroke-linecap="round" opacity="0.8"/>'
                     % (d["gx"] - reach, d["gy"], d["gx"] + reach, d["gx"], d["gy"] - reach, d["gy"] + reach, colour))
        out.append('<g class="tw" style="animation-delay:-%.1fs">%s<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" filter="url(#glow)"/>'
                   '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#ffffff"/></g>'
                   % (sky.uniform(0, 4.2), flare, d["gx"], d["gy"], size, colour, d["gx"], d["gy"], size * 0.4))
    out.append('</g>')  # turn
    out.append('<g class="pulse"><circle r="46" fill="url(#core)"/></g><circle r="4.5" fill="#fffaf0" filter="url(#glow)"/>')
    out.append('<circle class="ping" r="10" fill="none" stroke="#ffd27a" stroke-width="1.2"/>')
    out.append('</g>')  # disc

    # Read out, on the right.
    x = 600
    out.append('<text class="t" x="%d" y="44">%s</text>' % (x, user.upper()[:22]))
    out.append('<text class="s scan" x="%d" y="62">● GALAXY OF ONE YEAR</text>' % x)
    rows = [("CONTRIBUTIONS", total), ("DAYS SHIPPED", len(shipped)), ("BEST DAY", best),
            ("LONGEST RUN", "%d d" % longest), ("CURRENT RUN", "%d d" % current)]
    for i, (k, v) in enumerate(rows):
        col, row = i % 2, i // 2
        out.append('<text class="k" x="%d" y="%d">%s</text><text class="v" x="%d" y="%d">%s</text>'
                   % (x + col * 130, 98 + row * 56, k, x + col * 130, 120 + row * 56, v))
    out.append('<text class="k" x="%d" y="%d" opacity="0.8">CORE: A YEAR AGO  ·  RIM: TODAY</text>' % (x, H - 22))
    out.append('</g>')  # card
    out.insert(2, "<style>%s</style>" % "".join(css))
    out.append("</svg>")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--user", help="the GitHub login to draw")
    ap.add_argument("--days", help="a saved calendar: a JSON list of {date, count, level}")
    ap.add_argument("--out", default="galaxy.svg")
    args = ap.parse_args()
    if args.days:
        with open(args.days, encoding="utf-8") as f:
            saved = json.load(f)
        days = saved["days"] if isinstance(saved, dict) else saved
        user = args.user or (saved.get("user") if isinstance(saved, dict) else None) or "you"
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not args.user or not token:
            raise SystemExit("give --user and set GITHUB_TOKEN, or give --days")
        user, days = args.user, ask_github(args.user, token)
    svg = build(days, user)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(svg)
    print("%s: %d days, %d bytes" % (args.out, len(days), len(svg)))


if __name__ == "__main__":
    main()
