from collections.abc import Mapping, Sequence

from app.models.assessment_question import AssessmentQuestion


def calculate_assessment_score(
    questions: Sequence[AssessmentQuestion],
    selected_options: Mapping[int, int],
    passing_score: float,
) -> tuple[float, bool, dict[int, bool]]:
    correct_by_question = {
        question.id: selected_options[question.id] == question.correct_option_index
        for question in questions
    }
    correct_count = sum(correct_by_question.values())
    score = round(correct_count / len(questions) * 100, 2)
    return score, score >= passing_score, correct_by_question