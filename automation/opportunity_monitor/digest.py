"""Builds the plain-text body of the daily email digest."""


def build_digest_body(alerted_entries: list[dict]) -> str:
    if not alerted_entries:
        return "No opportunities scored 80 or above today."

    lines = []
    for entry in alerted_entries:
        # url is optional (.get, not entry['url']): not every source can
        # provide a direct link (e.g. a LinkedIn alert email body has no
        # extractable posting URL yet) — omit the line rather than error.
        url_line = f"  {entry['url']}\n" if entry.get("url") else ""
        lines.append(
            f"{entry['company']} — {entry['role']} "
            f"(score {entry['score']}, source: {entry['source']})\n"
            f"{url_line}"
            f"  {entry['score_reasoning']}\n"
        )
    return "\n".join(lines)
