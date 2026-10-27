"""Render assets/activity.svg from the GitHub contribution calendar.

Runs in GitHub Actions (see .github/workflows/activity.yml). Needs GITHUB_TOKEN
and GITHUB_USER in the environment; writes the SVG to stdout.
"""
import datetime as dt
import json
import os
import random
import sys
import urllib.request

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""

W, H = 1000, 200
CHART = (340, 36, 960, 160)  # x0, y0, x1, y1


def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
    if "errors" in data:
        raise SystemExit(f"GraphQL error: {data['errors']}")
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    return cal["totalContributions"], cal["weeks"], days


def longest_streak(days):
    best = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] > 0 else 0
        best = max(best, run)
    return best


def smooth_path(pts, floor):
    """Catmull-Rom spline through pts as cubic Béziers, never dipping below floor."""
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0 = pts[max(i - 1, 0)]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, min(p1[1] + (p2[1] - p0[1]) / 6, floor))
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, min(p2[1] - (p3[1] - p1[1]) / 6, floor))
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d


def render(total, weeks, days):
    x0, y0, x1, y1 = CHART
    sums = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in weeks]
    peak = max(sums) or 1
    step = (x1 - x0) / max(len(sums) - 1, 1)
    pts = [(x0 + i * step, y1 - (s / peak) * (y1 - y0)) for i, s in enumerate(sums)]
    line = smooth_path(pts, y1)
    area = f"{line} L{x1},{y1} L{x0},{y1} Z"
    active = sum(1 for d in days if d["contributionCount"] > 0)
    streak = longest_streak(days)
    ex, ey = pts[-1]

    # Month labels: first week that starts in a new month, every second month
    labels, last_month = [], None
    for i, w in enumerate(weeks):
        month = dt.date.fromisoformat(w["contributionDays"][0]["date"]).month
        if month != last_month:
            if last_month is not None and month % 2 == 1:
                labels.append((x0 + i * step, dt.date(2000, month, 1).strftime("%b")))
            last_month = month

    rnd = random.Random(3)
    out = []
    w = out.append
    w(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
      f'aria-label="{total} contributions in the last year">')
    w("""<style>
  .label { font: 400 12px ui-monospace,'SFMono-Regular',Menlo,Consolas,monospace; fill:#94a3b8; }
  .big   { font: 700 44px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:#f1f5f9; }
  .num   { font: 600 18px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:#f1f5f9; }
  .month { font: 400 10px ui-monospace,'SFMono-Regular',Menlo,Consolas,monospace; fill:#64748b; }
  .in    { opacity:0; animation: up .9s ease-out forwards; }
  .line  { fill:none; stroke:#a5b4fc; stroke-width:2; stroke-linecap:round; stroke-dasharray:2000; stroke-dashoffset:2000; animation: draw 2.4s .3s ease-out forwards; }
  .area  { opacity:0; animation: fade 1.6s 1.2s ease-out forwards; }
  .grid  { stroke:#334155; stroke-width:.6; stroke-dasharray:2 4; }
  .star  { fill:#cbd5e1; animation: twinkle 4s ease-in-out infinite; }
  .glow  { animation: glow 3.5s ease-in-out infinite; transform-box: fill-box; transform-origin: center; }
  @keyframes up { from { opacity:0; transform: translateY(8px);} to { opacity:1; transform:none;} }
  @keyframes draw { to { stroke-dashoffset:0; } }
  @keyframes fade { to { opacity:1; } }
  @keyframes twinkle { 0%,100% { opacity:.12;} 50% { opacity:.7;} }
  @keyframes glow { 0%,100% { opacity:.5; transform: scale(.85);} 50% { opacity:1; transform: scale(1.15);} }
  @media (prefers-reduced-motion: reduce) {
    * { animation: none !important; } .in, .area { opacity:1; } .line { stroke-dashoffset:0; }
  }
</style>""")
    w(f"""<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#0b1020"/><stop offset="1" stop-color="#1b2540"/>
  </linearGradient>
  <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#818cf8" stop-opacity=".45"/><stop offset="1" stop-color="#818cf8" stop-opacity="0"/>
  </linearGradient>
  <radialGradient id="core" cx=".5" cy=".5" r=".5">
    <stop offset="0" stop-color="#ffffff" stop-opacity=".9"/>
    <stop offset=".3" stop-color="#c7d2fe" stop-opacity=".4"/>
    <stop offset="1" stop-color="#818cf8" stop-opacity="0"/>
  </radialGradient>
  <clipPath id="clip"><rect width="{W}" height="{H}" rx="14"/></clipPath>
  <path id="curve" d="{line}"/>
</defs>""")
    w('<g clip-path="url(#clip)">')
    w(f'<rect width="{W}" height="{H}" fill="url(#bg)"/>')
    for _ in range(30):
        w(f'<circle class="star" cx="{rnd.uniform(5, W - 5):.0f}" cy="{rnd.uniform(5, H - 5):.0f}" r="{rnd.choice([0.6, 0.8, 1.0])}" '
          f'style="animation-delay:-{rnd.uniform(0, 4):.1f}s;animation-duration:{rnd.uniform(3, 6):.1f}s"/>')

    # Numbers
    w('<text class="label in" x="40" y="48" style="animation-delay:.1s">CONTRIBUTIONS · LAST 12 MONTHS</text>')
    w(f'<text class="big in" x="38" y="100" style="animation-delay:.25s">{total:,}</text>')
    w('<text class="label in" x="40" y="140" style="animation-delay:.45s">ACTIVE DAYS</text>')
    w(f'<text class="num in" x="40" y="164" style="animation-delay:.55s">{active}</text>')
    w('<text class="label in" x="160" y="140" style="animation-delay:.65s">LONGEST STREAK</text>')
    w(f'<text class="num in" x="160" y="164" style="animation-delay:.75s">{streak} {"day" if streak == 1 else "days"}</text>')

    # Chart
    for gy in (y0, (y0 + y1) / 2, y1):
        w(f'<line class="grid" x1="{x0}" y1="{gy:.0f}" x2="{x1}" y2="{gy:.0f}"/>')
    w(f'<path class="area" d="{area}" fill="url(#fill)"/>')
    w(f'<path class="line" d="{line}"/>')
    for x, text in labels:
        w(f'<text class="month" x="{x:.0f}" y="{y1 + 20}" text-anchor="middle">{text}</text>')
    w(f'<circle class="glow" cx="{ex:.1f}" cy="{ey:.1f}" r="16" fill="url(#core)"/>')
    w(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="3" fill="#ffffff"/>')
    w('<circle r="1.8" fill="#c7d2fe" opacity="0">'
      '<animateMotion dur="6s" begin="2.7s" repeatCount="indefinite"><mpath href="#curve"/></animateMotion>'
      '<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.05;.9;1" dur="6s" begin="2.7s" repeatCount="indefinite"/>'
      '</circle>')
    w("</g>")
    w("</svg>")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    total, weeks, days = fetch(os.environ["GITHUB_USER"], os.environ["GITHUB_TOKEN"])
    sys.stdout.write(render(total, weeks, days))
