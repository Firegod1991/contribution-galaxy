#!/usr/bin/env python3
"""Draw a year of GitHub contributions as the old game of snake: a glowing snake crawls the grid and eats
every square you lit, in the order it can reach them fastest, then leaves and starts over.

    python3 snake.py --user Firegod1991 --out snake.svg       # asks GitHub, needs GITHUB_TOKEN
    python3 snake.py --days sample.json --out snake.svg       # from a saved calendar

One animated SVG with no script in it, so it plays inside a README. Needs nothing but Python.
"""

import argparse
import datetime
import json
import os

from starchart import ask_github, streaks

STEP, CELL = 15, 11                 # distance from square to square, and the size of a square
LEFT, TOP = 40, 46                  # where the first square sits
W, H = LEFT * 2 + 53 * STEP, TOP + 7 * STEP + 52
SPEED = 260.0                       # pixels a second
START, MOST = 4, 22                 # pieces behind the head at the start, and at most: it grows with every square
GREEN = {0: "#161b22", 1: "#0e4429", 2: "#006d32", 3: "#26a641", 4: "#39d353"}
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
    """The squares to eat, in the order a hungry snake would reach them: always the nearest one next."""
    left = [d for d in days if d["count"]]
    at, order = (LEFT - 3 * STEP + CELL / 2, TOP + 3 * STEP + CELL / 2), []
    while left:
        nxt = min(left, key=lambda d: (abs(d["cx"] - at[0]) + abs(d["cy"] - at[1]), d["col"], d["row"]))
        order.append(nxt)
        left.remove(nxt)
        at = (nxt["cx"], nxt["cy"])
    return order


def route(order):
    """A path that moves only along the grid, as a snake does: across, then up or down, to each square."""
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
    # Then off the right edge, so the snake leaves the board before it starts again.
    for p in ((W + 3 * STEP, at[1]),):
        length += abs(p[0] - points[-1][0])
        points.append(p)
    path = "M" + " L".join("%.1f %.1f" % p for p in points)
    return path, eaten_at, length


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
    .m { fill: #7d8590; font-size: 9px; letter-spacing: 1.2px; }
    .k { fill: #7d8590; font-size: 9px; letter-spacing: 1.6px; }
    .v { fill: #e6edf3; font-size: 15px; font-weight: 700; }
    .t { fill: #e6edf3; font-size: 12px; font-weight: 700; letter-spacing: 2.6px; }
    .s { fill: #39d353; font-size: 9px; letter-spacing: 2px; }
    .seg { offset-path: path('%(path)s'); offset-rotate: 0deg; animation: crawl %(loop).2fs linear infinite both; }
    @keyframes crawl { 0%% { offset-distance: 0%%; } %(end).2f%%, 100%% { offset-distance: 100%%; } }
    .blink { animation: blink 1.4s steps(2, start) infinite; }
    @keyframes blink { to { visibility: hidden; } }
    @media (prefers-reduced-motion: reduce) { * { animation: none !important; } .seg { display: none; } }
    """ % {"path": path, "loop": loop, "end": end}]

    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-labelledby="t d">' % (W, H, W, H),
           '<title id="t">%s: a year of contributions eaten by a snake</title>' % user,
           '<desc id="d">%d contributions on %d days. A snake crawls the contribution grid and eats every lit square.</desc>' % (total, lit),
           '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0d1117"/><stop offset="1" stop-color="#070a10"/></linearGradient>'
           '<filter id="glow" x="-100%%" y="-100%%" width="300%%" height="300%%"><feGaussianBlur stdDeviation="2.4" result="b"/>'
           '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
           '<clipPath id="card"><rect width="%d" height="%d" rx="12"/></clipPath></defs>' % (W, H),
           "STYLE", '<g clip-path="url(#card)"><rect width="%d" height="%d" fill="url(#bg)"/>' % (W, H)]

    out.append('<text class="t" x="%d" y="22">%s</text><text class="s" x="%d" y="22" text-anchor="end">SNAKE<tspan class="blink"> ●</tspan></text>'
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
        colour = GREEN[d.get("level", 0) if d["count"] else 0]
        if id(d) in eat:
            t = 100.0 * (eat[id(d)] / length) * move / loop
            name = "e%d_%d" % (d["col"], d["row"])
            css.append("@keyframes %s { 0%%, %.2f%% { fill: %s; } %.2f%%, %.2f%% { fill: %s; } 100%% { fill: %s; } }"
                       % (name, max(0.0, t - 0.01), colour, t + 0.4, 99.0, GREEN[0], colour))
            out.append('<rect x="%d" y="%d" width="%d" height="%d" rx="2" fill="%s" style="animation: %s %.2fs linear infinite"/>'
                       % (d["x"], d["y"], CELL, CELL, colour, name, loop))
        else:
            out.append('<rect x="%d" y="%d" width="%d" height="%d" rx="2" fill="%s"/>' % (d["x"], d["y"], CELL, CELL, colour))

    # The snake: a head and a tail that follows it piece by piece. Every square it eats adds a piece.
    pieces = min(MOST, START + lit)
    for k in range(pieces, -1, -1):
        size = CELL - 1 - min(k, 14) * 0.3
        shade = "#a5f3fc" if k == 0 else ("#22d3ee" if k < 5 else ("#3b82f6" if k < 11 else "#6366f1"))
        extra = ' filter="url(#glow)"' if k < 3 else ""
        eyes = ""
        if k == 0:
            eyes = '<circle cx="2" cy="-2" r="1.1" fill="#0d1117"/><circle cx="2" cy="2" r="1.1" fill="#0d1117"/>'
        grow = ""
        if k > START:  # this piece appears when the head eats square number k minus START
            when = (eaten_at[k - START - 1] / length) * move - k * gap  # in the piece's own time, which lags the head
            at = 100.0 * max(0.0, when) / loop
            css.append("@keyframes g%d { 0%%, %.2f%% { opacity: 0; } %.2f%%, 100%% { opacity: 1; } }" % (k, at, min(99.9, at + 0.5)))
            grow = "; animation: crawl %.2fs linear infinite both, g%d %.2fs linear infinite both" % (loop, k, loop)
        out.append('<g class="seg" style="animation-delay: %.3fs%s"><rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f" fill="%s"%s/>%s</g>'
                   % (k * gap, grow and grow + "; animation-delay: %.3fs" % (k * gap), -size / 2, -size / 2, size, size, size / 2.6, shade, extra, eyes))

    y = TOP + 7 * STEP + 20
    facts = (("CONTRIBUTIONS", "{:,}".format(total)), ("DAYS SHIPPED", str(lit)), ("LONGEST RUN", "%d d" % longest), ("CURRENT RUN", "%d d" % current))
    for i, (k, v) in enumerate(facts):
        out.append('<text class="k" x="%d" y="%d">%s</text><text class="v" x="%d" y="%d">%s</text>' % (LEFT + i * 150, y, k, LEFT + i * 150, y + 19, v))
    out.append("</g></svg>")
    return "\n".join(out).replace("STYLE", "<style>%s</style>" % "\n    ".join(css))


def main():
    ap = argparse.ArgumentParser(description="A year of GitHub contributions eaten by a snake.")
    ap.add_argument("--user", help="the GitHub login to draw")
    ap.add_argument("--days", help="a saved calendar: JSON with user and days")
    ap.add_argument("--out", default="snake.svg")
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
