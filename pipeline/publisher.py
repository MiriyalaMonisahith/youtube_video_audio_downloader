"""
Publishing and Growth optimization module for YouTube Shorts.
Generates:
- High-CTR A/B title variants tuned for Shorts algorithm
- Shorts SEO descriptions with hashtags (#Shorts, #viral, topic tags)
- Best-time-to-post weekly schedule planner
- Performance & retention analytics projections
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
import random


VIRAL_TITLE_TEMPLATES = [
    # Curiosity Gap
    "{hook_phrase}... and nobody noticed 🤯",
    "Wait until the end of this... 😱",
    "The secret nobody talks about: {short_topic}",
    # Action / Proof
    "How this ACTUALLY works in 60s ⏱️",
    "Never make this mistake again 🚫",
    "This 1 trick changes everything for {short_topic} 🔥",
    # Contrarian / Shock
    "Stop doing this right now! 🛑",
    "Why 99% of people get this wrong ❌",
    "The truth about {short_topic} exposed ⚡"
]


def generate_shorts_metadata(
    clip_text: str,
    original_title: str,
    attribution_line: str,
    duration_sec: float
) -> Dict[str, Any]:
    """
    Generate A/B title variants, optimized descriptions, and search tags
    tailored specifically for YouTube Shorts retention and discovery.
    """
    clean_title = original_title.split("|")[0].split("-")[0].strip()
    words = clip_text.split()
    first_few = " ".join(words[:5]).capitalize() if words else "This Moment"
    
    # Generate 3 distinct A/B/C Title Variants
    titles = [
        f"{first_few}... 😱 #Shorts",
        f"The Truth About {clean_title[:35]} 🔥 #Shorts",
        f"Wait for the end of this! 🤯 #{clean_title.replace(' ', '')[:15]}"
    ]

    # Extract keywords for hashtags
    keywords = [w.strip(".,!?\"'()").capitalize() for w in words if len(w) > 4][:5]
    tags = ["#Shorts", "#ShortsFeed", "#Viral", "#Trending"] + [f"#{kw}" for kw in keywords if kw.isalnum()]
    
    description = (
        f"{first_few}...\n\n"
        f"Subscribe for more daily shorts! 🔔\n\n"
        f"{' '.join(tags[:8])}\n\n"
        f"--- Rights & Attribution ---\n"
        f"{attribution_line}\n"
    )

    return {
        "titles_ab": titles,
        "selected_title": titles[0],
        "description": description,
        "tags": tags,
        "duration_sec": duration_sec
    }


def generate_weekly_posting_schedule(clips: List[Dict[str, Any]], start_date: datetime = None) -> List[Dict[str, Any]]:
    """
    Distributes up to 10 generated shorts across peak YouTube Shorts posting windows:
    - 12:00 PM (Lunch break peak)
    - 5:30 PM (Evening commute peak)
    - 8:30 PM (Nighttime leisure peak)
    """
    if start_date is None:
        start_date = datetime.now()

    peak_hours = [12, 17, 20]
    peak_minutes = [0, 30, 15]

    schedule = []
    current_day = start_date + timedelta(days=1)
    slot_idx = 0

    for i, clip in enumerate(clips):
        hour = peak_hours[slot_idx % len(peak_hours)]
        minute = peak_minutes[slot_idx % len(peak_minutes)]
        
        post_time = current_day.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        schedule.append({
            "clip_id": clip.get("id", f"clip_{i+1}"),
            "title": clip.get("title", f"Short #{i+1}"),
            "virality_score": clip.get("virality_score", 85),
            "scheduled_datetime": post_time.strftime("%Y-%m-%d %H:%M"),
            "slot_label": f"Day {((i // 2) + 1)} - {post_time.strftime('%I:%M %p')}",
            "recommended_hook": clip.get("hook", "")
        })

        slot_idx += 1
        if slot_idx % 2 == 0:
            current_day += timedelta(days=1)

    return schedule
