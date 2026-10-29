
"""
Explainable, deterministic synthetic persona profiling.

spaCy provides linguistic annotations. Explicit evidence rules determine
the scores; scores are synthetic design estimates, not diagnoses or
scientifically validated psychological measurements.
"""

import re
from functools import lru_cache
from typing import Any

import spacy

from app.database.repository import get_persona
from app.database.module2_repository import save_profile
from app.schemas.psychological_profile_schema import PsychologicalProfile

import json
import os

from dotenv import load_dotenv
from google import genai
from pydantic import ValidationError

load_dotenv()


# Load the model once per Python process.
@lru_cache(maxsize=1)
def _get_nlp():
    try:
        return spacy.load("en_core_web_sm")
    except OSError as exc:
        raise RuntimeError(
            "spaCy English model is missing. Run: "
            "python -m spacy download en_core_web_sm"
        ) from exc


# Only fields that plausibly support a trait are considered.
# Values are rule-design choices, not learned or validated coefficients.
TRAIT_RULES = {
    "guidance_preference": {
        "preferences": {
            "positive": [
                "step by step guidance", "clear instructions",
                "detailed instructions", "guided learning",
                "regular support", "examples and documentation",
                "mentorship",
            ],
            "negative": [
                "minimal guidance", "minimal supervision",
                "independent problem solving", "self directed learning",
                "works independently",
            ],
        },
        "working_style": {
            "positive": ["guided", "structured walkthroughs"],
            "negative": ["works independently", "self directed"],
        },
        "challenges": {
            "positive": ["difficulty learning without guidance"],
            "negative": [],
        },
    },
    "openness_to_new_tools": {
        "preferences": {
            "positive": [
                "open to new tools", "eager to try new tools",
                "experiments with new tools", "explores alternatives",
                "explores new technologies", "embraces change",
                "adapts quickly", "experimentation",
            ],
            "negative": [
                "prefers familiar tools", "reluctant to adopt new tools",
                "resistant to change", "avoids new tools",
            ],
        },
        "working_style": {
            "positive": ["experiments", "iterative exploration"],
            "negative": ["resistant to change"],
        },
        "challenges": {
            "positive": [],
            "negative": ["difficulty adopting new tools"],
        },
    },
    "risk_tolerance": {
        "preferences": {
            "positive": [
                "comfortable with uncertainty", "willing to take risks",
                "experiments freely", "tries untested approaches",
                "bold experimentation", "rapid experimentation",
            ],
            "negative": [
                "risk averse", "avoids risk",
                "prefers predictable outcomes", "cautious about changes",
                "validates before implementation", "carefully evaluates risk",
            ],
        },
        "working_style": {
            "positive": ["rapid experimentation", "tries alternatives"],
            "negative": ["careful validation", "validates before implementation"],
        },
        "challenges": {
            "positive": [],
            "negative": ["concerned about unexpected outcomes"],
        },
    },
    "confidence_level": {
        "preferences": {
            "positive": [
                "confident in decisions", "highly confident",
                "takes initiative", "decisive",
                "comfortable working independently",
            ],
            "negative": [
                "hesitant to decide", "uncertain about decisions",
                "needs reassurance", "lacks confidence",
            ],
        },
        "working_style": {
            "positive": ["takes initiative", "decisive"],
            "negative": ["needs reassurance", "hesitant"],
        },
        "challenges": {
            "positive": [],
            "negative": ["difficulty making decisions"],
        },
    },
    "patience_level": {
        "preferences": {
            "positive": [
                "patient", "persistent", "methodical",
                "detail oriented", "thorough testing", "careful analysis",
                "systematic testing",
            ],
            "negative": [
                "impatient", "easily frustrated", "wants immediate results",
                "quickly abandons tasks",
            ],
        },
        "working_style": {
            "positive": ["methodical", "systematically", "thorough testing"],
            "negative": ["impatient", "easily frustrated"],
        },
        "challenges": {
            "positive": [],
            "negative": ["frustrated by repeated delays"],
        },
    },
}

DECISION_STYLE_RULES = {
    "analytical": {
        "fields": ("working_style", "preferences", "skills", "goals"),
        "phrases": (
            "data driven", "evidence based", "methodical",
            "systematic", "logical reasoning", "careful analysis",
            "compares alternatives", "structured testing matrices",
            "structured testing", "heuristic evaluation",
        ),
    },
    "experimental": {
        "fields": ("working_style", "preferences", "goals"),
        "phrases": (
            "trial and error", "rapid prototyping",
            "iterative exploration", "learn by doing",
            "tests alternatives", "duplicate sandbox pages",
            "experimentation", "experiments with",
        ),
    },
    "guidance_seeking": {
        "fields": ("preferences", "working_style", "challenges"),
        "phrases": (
            "step by step guidance", "clear instructions",
            "mentorship", "guided learning", "needs examples",
            "regular support",
        ),
    },
    "intuitive": {
        "fields": ("working_style", "preferences"),
        "phrases": (
            "gut feeling", "intuition", "instinct",
            "visual intuition", "spontaneous decisions",
            "big picture judgment",
        ),
    },
}

# Words that commonly negate a phrase. This is a practical heuristic,
# not a complete linguistic solution.
NEGATIONS = {
    "not", "never", "no", "neither", "nor", "without",
    "hardly", "rarely", "isn't", "aren't", "don't", "doesn't",
    "didn't", "can't", "cannot", "won't",
}

# Avoid scoring a single signal repeatedly when it appears several times.
MAX_EVIDENCE_PER_FIELD = 3
BASE_SCORE = 50
MAX_EXPLANATION_LENGTH = 1000


def _as_text(value: Any) -> str:
    """Convert supported database field values into readable text."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return "; ".join(_as_text(item) for item in value)
    if isinstance(value, dict):
        return "; ".join(
            f"{key}: {_as_text(item)}" for key, item in value.items()
        )
    return str(value).strip()


def _normalize(text: str) -> str:
    """Normalize text while preserving word boundaries."""
    text = text.casefold().replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", text).strip()


def _phrase_matches(text: str, phrase: str):
    """Return non-overlapping character spans for a phrase."""
    normalized_text = _normalize(text)
    normalized_phrase = _normalize(phrase)
    if not normalized_phrase:
        return []

    pattern = rf"(?<!\w){re.escape(normalized_phrase)}(?!\w)"
    return [
        (match.start(), match.end())
        for match in re.finditer(pattern, normalized_text)
    ]


def _is_negated(nlp, text: str, start: int, end: int) -> bool:
    """
    Detect nearby negation using spaCy tokens and dependency annotations.

    The local-window check handles common constructions such as
    'not confident' and 'does not prefer guidance'. It is deliberately
    conservative and cannot resolve every complex sentence.
    """
    doc = nlp(text)
    normalized = _normalize(text)

    # The phrase spans are measured on normalized text, so locate the
    # corresponding region in the parsed text approximately by tokens.
    # Using the phrase's starting character is sufficient for the local
    # window; the end is retained for future refinements.
    token_index = 0
    for token in doc:
        token_start = len(_normalize(text[:token.idx]))
        if token_start <= start:
            token_index = token.i
        else:
            break

    token = doc[token_index]
    if token.dep_ == "neg":
        return True

    left = max(0, token_index - 4)
    preceding = [t.lower_ for t in doc[left:token_index]]
    if any(word in NEGATIONS for word in preceding):
        return True

    # spaCy's parser may attach a negation token to the phrase's head.
    for nearby in doc[max(0, token_index - 2):min(len(doc), token_index + 5)]:
        if nearby.dep_ == "neg":
            return True

    # A simple fallback for common negated preference/attitude patterns.
    prefix = normalized[:start].split()
    if prefix and prefix[-1] in {"not", "never", "without", "no"}:
        return True

    return False


def _extract_evidence(persona: dict, trait_name: str, nlp):
    """
    Extract field-scoped, deduplicated signed evidence.

    Positive signal: +1
    Negative signal: -1
    Negated signal: invert the signal.

    Repeated matches of the same phrase within one field count once.
    """
    evidence = []
    rules_by_field = TRAIT_RULES[trait_name]

    for field, groups in rules_by_field.items():
        value = _as_text(persona.get(field))
        if not value:
            continue

        field_signals = set()

        for direction, phrases in groups.items():
            base_polarity = 1 if direction == "positive" else -1

            for phrase in phrases:
                if phrase in field_signals:
                    continue

                matches = _phrase_matches(value, phrase)
                if not matches:
                    continue

                # Count at most one occurrence of each phrase per field.
                start, end = matches[0]
                negated = _is_negated(nlp, value, start, end)
                polarity = -base_polarity if negated else base_polarity

                evidence.append({
                    "field": field,
                    "phrase": phrase,
                    "polarity": polarity,
                    "negated": negated,
                })
                field_signals.add(phrase)

                if len(field_signals) >= MAX_EVIDENCE_PER_FIELD:
                    break

            if len(field_signals) >= MAX_EVIDENCE_PER_FIELD:
                break

    return evidence


def _score_trait(persona: dict, trait_name: str, nlp):
    """
    Return a deterministic score and a concise explanation.

    When evidence is absent, 50 is a neutral technical fallback, not
    a claim that the persona's trait has been measured as neutral.
    """
    evidence = _extract_evidence(persona, trait_name, nlp)

    if not evidence:
        return BASE_SCORE, (
            "insufficient explicit evidence; 50 is a neutral fallback, "
            "not a measured trait value"
        )

    positive = sum(item["polarity"] > 0 for item in evidence)
    negative = sum(item["polarity"] < 0 for item in evidence)

    # Each independent signal shifts the score by 10 points. Conflicting
    # evidence offsets rather than being silently ignored.
    score = BASE_SCORE + 10 * (positive - negative)
    score = max(0, min(100, score))

    details = []
    for item in evidence[:5]:
        direction = "supports higher" if item["polarity"] > 0 else "supports lower"
        negation_note = " (negated phrase)" if item["negated"] else ""
        details.append(
            f"{item['field']} contains '{item['phrase']}' "
            f"{direction}{negation_note}"
        )

    explanation = "; ".join(details)

    if positive and negative:
        explanation += "; evidence is conflicting"
    elif positive:
        explanation += "; evidence leans higher"
    else:
        explanation += "; evidence leans lower"

    return score, explanation


def _choose_decision_style(persona: dict, nlp):
    
    """Select a style only when there is explicit phrase evidence."""
    
    counts = {style: 0 for style in DECISION_STYLE_RULES}
    evidence_by_style = {style: [] for style in DECISION_STYLE_RULES}

    for style, config in DECISION_STYLE_RULES.items():
        for field in config["fields"]:
            value = _as_text(persona.get(field))
            if not value:
                continue

            for phrase in config["phrases"]:
                matches = _phrase_matches(value, phrase)
                if not matches:
                    continue

                start, end = matches[0]
                if _is_negated(nlp, value, start, end):
                    continue

                counts[style] += 1
                evidence_by_style[style].append(f"{field}: '{phrase}'")

    maximum = max(counts.values(), default=0)

    if maximum == 0:
        return (
            "analytical",
            "No explicit decision-style evidence; analytical is a "
            "technical fallback, not a confirmed persona characteristic.",
        )

    winners = [
        style for style, count in counts.items() if count == maximum
    ]

    if len(winners) > 1:
        # Do not arbitrarily choose a style when evidence is tied.
        # Existing schema requires a single label, so use the fallback
        # and disclose the ambiguity.
        return (
            "analytical",
            "Decision-style evidence is tied across "
            + ", ".join(winners)
            + "; analytical is used as a schema-compatible fallback.",
        )

    selected = winners[0]
    details = "; ".join(evidence_by_style[selected][:4])
    return selected, f"Selected {selected} based on {details}."



def generate_psychological_profile(persona_id: int):
    """
    Generate an initial rule-based/NLP profile, let Gemini evaluate
    and produce the final profile, validate it, then persist it.
    """
    persona = get_persona(persona_id)
    if persona is None:
        raise ValueError("Persona not found")

    # 1. Generate the initial profile using existing rules and spaCy.
    nlp = _get_nlp()

    trait_scores = {}
    trait_evidence = {}
    explanations = []

    for trait_name in TRAIT_RULES:
        score, reason = _score_trait(persona, trait_name, nlp)
        evidence = _extract_evidence(persona, trait_name, nlp)

        trait_scores[trait_name] = score
        trait_evidence[trait_name] = {
            "initial_score": score,
            "evidence": evidence,
            "rule_explanation": reason,
        }
        explanations.append(f"{trait_name}={score}: {reason}")

    decision_style, style_reason = _choose_decision_style(persona, nlp)

    initial_profile = {
        "persona_id": persona_id,
        **trait_scores,
        "decision_style": decision_style,
        "rule_based_explanation": " | ".join(explanations),
        "decision_style_explanation": style_reason,
        "trait_evidence": trait_evidence,
    }

    # Only provide relevant persona fields, not database metadata.
    persona_context = {
        field: _as_text(persona.get(field))
        for field in (
            "role",
            "experience_level",
            "skills",
            "goals",
            "preferences",
            "challenges",
            "working_style",
        )
        if persona.get(field) is not None
    }

    # 2. Configure Gemini. Never silently substitute a rule-only profile.
    api_keys = [
        key.strip()
        for key in os.getenv("GEMINI_API_KEYS", "").split(",")
        if key.strip()
    ]
    model = os.getenv("GEMINI_MODEL", "").strip()

    if not api_keys:
        raise RuntimeError(
            "GEMINI_API_KEYS is not configured in the environment."
        )

    if not model:
        raise RuntimeError(
            "GEMINI_MODEL is not configured in the environment."
        )

    prompt = f"""
You generate explainable synthetic user psychological profiles for
software UX research. These are heuristic design estimates, NOT clinical
assessments, scientifically validated measurements, or facts about a
real person's mental health.

Your task is to produce the FINAL profile, not a review report.

PERSONA DATA:
{json.dumps(persona_context, ensure_ascii=False, indent=2)}

INITIAL RULE-BASED AND spaCy NLP PROFILE:
{json.dumps(initial_profile, ensure_ascii=False, indent=2)}

INSTRUCTIONS:

1. Evaluate each initial score against the persona's actual text and
   the supplied evidence. Keep a score unchanged when it is reasonable
   and adequately supported. Modify it only when the evidence indicates
   that the initial estimate is incorrect or misleading.

2. Do not invent traits, experiences, preferences, motivations, or
   behavior. Distinguish explicit evidence from weak inference.

3. The scores are integers from 0 to 100:
   - guidance_preference
   - openness_to_new_tools
   - risk_tolerance
   - confidence_level
   - patience_level

4. A score of 50 is the neutral technical fallback when there is
   insufficient evidence. It does NOT mean the trait has actually been
   measured as neutral. Retain 50 when there is no defensible evidence
   for changing it. Do not manufacture evidence to justify a score.

5. Interpret negated statements carefully. For example, "not patient"
   must not be treated as evidence of patience.

6. Choose exactly one decision_style from:
   "analytical", "experimental", "guidance_seeking", "intuitive".
   Prefer the style best supported by the persona. If the evidence is
   genuinely insufficient or tied, use "analytical" as a schema-compatible
   fallback and explicitly disclose the uncertainty.

7. The explanation must briefly describe the final estimates, important
   supporting evidence, any meaningful corrections to the initial
   scores, and uncertainty where evidence is insufficient. Mention that
   these are synthetic estimates, not validated psychological
   measurements. Do not claim certainty that the evidence cannot support.

8. Return ONLY a valid JSON object with exactly these fields:
{{
  "persona_id": {persona_id},
  "guidance_preference": 50,
  "openness_to_new_tools": 50,
  "risk_tolerance": 50,
  "confidence_level": 50,
  "patience_level": 50,
  "decision_style": "analytical",
  "explanation": "Explanation of the final synthetic estimates."
}}

Use the actual persona_id provided above. Do not return Markdown,
code fences, additional fields, or a separate review.
"""

    # 3. Ask Gemini to generate the final profile.
    try:
        client = genai.Client(api_key=api_keys[0])

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )

        response_text = response.text
        if not response_text or not response_text.strip():
            raise RuntimeError("Gemini returned an empty profile response.")

        result = json.loads(response_text)

        # Reject a response for a different persona.
        if result.get("persona_id") != persona_id:
            raise RuntimeError(
                "Gemini returned a profile with a mismatched persona_id."
            )

        # 4. Validate against the existing schema.
        try:
            profile = PsychologicalProfile.model_validate(result)
        except ValidationError as exc:
            raise RuntimeError(
                "Gemini returned a profile that failed schema validation."
            ) from exc

    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(
            f"Gemini could not generate the final psychological profile: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    # 5. Persist Gemini's validated FINAL profile, not the initial scores.
    save_profile(profile)

    return profile

