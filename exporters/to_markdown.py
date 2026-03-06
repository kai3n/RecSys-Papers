"""
Export papers to a Markdown file.
"""

from datetime import datetime
from typing import List, Dict


def export(papers: List[Dict], output_path: str) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    venue_order = ["RecSys", "KDD", "WWW", "SIGIR", "arXiv"]

    # Group by venue
    grouped: dict = {}
    for p in papers:
        v = p.get("venue", "Other")
        grouped.setdefault(v, []).append(p)

    lines = [
        "# CTR/CVR Recommender System Papers",
        f"\n> Generated: {now} | Total: {len(papers)} papers\n",
        "---\n",
    ]

    # Table of contents
    lines.append("## Table of Contents\n")
    for venue in venue_order:
        if venue in grouped:
            count = len(grouped[venue])
            anchor = venue.lower().replace("/", "").replace(" ", "-")
            lines.append(f"- [{venue}](#{anchor}) ({count} papers)")
    other_venues = [v for v in grouped if v not in venue_order]
    for venue in sorted(other_venues):
        count = len(grouped[venue])
        anchor = venue.lower().replace("/", "").replace(" ", "-")
        lines.append(f"- [{venue}](#{anchor}) ({count} papers)")
    lines.append("")

    # Papers by venue
    def render_venue(venue_name, venue_papers):
        anchor = venue_name.lower().replace("/", "").replace(" ", "-")
        section = [f"---\n", f"## {venue_name}\n"]
        # Group by year within venue
        by_year: dict = {}
        for p in venue_papers:
            y = p.get("year") or "N/A"
            by_year.setdefault(y, []).append(p)

        for year in sorted(by_year.keys(), reverse=True):
            section.append(f"### {year}\n")
            for i, p in enumerate(by_year[year], 1):
                title = p.get("title", "N/A")
                url = p.get("url", "")
                authors = p.get("authors", [])
                abstract = p.get("abstract", "")
                score = p.get("score", 0)

                author_str = ", ".join(authors[:5])
                if len(authors) > 5:
                    author_str += f" et al. ({len(authors)} authors)"

                if url:
                    section.append(f"**{i}. [{title}]({url})**")
                else:
                    section.append(f"**{i}. {title}**")

                section.append(f"*{author_str}*  ")
                section.append(f"Score: {score}")

                if abstract:
                    truncated = abstract[:400] + "..." if len(abstract) > 400 else abstract
                    section.append(f"\n> {truncated}\n")
                else:
                    section.append("")
        return section

    for venue in venue_order:
        if venue in grouped:
            lines.extend(render_venue(venue, grouped[venue]))

    for venue in sorted(other_venues):
        lines.extend(render_venue(venue, grouped[venue]))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Markdown saved: {output_path} ({len(papers)} papers)")
