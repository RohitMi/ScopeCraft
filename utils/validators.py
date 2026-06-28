# utils/validators.py
# Input validation for all user-facing inputs

MIN_IDEA_CHARS = 30
MIN_ANSWER_CHARS = 5
MIN_SESSION_NAME_CHARS = 3

def validate_idea(idea: str) -> tuple[bool, str]:
    """
    Validate app idea input.
    Returns (is_valid: bool, error_message: str)
    """
    if not idea or not idea.strip():
        return False, "Please describe your app idea before starting."

    if len(idea.strip()) < MIN_IDEA_CHARS:
        return False, f"Idea too short — please add more detail (min {MIN_IDEA_CHARS} characters). Currently: {len(idea.strip())}."

    if len(idea.strip().split()) < 5:
        return False, "Idea too vague — please use at least 5 words to describe your app."

    return True, ""


def validate_session_name(name: str) -> tuple[bool, str]:
    """
    Validate session name input.
    Returns (is_valid: bool, error_message: str)
    """
    if not name or not name.strip():
        return False, "Session name is required."

    if len(name.strip()) < MIN_SESSION_NAME_CHARS:
        return False, f"Session name too short (min {MIN_SESSION_NAME_CHARS} characters)."

    if len(name.strip()) > 100:
        return False, "Session name too long (max 100 characters)."

    return True, ""


def validate_answer(answer: str) -> tuple[bool, str]:
    """
    Validate user answer during interview.
    Returns (is_valid: bool, error_message: str)
    """
    if not answer or not answer.strip():
        return False, "Answer cannot be empty — please respond to the question."

    if len(answer.strip()) < MIN_ANSWER_CHARS:
        return False, f"Answer too short (min {MIN_ANSWER_CHARS} characters)."

    return True, ""


def validate_conflict_input(text: str) -> tuple[bool, str]:
    """
    Validate conflict clarification input.
    Returns (is_valid: bool, error_message: str)
    """
    if not text or not text.strip():
        return False, "Please enter a clarification or click Proceed to Generation."

    return True, ""