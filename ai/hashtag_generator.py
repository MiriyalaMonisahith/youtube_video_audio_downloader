"""
AI Hashtag Generator for YouTube Shorts.
Generates high-traffic, algorithm-optimized hashtag sets
by combining macro-viral reach tags with niche content-specific tags.
"""

import re
from typing import List, Dict
from ai.llm_client import generate_ai_text

NICHE_TAGS: Dict[str, List[str]] = {
    "tech": ["#tech", "#technology", "#ai", "#innovation", "#coding", "#software", "#futuretech"],
    "finance": ["#money", "#wealth", "#investing", "#business", "#finance", "#crypto", "#passiveincome"],
    "motivation": ["#motivation", "#mindset", "#discipline", "#success", "#growth", "#productivity", "#mindsetshift"],
    "fitness": ["#fitness", "#gym", "#workout", "#health", "#bodybuilding", "#nutrition", "#gains"],
    "gaming": ["#gaming", "#gamer", "#gameplay", "#videogames", "#twitch", "#gamershorts"],
    "education": ["#learn", "#didyouknow", "#education", "#facts", "#history", "#science", "#knowledge"],
    "comedy": ["#comedy", "#funny", "#relatable", "#humor", "#jokes", "#lol", "#hilarious"]
}

CORE_VIRAL_TAGS = ["#Shorts", "#Viral", "#ShortsFeed", "#Trending", "#FYP"]


def detect_niche(text: str) -> str:
    """Classifies content into the most probable viral niche."""
    t = text.lower()
    scores = {
        "tech": len(re.findall(r"\b(code|computer|ai|software|phone|app|tech|internet|robot|data)\b", t)),
        "finance": len(re.findall(r"\b(money|dollar|\$|cash|million|invest|rich|wealth|crypto|stock|income)\b", t)),
        "motivation": len(re.findall(r"\b(mindset|success|fail|goal|discipline|hustle|focus|habit|life|work)\b", t)),
        "fitness": len(re.findall(r"\b(gym|workout|muscle|diet|weight|exercise|health|fit|train|body)\b", t)),
        "gaming": len(re.findall(r"\b(game|play|fps|stream|boss|level|kill|controller|mod|console)\b", t)),
        "education": len(re.findall(r"\b(why|learn|fact|science|history|study|brain|human|discover)\b", t)),
        "comedy": len(re.findall(r"\b(funny|laugh|joke|crazy|insane|wild|prank|hilarious)\b", t))
    }
    best_niche = max(scores, key=scores.get)
    return best_niche if scores[best_niche] > 0 else "general"


def generate_hashtag_list(text: str, max_tags: int = 10) -> List[str]:
    """
    Generates a structured list of hashtags combining viral staples and niche keywords.
    """
    # 1. Try LLM generation
    prompt = f"""
Generate 10 viral YouTube Shorts hashtags for this transcript.
Rules:
- Include #Shorts and #Viral
- Include 8 content-specific hashtags
- Format: #tag1 #tag2 #tag3 on one line

Transcript:
"{text[:350]}"
"""
    system_prompt = "You are a YouTube Shorts SEO specialist. Output ONLY space-separated hashtags."

    ai_output = generate_ai_text(prompt, system=system_prompt, temperature=0.5, timeout=4)
    if ai_output:
        raw_tags = re.findall(r"#\w+", ai_output)
        if len(raw_tags) >= 5:
            # Capitalize standard format
            seen = set()
            clean_tags = []
            for t in raw_tags:
                clean_t = t.strip()
                if clean_t.lower() not in seen and len(clean_t) > 2:
                    seen.add(clean_t.lower())
                    clean_tags.append(clean_t)
            return clean_tags[:max_tags]

    # 2. Intelligent NLP Categorization Fallback
    niche = detect_niche(text)
    niche_specific = NICHE_TAGS.get(niche, ["#viralvideo", "#foryou", "#creators"])

    # Extract high-salience words from text
    words = re.findall(r"\b[A-Za-z]{4,15}\b", text.lower())
    stop_words = {"this", "that", "with", "from", "have", "were", "they", "will", "what", "when", "there", "about"}
    salient = [w for w in words if w not in stop_words]
    
    content_tags = []
    seen = set(t.lower() for t in CORE_VIRAL_TAGS)
    for w in salient:
        tag = f"#{w.capitalize()}"
        if tag.lower() not in seen:
            seen.add(tag.lower())
            content_tags.append(tag)
        if len(content_tags) >= 4:
            break

    combined = CORE_VIRAL_TAGS + niche_specific[:3] + content_tags
    return combined[:max_tags]


def generate_hashtags(text: str) -> str:
    """
    Generates space-delimited hashtag string.
    Maintains 100% backwards compatibility with legacy callers.
    """
    tags = generate_hashtag_list(text)
    return " ".join(tags)
