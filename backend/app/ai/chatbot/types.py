from dataclasses import dataclass, field

# How a reply was produced (stored with each assistant message and shown to the student):
SOURCE_DATA = "data"  # computed from the student's own PlaceGenie data
SOURCE_GUIDE = "guide"  # the built-in placement guide
SOURCE_AI = "ai"  # a language model
SOURCE_FALLBACK = "fallback"  # the language model failed, so the built-in guide answered
SOURCE_LIMIT = "limit"  # a question PlaceGenie cannot answer (real-time company decisions)
SOURCE_HELP = "help"  # greetings, help text, out-of-scope questions


@dataclass
class Draft:
    """A reply before it is saved."""

    text: str
    source: str
    suggestions: list[str] = field(default_factory=list)  # follow-up questions the UI can offer as buttons
