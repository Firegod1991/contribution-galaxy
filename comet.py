#!/usr/bin/env python3
"""Draw a year of GitHub contributions as a comet sweep: a burning comet flies the grid through deep space
and swallows every square you lit, nearest first, each one going off in a flash, and its tail grows longer
with every square it takes. Then it burns off the edge of the board and the next pass begins.

    python3 comet.py --user Firegod1991 --out comet.svg       # asks GitHub, needs GITHUB_TOKEN
    python3 comet.py --days sample.json --out comet.svg       # from a saved calendar

One animated SVG with no script in it, so it plays inside a README. Needs nothing but Python.
"""

import argparse
import datetime
import json
import os
import random

from starchart import ask_github, streaks

STEP, CELL = 15, 11                 # distance from square to square, and the size of a square
LEFT, TOP = 40, 58                  # where the first square sits
W, H = LEFT * 2 + 53 * STEP, TOP + 7 * STEP + 62
SPEED = 230.0                       # pixels a second
START, MOST = 5, 26                 # pieces of tail at the start, and at most: it grows with every square
# A lit square is a charged cell, brighter the more was shipped that day.
CHARGE = {1: "#1c4f7a", 2: "#2a7fc0", 3: "#45b6f0", 4: "#9be7ff"}
EMPTY = "#0b0f19"
# The tail, from the head back: white hot, yellow, orange, red, then embers.
FIRE = ["#fffbe8", "#fff1b0", "#ffd166", "#ffb347", "#ff9f1c", "#ff7a1a", "#ff5a1f", "#f2421b", "#d6301a", "#b8231a", "#8f1b1f", "#6b1626"]
MONTHS = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()


def grid(days):
    """A square for every day: a column per week, a row per weekday, Sunday on top."""
    first = datetime.date.fromisoformat(days[0]["date"])
    lead = (first.weekday() + 1) % 7
    for i, d in enumerate(days):
        col, row = divmod(i + lead, 7)
        d["col"], d["row"] = col, row
        d["x"], d["y"] = LEFT + col * STEP, TOP + row * STEP
        d["cx"], d["cy"] = d["x"] + CELL / 2, d["y"] + CELL / 2
    return days


def tour(days):
    """The squares to eat, in the order the comet reaches them: always the nearest one next."""
    left = [d for d in days if d["count"]]
    at, order = (LEFT - 3 * STEP + CELL / 2, TOP + 3 * STEP + CELL / 2), []
    while left:
        nxt = min(left, key=lambda d: (abs(d["cx"] - at[0]) + abs(d["cy"] - at[1]), d["col"], d["row"]))
        order.append(nxt)
        left.remove(nxt)
        at = (nxt["cx"], nxt["cy"])
    return order


def route(order):
    """A path that moves only along the grid, as in the old game of snake: across, then up or down, to each square."""
    start = (LEFT - 3 * STEP + CELL / 2, TOP + 3 * STEP + CELL / 2)
    points, eaten_at, length = [start], [], 0.0
    at = start
    for d in order:
        corner = (d["cx"], at[1])
        for p in (corner, (d["cx"], d["cy"])):
            if p != points[-1]:
                length += abs(p[0] - points[-1][0]) + abs(p[1] - points[-1][1])
                points.append(p)
        eaten_at.append(length)
        at = (d["cx"], d["cy"])
    # Then off the right edge, so the comet leaves the board before it starts again.
    for p in ((W + 3 * STEP, at[1]),):
        length += abs(p[0] - points[-1][0])
        points.append(p)
    path = "M" + " L".join("%.1f %.1f" % p for p in points)
    return path, eaten_at, length


def fire(k, pieces):
    """The colour of tail piece k of pieces."""
    return FIRE[min(len(FIRE) - 1, int(k * len(FIRE) / max(1, pieces)))]


def draw(days, user):
    days = grid(days)
    order = tour(days)
    path, eaten_at, length = route(order)
    total, lit = sum(d["count"] for d in days), len(order)
    longest, current = streaks(days)
    move = max(6.0, length / SPEED)          # seconds the crawl takes
    loop = move + 2.5                        # and a pause with the board full again before the next one
    gap = STEP / SPEED                       # how far a piece of the tail lags behind the one before it
    end = 100.0 * move / loop

    css = ["""
    text { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
    .m { fill: #5b6b88; font-size: 9px; letter-spacing: 1.4px; }
    .k { fill: #5b6b88; font-size: 9px; letter-spacing: 1.8px; }
    .v { fill: #f4f6fb; font-size: 15px; font-weight: 700; }
    .t { fill: #ffffff; font-size: 13px; font-weight: 700; letter-spacing: 3.4px; }
    .u { fill: #ff7a1a; font-size: 13px; font-weight: 700; letter-spacing: 3.4px; }
    .s { fill: #ff9f1c; font-size: 9px; letter-spacing: 2.2px; }
    .far { animation: drift 120s linear infinite; }
    .near { animation: drift 55s linear infinite; }
    @keyframes drift { to { transform: translateX(-%(w)dpx); } }
    .tw { animation: tw 3.8s ease-in-out infinite; }
    @keyframes tw { 0%%, 100%% { opacity: 1; } 50%% { opacity: 0.3; } }
    .cell { animation: pulse 3.2s ease-in-out infinite; }
    @keyframes pulse { 0%%, 100%% { opacity: 1; } 50%% { opacity: 0.72; } }
    .scan { animation: scan %(loop).2fs linear infinite; }
    @keyframes scan { 0%% { transform: translateY(0); } 100%% { transform: translateY(%(scan)dpx); } }
    .seg { offset-path: path('%(path)s'); offset-rotate: 0deg; animation: crawl %(loop).2fs linear infinite both; }
    @keyframes crawl { 0%% { offset-distance: 0%%; } %(end).2f%%, 100%% { offset-distance: 100%%; } }
    .blink { animation: blink 1.4s steps(2, start) infinite; }
    @keyframes blink { to { visibility: hidden; } }
    @media (prefers-reduced-motion: reduce) { * { animation: none !important; } .seg, .boom { display: none; } }
    """ % {"path": path, "loop": loop, "end": end, "w": W, "scan": H}]

    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-labelledby="t d">' % (W, H, W, H),
           '<title id="t">%s: a year of contributions swept up by a comet</title>' % user,
           '<desc id="d">%d contributions on %d days. A burning comet flies the contribution grid and swallows every lit square.</desc>' % (total, lit),
           '<defs><radialGradient id="bg" cx="0.72" cy="0.2" r="1"><stop offset="0" stop-color="#160a1c"/><stop offset="0.45" stop-color="#05060d"/><stop offset="1" stop-color="#000000"/></radialGradient>'
           '<radialGradient id="neb" r="0.5"><stop offset="0" stop-color="#ff5a1f" stop-opacity="0.16"/><stop offset="1" stop-color="#ff5a1f" stop-opacity="0"/></radialGradient>'
           '<radialGradient id="neb2" r="0.5"><stop offset="0" stop-color="#3a6bff" stop-opacity="0.14"/><stop offset="1" stop-color="#3a6bff" stop-opacity="0"/></radialGradient>'
           '<linearGradient id="beam" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ff9f1c" stop-opacity="0"/><stop offset="1" stop-color="#ff9f1c" stop-opacity="0.07"/></linearGradient>'
           '<filter id="glow" x="-100%%" y="-100%%" width="300%%" height="300%%"><feGaussianBlur stdDeviation="2.4" result="b"/>'
           '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
           '<clipPath id="card"><rect width="%d" height="%d" rx="12"/></clipPath></defs>' % (W, H),
           "STYLE", '<g clip-path="url(#card)"><rect width="%d" height="%d" fill="url(#bg)"/>' % (W, H),
           '<ellipse cx="%d" cy="30" rx="260" ry="90" fill="url(#neb)"/><ellipse cx="120" cy="%d" rx="220" ry="80" fill="url(#neb2)"/>' % (W - 170, H - 20)]

    # Deep space: two layers of stars drifting at different speeds, each drawn twice so the drift never shows a seam.
    sky = random.Random(1991)
    for cls, count, size in (("far", 120, 0.5), ("near", 40, 0.95)):
        stars = "".join('<circle class="tw" style="animation-delay:-%.1fs" cx="%.1f" cy="%.1f" r="%.2f" fill="#dfe8ff" opacity="%.2f"/>'
                        % (sky.uniform(0, 3.8), sky.uniform(0, W), sky.uniform(0, H), size * sky.uniform(0.6, 1.4), sky.uniform(0.2, 0.9)) for _ in range(count))
        out.append('<g class="%s"><g>%s</g><g transform="translate(%d 0)">%s</g></g>' % (cls, stars, W, stars))
    # Corner brackets, as on a targeting screen.
    for x, y, dx, dy in ((10, 10, 1, 1), (W - 10, 10, -1, 1), (10, H - 10, 1, -1), (W - 10, H - 10, -1, -1)):
        out.append('<path d="M%d %d V%d M%d %d H%d" stroke="#ff7a1a" stroke-opacity="0.55" stroke-width="1.2" fill="none"/>'
                   % (x, y + dy * 14, y, x, y, x + dx * 14))
    out.append('<rect class="scan" x="0" y="-40" width="%d" height="40" fill="url(#beam)"/>' % W)

    out.append('<text x="%d" y="30"><tspan class="t">%s</tspan><tspan class="u"> // </tspan><tspan class="t">COMET SWEEP</tspan></text>'
               '<text class="s" x="%d" y="30" text-anchor="end">TARGETS LOCKED<tspan class="blink"> ●</tspan></text>'
               % (LEFT, user.upper(), W - LEFT))
    seen = None
    for d in days:
        when = datetime.date.fromisoformat(d["date"])
        if when.day <= 7 and when.month != seen and d["row"] == 0:
            seen = when.month
            out.append('<text class="m" x="%d" y="%d">%s</text>' % (d["x"], TOP - 7, MONTHS[seen - 1]))

    # Every square. A lit one turns dark the moment the head reaches it, and lights again before the next crawl.
    eat = {id(d): eaten_at[i] for i, d in enumerate(order)}
    for d in days:
        if id(d) in eat:
            colour = CHARGE[max(1, d.get("level", 1))]
            t = 100.0 * (eat[id(d)] / length) * move / loop
            name = "e%d_%d" % (d["col"], d["row"])
            css.append("@keyframes %s { 0%%, %.2f%% { fill: %s; } %.2f%% { fill: #ffffff; } %.2f%%, %.2f%% { fill: %s; } 100%% { fill: %s; } }"
                       % (name, max(0.0, t - 0.01), colour, t + 0.2, t + 0.9, 99.0, EMPTY, colour))
            out.append('<rect x="%d" y="%d" width="%d" height="%d" rx="2" fill="%s" filter="url(#glow)" style="animation: %s %.2fs linear infinite"/>'
                       % (d["x"], d["y"], CELL, CELL, colour, name, loop))
            # The flash when it goes: a ring of fire that opens and fades.
            css.append("@keyframes b%s { 0%%, %.2f%% { transform: scale(0.2); opacity: 0; } %.2f%% { transform: scale(0.6); opacity: 1; } "
                       "%.2f%%, 100%% { transform: scale(2.8); opacity: 0; } }" % (name, max(0.0, t - 0.01), t + 0.2, t + 3.5))
            out.append('<circle class="boom" cx="%.1f" cy="%.1f" r="7" fill="none" stroke="#ffb347" stroke-width="1.6" '
                       'style="transform-box: fill-box; transform-origin: center; opacity: 0; animation: b%s %.2fs linear infinite"/>'
                       % (d["cx"], d["cy"], name, loop))
        else:
            out.append('<rect x="%d" y="%d" width="%d" height="%d" rx="2" fill="%s" stroke="#16203a" stroke-width="0.6"/>' % (d["x"], d["y"], CELL, CELL, EMPTY))

    # The comet: a white hot head and a tail of fire that follows it piece by piece, longer with every square.
    pieces = min(MOST, START + lit)
    for k in range(pieces, -1, -1):
        r = max(1.2, 6.2 - k * (5.0 / max(1, pieces)))
        shade = fire(k, pieces)
        fade = max(0.25, 1.0 - k / (pieces + 2.0))
        extra = ' filter="url(#glow)"'
        eyes = ""
        if k == 0:
            eyes = '<circle r="11" fill="#ff9f1c" opacity="0.22"/><circle r="3.2" fill="#ffffff"/>'
        grow = ""
        if k > START:  # this piece appears when the head eats square number k minus START
            when = (eaten_at[k - START - 1] / length) * move - k * gap * 0.55  # in the piece's own time, which lags the head
            at = 100.0 * max(0.0, when) / loop
            css.append("@keyframes g%d { 0%%, %.2f%% { opacity: 0; } %.2f%%, 100%% { opacity: 1; } }" % (k, at, min(99.9, at + 0.5)))
            grow = "; animation: crawl %.2fs linear infinite both, g%d %.2fs linear infinite both" % (loop, k, loop)
        out.append('<g class="seg" style="animation-delay: %.3fs%s"><circle r="%.1f" fill="%s" opacity="%.2f"%s/>%s</g>'
                   % (k * gap * 0.55, grow and grow + "; animation-delay: %.3fs" % (k * gap * 0.55), r, shade, fade, extra, eyes))

    y = TOP + 7 * STEP + 26
    facts = (("CONTRIBUTIONS", "{:,}".format(total)), ("TARGETS", str(lit)), ("LONGEST RUN", "%d d" % longest), ("CURRENT RUN", "%d d" % current))
    out.append('<text class="k" x="%d" y="%d" text-anchor="end">ONE YEAR  //  EVERY CELL A DAY I SHIPPED</text>' % (W - LEFT, y))
    for i, (k, v) in enumerate(facts):
        out.append('<text class="k" x="%d" y="%d">%s</text><text class="v" x="%d" y="%d">%s</text>' % (LEFT + i * 118, y, k, LEFT + i * 118, y + 19, v))
    out.append("</g></svg>")
    return "\n".join(out).replace("STYLE", "<style>%s</style>" % "\n    ".join(css))


def main():
    ap = argparse.ArgumentParser(description="A year of GitHub contributions swept up by a comet.")
    ap.add_argument("--user", help="the GitHub login to draw")
    ap.add_argument("--days", help="a saved calendar: JSON with user and days")
    ap.add_argument("--out", default="comet.svg")
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
    svg = draw(days, user)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(svg + "\n")
    print("%s: %d days, %d bytes" % (args.out, len(days), len(svg)))


if __name__ == "__main__":
    main()
