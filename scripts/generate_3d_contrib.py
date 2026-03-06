"""Generate a 3D contribution graph (SVG) for a GitHub account.

This script is intended to be run as part of a GitHub Actions workflow that
provides a `GITHUB_TOKEN`. It fetches the authenticated user's contribution
calendar via the GitHub GraphQL API and renders it as a 3D bar chart.

The generated SVG is written to `profile-3d-contrib/profile-night-rainbow.svg`.
"""

import os
import sys
import requests
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT_PATH = "profile-3d-contrib/profile-night-rainbow.svg"


def query_contributions(login: str) -> dict:
    url = "https://api.github.com/graphql"
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN environment variable is required")

    headers = {"Authorization": f"Bearer {token}"}
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
                weekday
              }
            }
          }
        }
      }
    }
    """
    variables = {"login": login}

    r = requests.post(url, json={"query": query, "variables": variables}, headers=headers)
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise SystemExit(f"GraphQL error: {data['errors']}")
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def render_3d(contrib: dict, output_path: str) -> None:
    weeks = contrib.get("weeks", [])
    if not weeks:
        raise SystemExit("No contribution data found")

    # Build a 2D grid of contribution counts (weeks x weekdays)
    counts = np.zeros((len(weeks), 7), dtype=int)
    for wi, week in enumerate(weeks):
        for day in week.get("contributionDays", []):
            weekday = day.get("weekday", 0)
            counts[wi, weekday] = day.get("contributionCount", 0)

    # Create 3D bar chart
    fig = plt.figure(figsize=(12, 6))
    ax = fig.add_subplot(111, projection="3d")

    x, y = np.meshgrid(np.arange(counts.shape[0]), np.arange(counts.shape[1]), indexing="ij")
    x = x.flatten()
    y = y.flatten()
    z = np.zeros_like(x)

    dx = dy = 0.8
    dz = counts.flatten().astype(float)

    norm = plt.Normalize(vmin=dz.min(), vmax=dz.max() if dz.max() > 0 else 1)
    colors = plt.cm.winter(norm(dz))

    ax.bar3d(x, y, z, dx, dy, dz, color=colors, shade=True)

    ax.set_xlabel("Week")
    ax.set_ylabel("Weekday")
    ax.set_zlabel("Contributions")

    ax.set_yticks(range(7))
    ax.set_yticklabels(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])

    ax.set_title("GitHub Contributions (3D)")
    plt.tight_layout()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, format="svg")
    print(f"Generated {output_path}")


def main() -> None:
    login = os.environ.get("GITHUB_ACTOR") or os.environ.get("GITHUB_REPOSITORY_OWNER")
    if not login:
        # Fallback: try to parse from repository name
        repo = os.environ.get("GITHUB_REPOSITORY")
        if repo and "/" in repo:
            login = repo.split("/")[0]

    if not login:
        raise SystemExit("Unable to determine GitHub login; set GITHUB_ACTOR or GITHUB_REPOSITORY_OWNER")

    contrib = query_contributions(login)
    render_3d(contrib, OUT_PATH)


if __name__ == "__main__":
    main()
