#!/usr/bin/env python3
"""Draw a year of GitHub contributions as a star chart: every day you shipped is a star, brighter the more
you did, and a ship flies the year from star to star in the order you lit them.

    python3 starchart.py --user Firegod1991 --out starchart.svg            # asks GitHub, needs GITHUB_TOKEN
    python3 starchart.py --days sample.json --out starchart.svg            # from a saved calendar

It writes one animated SVG with no script in it, so it plays inside a README. Needs nothing but Python.
"""

import argparse
import datetime
import json
import math
import os
import random
import urllib.request

W, H = 880, 268          # the picture
LEFT, TOP, STEP = 69, 78, 14   # the chart: where the first day sits, and the distance from day to day
LOOP = 22.0              # seconds for one whole flight, the pause at the end included
FLY = 15.0               # seconds of it spent flying
MONTHS = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()
STAR = {1: ("#8ec5ff", 2.1), 2: ("#bfe0ff", 2.7), 3: ("#ffe9a8", 3.3), 4: ("#ffb454", 4.0)}  # colour and size by level

QUERY = """query($login: String!) { user(login: $login) { contributionsCollection { contributionCalendar {
  totalContributions weeks { contributionDays { date contributionCount contributionLevel } } } } } }"""
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


def ask_github(user, token):
    """The public contribution calendar of a user, as a list of days."""
    body = json.dumps({"query": QUERY, "variables": {"login": user}}).encode()
    request = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": "bearer " + token, "Content-Type": "application/json", "User-Agent": "starchart"})
    with urllib.request.urlopen(request, timeout=60) as answer:
        data = json.load(answer)
    if data.get("errors") or not (data.get("data") or {}).get("user"):
        raise SystemExit("GitHub did not answer with a calendar: %s" % str(data.get("errors") or data)[:300])
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [{"date": d["date"], "count": d["contributionCount"], "level": LEVELS.get(d["contributionLevel"], 0)}
            for w in weeks for d in w["contributionDays"]]


def place(days):
    """Give every day its spot on the chart: a column per week, a row per weekday, Sunday on top."""
    first = datetime.date.fromisoformat(days[0]["date"])
    lead = (first.weekday() + 1) % 7  # days of the first week that fall before the chart begins
    for i, day in enumerate(days):
        col, row = divmod(i + lead, 7)
        day["x"], day["y"] = LEFT + col * STEP, TOP + row * STEP
        day["when"] = datetime.date.fromisoformat(day["date"])
    return days


def streaks(days):
    """The longest run of days with something shipped, and the run that reaches today (or yesterday)."""
    longest = run = 0
    for day in days:
        run = run + 1 if day["count"] else 0
        longest = max(longest, run)
    current = 0
    tail = days[:-1] if not days[-1]["count"] else days  # a day that has only begun does not break a run
    for day in reversed(tail):
        if not day["count"]:
            break
        current += 1
    return longest, current


def route(stops):
    """A smooth line through the stops in order, and how far along it each stop lies (0 to 1)."""
    if len(stops) < 2:
        return "", [0.0 for _ in stops]
    path, lengths, total = "M%.1f %.1f" % stops[0], [0.0], 0.0
    for (x0, y0), (x1, y1) in zip(stops, stops[1:]):
        span = math.hypot(x1 - x0, y1 - y0)
        lift = min(26.0, span * 0.22) * (-1 if (x0 + x1) % (2 * STEP) < STEP else 1)  # each leg bows a little, alternately
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2 + lift
        path += " Q%.1f %.1f %.1f %.1f" % (mx, my, x1, y1)
        steps, px, py, leg = 24, x0, y0, 0.0
        for s in range(1, steps + 1):  # the length of the curve, measured in short straight pieces
            t = s / steps
            qx = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * mx + t ** 2 * x1
            qy = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * my + t ** 2 * y1
            leg += math.hypot(qx - px, qy - py)
            px, py = qx, qy
        total += leg
        lengths.append(total)
    return path, [length / total for length in lengths]


def draw(days, user):
    days = place(days)
    lit = [d for d in days if d["count"]]
    total, best = sum(d["count"] for d in days), max(days, key=lambda d: d["count"])
    longest, current = streaks(days)
    today = days[-1]
    dust = random.Random(len(days) * 7919 + total)  # the same sky for the same year, a new one as the year moves

    # The flight: from the edge of the chart, through every lit day in order, and on to today.
    stops = [(LEFT - 34.0, TOP + 3 * STEP)] + [(float(d["x"]), float(d["y"])) for d in lit]
    if not lit or lit[-1] is not today:
        stops.append((float(today["x"]), float(today["y"])))
    path, along = route(stops)
    fly = 100.0 * FLY / LOOP  # the part of the loop spent flying, in percent

    css = ["""
    text { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; }
    .dim { fill: #5d7399; font-size: 9px; letter-spacing: 1.2px; }
    .label { fill: #6f88b3; font-size: 9px; letter-spacing: 1.6px; }
    .value { fill: #e8f1ff; font-size: 17px; font-weight: 700; letter-spacing: 0.5px; }
    .name { fill: #e8f1ff; font-size: 13px; font-weight: 700; letter-spacing: 2.4px; }
    .tag { fill: #39d0ff; font-size: 9px; letter-spacing: 2px; }
    .day { fill: #8fa6cf; opacity: 0.38; }
    .plus { fill: #ffe9a8; font-size: 9px; font-weight: 700; letter-spacing: 0.4px; opacity: 0; }
    .far { animation: drift 90s linear infinite; }
    .near { animation: drift 46s linear infinite; }
    .twinkle { animation: twinkle 4.6s ease-in-out infinite; }
    .sweep { animation: sweep %(loop)ss linear infinite; }
    .trail { fill: none; stroke: #39d0ff; stroke-width: 1.4; stroke-linecap: round; stroke-dasharray: 1; stroke-dashoffset: 1;
             animation: trail %(loop)ss linear infinite; }
    .ship { animation: ship %(loop)ss linear infinite; }
    .here { transform-box: fill-box; transform-origin: center; animation: here 2.4s ease-out infinite; }
    .blink { animation: blink 1.6s steps(2, start) infinite; }
    @keyframes drift { from { transform: translateX(0); } to { transform: translateX(-%(w)spx); } }
    @keyframes twinkle { 0%%, 100%% { opacity: 1; } 50%% { opacity: 0.55; } }
    @keyframes sweep { 0%% { transform: translateX(0); opacity: 0; } 4%% { opacity: 0.9; } %(fly).2f%% { transform: translateX(%(span)spx); opacity: 0.9; }
                       %(flyend).2f%%, 100%% { transform: translateX(%(span)spx); opacity: 0; } }
    @keyframes trail { 0%% { stroke-dashoffset: 1; opacity: 1; } %(fly).2f%% { stroke-dashoffset: 0; opacity: 1; }
                       92%% { stroke-dashoffset: 0; opacity: 1; } 99%%, 100%% { stroke-dashoffset: 0; opacity: 0; } }
    @keyframes ship { 0%% { offset-distance: 0%%; opacity: 0; } 1.5%% { opacity: 1; } %(fly).2f%% { offset-distance: 100%%; opacity: 1; }
                      92%% { offset-distance: 100%%; opacity: 1; } 99%%, 100%% { offset-distance: 100%%; opacity: 0; } }
    @keyframes here { 0%% { transform: scale(0.5); opacity: 0.9; } 100%% { transform: scale(2.6); opacity: 0; } }
    @keyframes blink { to { visibility: hidden; } }
    @media (prefers-reduced-motion: reduce) { * { animation: none !important; } .trail { stroke-dashoffset: 0; } .ship, .sweep { opacity: 0; } }
    """ % {"loop": LOOP, "w": W, "fly": fly, "flyend": fly + 3, "span": 53 * STEP + 20}]

    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-labelledby="t d">' % (W, H, W, H),
           '<title id="t">%s: a year of contributions as a star chart</title>' % user,
           '<desc id="d">%d contributions on %d days in the last year. Every day with a contribution is a star, and a ship flies '
           'from star to star in the order they were made.</desc>' % (total, len(lit)),
           "<defs>",
           '<linearGradient id="space" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0b1026"/><stop offset="0.55" stop-color="#070a18"/>'
           '<stop offset="1" stop-color="#03040a"/></linearGradient>',
           '<radialGradient id="nebula" cx="0.82" cy="0.1" r="0.7"><stop offset="0" stop-color="#3b2a7a" stop-opacity="0.55"/>'
           '<stop offset="0.45" stop-color="#16306b" stop-opacity="0.22"/><stop offset="1" stop-color="#070a18" stop-opacity="0"/></radialGradient>',
           '<radialGradient id="planet" cx="0.35" cy="0.3" r="0.8"><stop offset="0" stop-color="#2f6fb5"/><stop offset="0.6" stop-color="#173a6e"/>'
           '<stop offset="1" stop-color="#0a1730"/></radialGradient>',
           '<linearGradient id="beam" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#39d0ff" stop-opacity="0"/>'
           '<stop offset="1" stop-color="#39d0ff" stop-opacity="0.55"/></linearGradient>',
           '<filter id="glow" x="-300%" y="-300%" width="700%" height="700%"><feGaussianBlur stdDeviation="2.6" result="b"/>'
           '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
           '<filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="1.2"/></filter>',
           '<clipPath id="card"><rect width="%d" height="%d" rx="14"/></clipPath>' % (W, H),
           "</defs>", "STYLE", '<g clip-path="url(#card)">',
           '<rect width="%d" height="%d" fill="url(#space)"/><rect width="%d" height="%d" fill="url(#nebula)"/>' % (W, H, W, H)]

    # Two layers of far stars that drift at different speeds. Each is drawn twice so the drift never shows a seam.
    for cls, count, size in (("far", 90, 0.55), ("near", 34, 0.95)):
        stars = "".join('<circle cx="%.1f" cy="%.1f" r="%.2f" fill="#cfe0ff" opacity="%.2f"/>'
                        % (dust.uniform(0, W), dust.uniform(0, H), size * dust.uniform(0.6, 1.3), dust.uniform(0.25, 0.85)) for _ in range(count))
        out.append('<g class="%s">%s<g transform="translate(%d 0)">%s</g></g>' % (cls, stars, W, stars))
    out.append('<circle cx="%d" cy="%d" r="120" fill="url(#planet)" opacity="0.9"/><ellipse cx="%d" cy="%d" rx="178" ry="20" fill="none" '
               'stroke="#6aa8e8" stroke-opacity="0.28" stroke-width="1.2" transform="rotate(-16 %d %d)"/>' % (W - 30, H + 62, W - 30, H + 62, W - 30, H + 62))

    # The chart: a faint point for every day, the months along the top.
    out.append('<text x="%d" y="30" class="name">%s</text><text x="%d" y="45" class="tag">FLIGHT LOG  //  ONE YEAR  //  EVERY STAR IS A DAY I SHIPPED</text>'
               % (LEFT - 34, user.upper(), LEFT - 34))
    seen = None
    for day in days:
        if day["when"].day <= 7 and day["when"].month != seen and day["y"] == TOP:
            seen = day["when"].month
            out.append('<text x="%d" y="%d" class="dim">%s</text>' % (day["x"] - 3, TOP - 12, MONTHS[seen - 1]))
    out.append("".join('<circle class="day" cx="%d" cy="%d" r="1.25"/>' % (d["x"], d["y"]) for d in days if not d["count"]))
    out.append('<rect class="sweep" x="%d" y="%d" width="26" height="%d" fill="url(#beam)"/>' % (LEFT - 30, TOP - 7, 6 * STEP + 14))

    # The flight path, the stars it lights, and the ship.
    if path:
        out.append('<path class="trail" pathLength="1" d="%s" filter="url(#soft)" opacity="0.9"/><path class="trail" pathLength="1" d="%s"/>' % (path, path))
    order = {id(d): i + 1 for i, d in enumerate(lit)}
    for d in lit:
        colour, size = STAR[max(1, d["level"])]
        at = along[order[id(d)]] * fly  # when the ship arrives, in percent of the loop
        name = "s%d" % order[id(d)]
        css.append("@keyframes %s { 0%%, %.2f%% { opacity: 0.28; transform: scale(0.7); } %.2f%% { opacity: 1; transform: scale(2.1); } "
                   "%.2f%%, 92%% { opacity: 1; transform: scale(1); } 99%%, 100%% { opacity: 0.28; transform: scale(0.7); } }"
                   % (name, max(0.0, at - 0.6), at + 0.9, at + 3.2))
        css.append(".%s { transform-box: fill-box; transform-origin: center; animation: %s %ss linear infinite; }" % (name, name, LOOP))
        flare = ""
        if d["level"] >= 3:  # the big days throw a cross of light, as a bright star does through a lens
            reach = size * 2.6
            flare = ('<path d="M%.1f %d H%.1f M%d %.1f V%.1f" stroke="%s" stroke-width="0.8" stroke-linecap="round" opacity="0.75"/>'
                     % (d["x"] - reach, d["y"], d["x"] + reach, d["x"], d["y"] - reach, d["y"] + reach, colour))
        out.append('<g class="%s">%s<circle cx="%d" cy="%d" r="%.1f" fill="%s" filter="url(#glow)"/><circle class="twinkle" style="animation-delay:-%.1fs" '
                   'cx="%d" cy="%d" r="%.1f" fill="#ffffff"/></g>' % (name, flare, d["x"], d["y"], size, colour, dust.uniform(0, 4.6), d["x"], d["y"], size * 0.42))
        # What the day was worth rises off the star as the ship arrives, to the left and to the right by turns so neighbours do not collide.
        side = -1 if order[id(d)] % 2 else 1
        css.append("@keyframes p%s { 0%%, %.2f%% { opacity: 0; transform: translateY(4px); } %.2f%% { opacity: 1; transform: translateY(-3px); } "
                   "%.2f%% { opacity: 1; transform: translateY(-7px); } %.2f%%, 100%% { opacity: 0; transform: translateY(-12px); } }"
                   % (name, max(0.0, at - 0.4), at + 1.2, at + 6.0, at + 8.5))
        css.append(".p%s { animation: p%s %ss linear infinite; }" % (name, name, LOOP))
        out.append('<text class="plus p%s" x="%d" y="%d" text-anchor="%s">+%d</text>'
                   % (name, d["x"] + side * 8, d["y"] - 5, "end" if side < 0 else "start", d["count"]))
    out.append('<circle class="here" cx="%d" cy="%d" r="5" fill="none" stroke="#ff7a59" stroke-width="1.2"/>' % (today["x"], today["y"]))
    if path:
        out.append('<g class="ship" style="offset-path: path(\'%s\'); offset-rotate: auto;"><path class="blink" d="M-4 0 L-17 0" stroke="#ffb454" '
                   'stroke-width="2.2" stroke-linecap="round" opacity="0.9"/><path d="M-3 0 L-13 0" stroke="#39d0ff" stroke-width="2.6" stroke-linecap="round"/>'
                   '<path d="M11 0 L-7 -5.4 L-3.4 0 L-7 5.4 Z" fill="#f4fbff" filter="url(#glow)"/></g>' % path)

    # The readout along the bottom.
    y = TOP + 6 * STEP + 44
    facts = (("CONTRIBUTIONS", "{:,}".format(total)), ("DAYS SHIPPED", str(len(lit))), ("BEST DAY", str(best["count"])),
             ("LONGEST RUN", "%d d" % longest), ("CURRENT RUN", "%d d" % current))
    for i, (label, value) in enumerate(facts):
        x = LEFT - 34 + i * 128
        out.append('<text x="%d" y="%d" class="label">%s</text><text x="%d" y="%d" class="value">%s</text>' % (x, y, label, x, y + 22, value))
    out.append('<text x="%d" y="%d" class="tag" text-anchor="end">TRACKING<tspan class="blink"> ●</tspan></text>' % (W - 190, 30))
    out.append("</g></svg>")
    return "\n".join(out).replace("STYLE", "<style>%s</style>" % "\n    ".join(css))


def main():
    ap = argparse.ArgumentParser(description="A year of GitHub contributions as a star chart.")
    ap.add_argument("--user", help="the GitHub login to draw")
    ap.add_argument("--days", help="a saved calendar to draw instead of asking GitHub: JSON with user and days")
    ap.add_argument("--out", default="starchart.svg")
    args = ap.parse_args()
    if args.days:
        with open(args.days, encoding="utf-8") as f:
            saved = json.load(f)
        user, days = args.user or saved["user"], saved["days"]
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
