
import pytest

from app.services import trait_generator as tg


@pytest.fixture(scope="module")
def nlp():
    return tg._get_nlp()


def test_spacy_model_loads(nlp):
    doc = nlp("The designer prefers structured testing.")
    assert len(doc) > 0
    assert any(token.dep_ for token in doc)


def test_no_evidence_is_not_presented_as_measured_neutrality(nlp):
    score, explanation = tg._score_trait(
        {"role": "UX Designer"},
        "guidance_preference",
        nlp,
    )

    assert score == 50
    assert "insufficient explicit evidence" in explanation
    assert "not a measured trait value" in explanation


def test_negated_guidance_phrase_reverses_signal(nlp):
    positive = {
        "preferences": "I prefer step-by-step guidance."
    }
    negative = {
        "preferences": "I do not prefer step-by-step guidance."
    }

    positive_score, _ = tg._score_trait(
        positive, "guidance_preference", nlp
    )
    negative_score, _ = tg._score_trait(
        negative, "guidance_preference", nlp
    )

    assert positive_score > 50
    assert negative_score < positive_score


def test_conflicting_evidence_is_disclosed(nlp):
    persona = {
        "preferences": (
            "I prefer clear instructions but also prefer minimal guidance."
        )
    }

    score, explanation = tg._score_trait(
        persona, "guidance_preference", nlp
    )

    assert 0 <= score <= 100
    assert "conflicting" in explanation


def test_unrelated_role_does_not_create_trait_evidence(nlp):
    persona = {
        "role": "UX Designer",
        "skills": "Wireframing, prototyping, usability testing",
        "goals": "Improve navigation in Figma",
    }

    score, explanation = tg._score_trait(
        persona, "confidence_level", nlp
    )

    assert score == 50
    assert "insufficient explicit evidence" in explanation


def test_decision_style_fallback_is_explained(nlp):
    style, explanation = tg._choose_decision_style(
        {"role": "Figma user"},
        nlp,
    )

    assert style == "analytical"
    assert "fallback" in explanation


def test_decision_style_uses_explicit_evidence(nlp):
    style, explanation = tg._choose_decision_style(
        {
            "working_style": (
                "Uses systematic testing and careful analysis."
            )
        },
        nlp,
    )

    assert style == "analytical"
    assert "Selected analytical" in explanation


def test_scores_always_stay_within_range(nlp):
    for trait_name in tg.TRAIT_RULES:
        score, _ = tg._score_trait(
            {
                "preferences": (
                    "I prefer clear instructions, step-by-step guidance, "
                    "and guided learning."
                ),
                "working_style": "Methodical and systematic.",
            },
            trait_name,
            nlp,
        )

        assert 0 <= score <= 100
