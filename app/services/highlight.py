from typing import List, Dict
import math
import re
from rapidfuzz.fuzz import ratio as fuzz_ratio

EMOTION_WORDS = set([
    "amazing","incredible","shocking","unbelievable","crazy","insane","wow",
    "love","hate","fear","angry","sad","happy","excited","danger","warning",
    "critical","urgent","surprising","important","powerful","dramatic",
])

FILLER_PATTERNS = [
    r"\buh+\b", r"\bum+\b", r"\byou know\b", r"\blike\b", r"\bokay\b"
]

def _normalize(text: str) -> str:
    t = text.lower().strip()
    t = re.sub(r"\s+", " ", t)
    return t

def _tokenize(text: str) -> List[str]:
    return re.findall(r"[\w']+", text.lower())

def _emotion_intensity(text: str) -> float:
    t = text.strip()
    if not t:
        return 0.0

    score = 0.0
    score += 0.7 * min(3, t.count("!"))
    score += 0.4 * min(3, t.count("?"))

    caps_words = re.findall(r"\b[A-Z]{3,}\b", text)
    score += 0.5 * min(2, len(caps_words))

    toks = _tokenize(text)
    emo_hits = sum(1 for w in toks if w in EMOTION_WORDS)
    score += 0.6 * min(3, emo_hits)

    if re.search(r"\b(very|really|extremely|super)\b", text.lower()):
        score += 0.4

    return min(3.0, score)

def _sentence_weight(text: str) -> float:
    t = text.strip()
    if not t:
        return 0.0

    length = len(t)
    score = 0.0

    if re.search(r"\d", t):
        score += 0.8

    if re.search(r"\b(is|means|defined as|in other words)\b", t.lower()):
        score += 0.9

    if 45 <= length <= 180:
        score += 0.8
    elif 25 <= length < 45:
        score += 0.3
    elif length > 260:
        score -= 0.4

    for pat in FILLER_PATTERNS:
        if re.search(pat, t.lower()):
            score -= 0.2

    return max(-1.0, min(2.5, score))

def _topic_importance(text: str, global_keywords: set) -> float:
    toks = _tokenize(text)
    if not toks:
        return 0.0
    hits = sum(1 for w in toks if w in global_keywords)
    return min(3.0, hits * 0.35)

def _extract_global_keywords(segments: List[Dict], top_k: int = 40) -> set:
    freq = {}
    for s in segments:
        for w in _tokenize(s.get("text", "")):
            if len(w) < 3:
                continue
            freq[w] = freq.get(w, 0) + 1

    stop = set(["the","and","you","your","are","for","that","this","with","from","have","what","how"])
    items = [(w,c) for w,c in freq.items() if w not in stop]
    items.sort(key=lambda x: x[1], reverse=True)
    return set([w for w,_ in items[:top_k]])

def _repetition_penalty(text: str, selected_texts: List[str]) -> float:
    t = _normalize(text)
    if not t:
        return 0.0

    worst = 0.0
    for prev in selected_texts:
        sim = fuzz_ratio(t, prev) / 100.0
        worst = max(worst, sim)

    if worst >= 0.90:
        return 2.0
    if worst >= 0.80:
        return 1.2
    if worst >= 0.70:
        return 0.6
    return 0.0

def score_segments(segments: List[Dict]) -> List[Dict]:
    global_kw = _extract_global_keywords(segments)

    scored = []
    for s in segments:
        start, end = float(s["start"]), float(s["end"])
        dur = max(0.0, end - start)
        text = s.get("text", "").strip()
        if not text or dur <= 0:
            continue

        emo = _emotion_intensity(text)
        imp = _topic_importance(text, global_kw)
        wt  = _sentence_weight(text)

        dur_pref = 0.0
        if 4 <= dur <= 14:
            dur_pref = 0.7
        elif 2 <= dur < 4:
            dur_pref = 0.2
        elif dur > 20:
            dur_pref = -0.4

        total = (1.1 * imp) + (0.9 * wt) + (0.7 * emo) + dur_pref

        scored.append({
            "start": start,
            "end": end,
            "text": text,
            "score": float(total),
            "score_breakdown": {
                "topic_importance": float(imp),
                "sentence_weight": float(wt),
                "emotional_intensity": float(emo),
                "duration_pref": float(dur_pref),
            }
        })

    return scored

def select_highlights(
    segments: List[Dict],
    target_seconds: float = 300.0,
    min_segment_seconds: float = 3.0,
    max_segment_seconds: float = 16.0,
    merge_gap_seconds: float = 0.8,
    context_before: float = 0.6,
    context_after: float = 0.8,
    video_duration: float | None = None,
) -> List[Dict]:

    
    scored = score_segments(segments)

    cleaned = []
    for s in scored:
        dur = s["end"] - s["start"]
        if dur < min_segment_seconds:
            continue
        if dur > max_segment_seconds:
            s["end"] = s["start"] + max_segment_seconds
        cleaned.append(s)

    cleaned.sort(key=lambda x: x["score"], reverse=True)

    picked = []
    picked_texts = []  
    total = 0.0

    for s in cleaned:
        dur = s["end"] - s["start"]
        if total + dur > target_seconds:
            continue

        rep_pen = _repetition_penalty(s["text"], picked_texts)
        adjusted = s["score"] - rep_pen
        if adjusted < 0.6:  
            continue

        s["score_breakdown"]["repetition_penalty"] = float(rep_pen)
        s["score_adjusted"] = float(adjusted)

        picked.append(s)
        picked_texts.append(_normalize(s["text"]))
        total += dur

        if total >= target_seconds * 0.98:
            break

    picked.sort(key=lambda x: x["start"])
    
    for s in picked:
        s["start"] = max(0.0, float(s["start"]) - context_before)
        s["end"] = float(s["end"]) + context_after
        if video_duration is not None:
            s["end"] = min(float(video_duration), float(s["end"]))


    merged = []
    for s in picked:
        if not merged:
            merged.append(s)
            continue
        prev = merged[-1]
        if s["start"] - prev["end"] <= merge_gap_seconds:
            prev["end"] = max(prev["end"], s["end"])
            prev["text"] = (prev["text"] + " " + s["text"]).strip()
            prev["score_adjusted"] = max(prev.get("score_adjusted", prev["score"]), s.get("score_adjusted", s["score"]))
        else:
            merged.append(s)

    return merged
