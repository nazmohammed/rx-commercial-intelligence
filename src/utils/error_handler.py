"""Graceful error handling — convert exceptions to user-friendly messages."""


def friendly_error(error: Exception) -> str:
    """Map common errors to messages safe to show end-users in Teams."""

    msg = str(error).lower()

    if "auth" in msg or "token" in msg or "401" in msg:
        return "Authentication issue with Power BI. The Cx Insights team has been notified."

    if "timeout" in msg:
        return "The query took too long. Try narrowing the date range or asking about fewer routes."

    if "429" in msg or "rate limit" in msg:
        return "Too many requests — please wait a moment and try again."

    if "dax" in msg or "syntax" in msg or "query" in msg:
        return "I had trouble generating the right query. Could you rephrase your question?"

    if "not found" in msg or "404" in msg:
        return "The Power BI dataset couldn't be reached. It may be refreshing — try again in a few minutes."

    return "Something unexpected happened. The Cx Insights team has been notified."
