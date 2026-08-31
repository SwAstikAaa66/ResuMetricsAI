import re


def _extract_resume_keywords(resume_text):
    if not resume_text:
        return []
    words = re.findall(r"[A-Za-z][A-Za-z+/#.-]{2,}", resume_text)
    keywords = [w.title() for w in words if w.lower() not in {
        "the", "and", "with", "for", "from", "that", "this", "into", "your", "have", "been",
        "were", "their", "there", "about", "over", "after", "before", "more", "most", "some",
        "using", "based", "including", "through", "across", "within", "years", "year", "work",
    }]
    unique = []
    seen = set()
    for word in keywords:
        if word.lower() not in seen and len(word) > 2:
            unique.append(word)
            seen.add(word.lower())
    return unique[:12]


def generate_followup_suggestions(question, resume_text=None, role=None):
    question = (question or "").strip()
    role = (role or "Professional").strip() or "Professional"
    resume_keywords = _extract_resume_keywords(resume_text)

    if not question:
        raise ValueError("Please provide a follow-up question.")

    if not resume_keywords:
        resume_keywords = ["communication", "problem-solving", "technical execution"]

    suggestions = [
        f"Frame your answer around measurable impact in {role} projects.",
        "Use the STAR structure: Situation, Task, Action, Result.",
        f"Tie your examples to skills like {', '.join(resume_keywords[:4])} and business impact.",
        "Prepare 2-3 concise stories that show ownership, collaboration, and outcomes.",
    ]

    if "sql" in question.lower():
        suggestions.insert(0, "Practice SQL questions that combine joins, window functions, and business interpretation.")
    if "backend" in question.lower() or "engineer" in question.lower():
        suggestions.insert(0, "Highlight reliability, scalability, and trade-off decisions in your architecture examples.")
    if "data" in question.lower() or "analyst" in question.lower():
        suggestions.insert(0, "Emphasize metrics, dashboards, and how your analysis changed decisions.")

    return {
        "status": "success",
        "question": question,
        "role": role,
        "summary": f"Tailored suggestions for {role} based on your resume and question.",
        "suggestions": suggestions[:5],
    }
