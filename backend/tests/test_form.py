import json
import os
import sys
from pathlib import Path

os.environ.setdefault("MONGO_ATLAS_URI", "mongodb://localhost:27017")
sys.path.append(str(Path(__file__).resolve().parents[1]))

from server import FormSubmission


def test_form_submission_truncates_detected_goal_titles_to_80_chars():
    long_title = "Quero finalmente organizar toda minha rotina diária com muitos detalhes extras desnecessários"

    submission = FormSubmission.as_form(
        full_name="Usuário Teste",
        email="teste@elios.com",
        whatsapp="+5511999999999",
        date_of_birth=None,
        responses=json.dumps([
            {"question_id": "q1", "answer": "Vou treinar 4x por semana"}
        ]),
        detected_goals=json.dumps([
            {
                "question_id": "q1",
                "pillar": "Saúde",
                "title": long_title,
                "description": "meta longa"
            }
        ]),
        profile_photo=None,
    )

    assert len(submission.detected_goals) == 1
    assert submission.detected_goals[0].title == long_title[:80]
    assert len(submission.detected_goals[0].title) <= 80
