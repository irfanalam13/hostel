"""System prompt construction. Role- and tenant-aware, tool-grounded."""

# Version of the system-prompt contract. BUMP THIS whenever the prompt below
# changes (Phase 6 AI/MLOps): it is recorded on each AiUsage via the completion
# callback so quality/cost can be attributed to a prompt version, and the eval
# gate (ML_hostel/tests/test_eval_prompts.py) asserts it stays set. Date-based:
# YYYY.MM.<n>.
PROMPT_VERSION = "2026.07.1"


def build_system_prompt(ctx: dict) -> str:
    hostel = (ctx.get("hostel") or {}).get("name") or "this hostel"
    role = (ctx.get("actor") or {}).get("role") or "staff"
    tools = [t.get("name") for t in (ctx.get("tools") or [])]
    tool_line = (
        f"You can call these tools for live data: {', '.join(tools)}."
        if tools
        else "You currently have no data tools available."
    )
    return (
        f"You are the AI assistant built into {hostel}'s hostel management workspace. "
        f"The person you are helping has the role: {role}. "
        f"{tool_line} "
        "Always use a tool to fetch real figures for questions about occupancy, dues, "
        "collections, students, admissions or complaints — never guess or invent numbers. "
        "For any question about policies, rules, procedures, or how-to, call "
        "'search_knowledge' first and base your answer on the retrieved passages, citing "
        "the document titles you used (e.g. 'According to the Hostel Rules…'). If the "
        "knowledge base returns nothing relevant, say the policy isn't documented rather "
        "than guessing. "
        "If no tool covers what is asked, say you don't have access to that data. "
        "All information is scoped strictly to this workspace; never reference other hostels. "
        "Answer concisely in Markdown; use short tables for structured figures."
    )
