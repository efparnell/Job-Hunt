"""Builds the plain-text body of the daily email digest."""


def build_digest_body(alerted_entries: list[dict]) -> str:
    if not alerted_entries:
        return "No opportunities scored 80 or above today."

    lines = []
    for entry in alerted_entries:
        lines.append(
            f"{entry['company']} — {entry['role']} "
            f"(score {entry['score']}, source: {entry['source']})\n"
            f"  {entry['score_reasoning']}\n"
        )
    return "\n".join(lines)
