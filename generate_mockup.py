#!/usr/bin/env python3
"""
generate_mockup.py — Generates a sample HTML digest with dummy data for UI testing.
"""

import os
from src.render import render_email

def main():
    dummy_articles = [
        {
            "title": "Anthropic's C.E.O. Says It Could Grow by 80 Times This Year",
            "url": "https://example.com",
            "source_label": "New York Times (Technology)",
            "ai_topic": "ai_coding",
            "is_nyt": True,
            "tldr_summary": "Anthropic's CEO says the company could grow 80x this year, but there's a catch: they're now compute-constrained and desperately need more GPUs. Growth and bottlenecks, simultaneously.",
            "feedback_up_url": "#",
            "feedback_down_url": "#"
        },
        {
            "title": "Japan's SoftBank explores homegrown AI servers with Nvidia, Foxconn, Nikkei reports",
            "url": "https://example.com",
            "source_label": "Reuters",
            "ai_topic": "ai_coding",
            "is_nyt": False,
            "tldr_summary": "SoftBank is exploring homegrown AI server manufacturing with Nvidia and Foxconn, aiming to build Japan-made alternatives. The chip supply chain is finally getting geopolitically diversified.",
            "feedback_up_url": "#",
            "feedback_down_url": "#"
        },
        {
            "is_xkcd": True,
            "title": "Machine Learning",
            "url": "https://xkcd.com/1838/",
            "image_url": "https://imgs.xkcd.com/comics/machine_learning.png",
            "xkcd_alt": "The pile gets soaked with data and starts to get mushy over time, so it's technically a recurrent neural net."
        },
        {
            "is_podcast": True,
            "title": "The AI Revolution",
            "podcast_name": "Tech Daily",
            "podcast_duration": "45 min",
            "url": "https://example.com/podcast",
            "tldr_summary": "An in-depth look at how AI is reshaping the tech landscape."
        }
    ]

    html, _ = render_email(dummy_articles)

    output_path = "mockup.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
        
    print(f"✅ Mockup generated at {output_path}")

if __name__ == "__main__":
    main()
