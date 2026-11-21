# Output shape

Start the comment with: **TeveBot Agent review** and one line stating the PR scope in your words.

For each finding, in this order of importance (numbers, then security, then scope):

- **Severity:** high | medium | low
- **File:** path:line
- **Problem:** what is wrong
- **Why it matters:** the consequence
- **Suggested fix:** one concrete change

## Quality gate
- Report only findings you are confident about. Do not pad.
- If there are no findings, say "No findings" and list what you checked.
- End with: "This review is advisory. Steve decides."
