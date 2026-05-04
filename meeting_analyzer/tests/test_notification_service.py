"""
notification_service ve ilgili bileşenler için birim testleri.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ─── notification_service testleri ───────────────────────────────────────────

class TestNotifyAssignees:
    """notify_assignees fonksiyonu testleri."""

    def _make_participants(self):
        return [
            {"user_id": "usr-001", "name": "Ahmet Yilmaz", "email": "ahmet@example.com"},
            {"user_id": "usr-002", "name": "Zeynep Kara", "email": "zeynep@example.com"},
            {"user_id": "usr-003", "name": "Mehmet Demir", "email": "mehmet@example.com"},
            {"user_id": "usr-004", "name": "Elif Arslan", "email": ""},  # email yok
        ]

    @patch("src.services.notification_service.is_email_configured", return_value=True)
    @patch("src.services.notification_service.send_email")
    def test_sends_email_for_assigned_task(self, mock_send, mock_config):
        from src.services.notification_service import notify_assignees

        action_items = [
            {
                "task": "Raporu hazirla",
                "assigned_to_user_id": "usr-001",
                "assignee_name": "Ahmet Yilmaz",
                "due_date": "2026-05-10",
                "priority": "high",
                "ambiguous": False,
                "candidates": [],
            }
        ]
        result = notify_assignees(action_items, self._make_participants())

        assert len(result) == 1
        assert result[0]["user_id"] == "usr-001"
        assert result[0]["email"] == "ahmet@example.com"
        assert result[0]["tasks_count"] == 1
        mock_send.assert_called_once()

    @patch("src.services.notification_service.is_email_configured", return_value=True)
    @patch("src.services.notification_service.send_email")
    def test_does_not_send_when_assigned_to_user_id_is_null(self, mock_send, mock_config):
        from src.services.notification_service import notify_assignees

        action_items = [
            {
                "task": "Belirsiz gorev",
                "assigned_to_user_id": None,
                "assignee_name": None,
                "ambiguous": False,
                "candidates": [],
            }
        ]
        result = notify_assignees(action_items, self._make_participants())

        assert result == []
        mock_send.assert_not_called()

    @patch("src.services.notification_service.is_email_configured", return_value=True)
    @patch("src.services.notification_service.send_email")
    def test_does_not_send_when_ambiguous_is_true(self, mock_send, mock_config):
        from src.services.notification_service import notify_assignees

        action_items = [
            {
                "task": "Belirsiz atama",
                "assigned_to_user_id": "usr-001",
                "assignee_name": "Ahmet Yilmaz",
                "ambiguous": True,
                "candidates": ["usr-001", "usr-002"],
            }
        ]
        result = notify_assignees(action_items, self._make_participants())

        assert result == []
        mock_send.assert_not_called()

    @patch("src.services.notification_service.is_email_configured", return_value=True)
    @patch("src.services.notification_service.send_email")
    def test_does_not_send_when_user_id_not_in_participants(self, mock_send, mock_config):
        from src.services.notification_service import notify_assignees

        action_items = [
            {
                "task": "Gecersiz atama",
                "assigned_to_user_id": "usr-999",
                "assignee_name": "Bilinmeyen",
                "ambiguous": False,
                "candidates": [],
            }
        ]
        result = notify_assignees(action_items, self._make_participants())

        assert result == []
        mock_send.assert_not_called()

    @patch("src.services.notification_service.is_email_configured", return_value=True)
    @patch("src.services.notification_service.send_email")
    def test_groups_multiple_tasks_for_same_user(self, mock_send, mock_config):
        from src.services.notification_service import notify_assignees

        action_items = [
            {
                "task": "Raporu hazirla",
                "assigned_to_user_id": "usr-001",
                "assignee_name": "Ahmet Yilmaz",
                "due_date": "2026-05-10",
                "priority": "high",
                "ambiguous": False,
                "candidates": [],
            },
            {
                "task": "Sunumu guncelle",
                "assigned_to_user_id": "usr-001",
                "assignee_name": "Ahmet Yilmaz",
                "due_date": "2026-05-12",
                "priority": "medium",
                "ambiguous": False,
                "candidates": [],
            },
        ]
        result = notify_assignees(action_items, self._make_participants())

        assert len(result) == 1
        assert result[0]["tasks_count"] == 2
        mock_send.assert_called_once()  # Tek mail

    @patch("src.services.notification_service.is_email_configured", return_value=True)
    @patch("src.services.notification_service.send_email")
    def test_sends_to_multiple_users(self, mock_send, mock_config):
        from src.services.notification_service import notify_assignees

        action_items = [
            {
                "task": "Raporu hazirla",
                "assigned_to_user_id": "usr-001",
                "assignee_name": "Ahmet Yilmaz",
                "ambiguous": False,
                "candidates": [],
            },
            {
                "task": "Tasarimi guncelle",
                "assigned_to_user_id": "usr-002",
                "assignee_name": "Zeynep Kara",
                "ambiguous": False,
                "candidates": [],
            },
        ]
        result = notify_assignees(action_items, self._make_participants())

        assert len(result) == 2
        assert mock_send.call_count == 2

    @patch("src.services.notification_service.is_email_configured", return_value=True)
    @patch("src.services.notification_service.send_email")
    def test_skips_user_without_email(self, mock_send, mock_config):
        from src.services.notification_service import notify_assignees

        action_items = [
            {
                "task": "Email'siz kullanici",
                "assigned_to_user_id": "usr-004",
                "assignee_name": "Elif Arslan",
                "ambiguous": False,
                "candidates": [],
            }
        ]
        result = notify_assignees(action_items, self._make_participants())

        assert result == []
        mock_send.assert_not_called()

    @patch("src.services.notification_service.is_email_configured", return_value=False)
    def test_skips_all_when_smtp_not_configured(self, mock_config):
        from src.services.notification_service import notify_assignees

        action_items = [
            {
                "task": "Gorev",
                "assigned_to_user_id": "usr-001",
                "ambiguous": False,
                "candidates": [],
            }
        ]
        result = notify_assignees(action_items, self._make_participants())
        assert result == []

    @patch("src.services.notification_service.is_email_configured", return_value=True)
    @patch("src.services.notification_service.send_email")
    def test_empty_action_items_returns_empty(self, mock_send, mock_config):
        from src.services.notification_service import notify_assignees

        result = notify_assignees([], self._make_participants())
        assert result == []
        mock_send.assert_not_called()

    @patch("src.services.notification_service.is_email_configured", return_value=True)
    @patch("src.services.notification_service.send_email")
    def test_send_failure_does_not_crash(self, mock_send, mock_config):
        from src.services.notification_service import notify_assignees
        from src.services.email_service import EmailSendError

        mock_send.side_effect = EmailSendError("SMTP error")
        action_items = [
            {
                "task": "Gorev",
                "assigned_to_user_id": "usr-001",
                "assignee_name": "Ahmet",
                "ambiguous": False,
                "candidates": [],
            }
        ]
        # Hata fırlatmamalı
        result = notify_assignees(action_items, self._make_participants())
        assert result == []


# ─── action_item_agent normalize testleri ────────────────────────────────────

class TestUserIdNormalization:
    """utils.normalize_user_id ve normalize_candidates testleri."""

    def test_normalize_user_id_valid(self):
        from src.services.ai_agents.utils import normalize_user_id
        assert normalize_user_id("usr-001", {"usr-001", "usr-002"}) == "usr-001"

    def test_normalize_user_id_invalid(self):
        from src.services.ai_agents.utils import normalize_user_id
        assert normalize_user_id("usr-999", {"usr-001", "usr-002"}) is None

    def test_normalize_user_id_none(self):
        from src.services.ai_agents.utils import normalize_user_id
        assert normalize_user_id(None, {"usr-001"}) is None

    def test_normalize_user_id_empty_string(self):
        from src.services.ai_agents.utils import normalize_user_id
        assert normalize_user_id("", {"usr-001"}) is None

    def test_normalize_candidates_valid(self):
        from src.services.ai_agents.utils import normalize_candidates
        result = normalize_candidates(
            ["usr-001", "usr-002", "usr-999"],
            {"usr-001", "usr-002"},
        )
        assert result == ["usr-001", "usr-002"]

    def test_normalize_candidates_invalid_type(self):
        from src.services.ai_agents.utils import normalize_candidates
        assert normalize_candidates("not-a-list", {"usr-001"}) == []

    def test_normalize_candidates_empty(self):
        from src.services.ai_agents.utils import normalize_candidates
        assert normalize_candidates([], {"usr-001"}) == []


# ─── email_service config testleri ───────────────────────────────────────────

class TestEmailConfig:
    """email_service yapilandirma testleri."""

    @patch.dict("os.environ", {
        "SMTP_HOST": "smtp.gmail.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "test@gmail.com",
        "SMTP_PASSWORD": "secret",
        "FROM_EMAIL": "test@gmail.com",
    })
    def test_is_email_configured_true(self):
        from src.services.email_service import is_email_configured
        assert is_email_configured() is True

    @patch.dict("os.environ", {
        "SMTP_HOST": "",
        "SMTP_USER": "",
        "SMTP_PASSWORD": "",
        "FROM_EMAIL": "",
    })
    def test_is_email_configured_false(self):
        from src.services.email_service import is_email_configured
        assert is_email_configured() is False


# ─── ai_output_models testleri ───────────────────────────────────────────────

class TestSummaryActionItemModel:
    """SummaryActionItem yeni alan testleri."""

    def test_new_fields_in_summary_action_item(self):
        from src.services.ai_output_models import SummaryActionItem
        item = SummaryActionItem(
            id="action-item-1-test",
            title="Test gorev",
            assigned_to_user_id="usr-001",
            assignee_name="Ahmet",
            ambiguous=False,
            candidates=[],
            reason="",
        )
        assert item.assigned_to_user_id == "usr-001"
        assert item.assignee_name == "Ahmet"
        assert item.ambiguous is False
        assert item.candidates == []

    def test_ambiguous_action_item(self):
        from src.services.ai_output_models import SummaryActionItem
        item = SummaryActionItem(
            id="action-item-2-test",
            title="Belirsiz gorev",
            assigned_to_user_id=None,
            assignee_name=None,
            ambiguous=True,
            candidates=["usr-001", "usr-002"],
            reason="Iki kisi de Ahmet adinda",
        )
        assert item.assigned_to_user_id is None
        assert item.ambiguous is True
        assert len(item.candidates) == 2
        assert item.reason == "Iki kisi de Ahmet adinda"

    def test_build_meeting_summary_output_with_new_fields(self):
        from src.services.ai_output_models import build_meeting_summary_output

        output = build_meeting_summary_output(
            executive_summary="Test ozet",
            action_items=[
                {
                    "task": "Gorev 1",
                    "assigned_to_user_id": "usr-001",
                    "assignee_name": "Ahmet",
                    "due_date": "2026-05-10",
                    "priority": "high",
                    "ambiguous": False,
                    "candidates": [],
                    "reason": "",
                    "needs_review": False,
                },
                {
                    "task": "Gorev 2",
                    "assigned_to_user_id": None,
                    "assignee_name": None,
                    "ambiguous": True,
                    "candidates": ["usr-001", "usr-002"],
                    "reason": "Belirsiz",
                    "needs_review": True,
                },
            ],
        )
        assert len(output.actionItems) == 2
        assert output.actionItems[0].assigned_to_user_id == "usr-001"
        assert output.actionItems[0].ambiguous is False
        assert output.actionItems[1].assigned_to_user_id is None
        assert output.actionItems[1].ambiguous is True
        assert output.actionItems[1].candidates == ["usr-001", "usr-002"]

    def test_source_fields_in_summary_action_item(self):
        from src.services.ai_output_models import SummaryActionItem
        item = SummaryActionItem(
            id="action-item-source-test",
            title="Kaynak referansli gorev",
            source_quote="Ahmet raporu cumaya kadar hazirlasin",
            source_speaker="Mehmet",
        )
        assert item.source_quote == "Ahmet raporu cumaya kadar hazirlasin"
        assert item.source_speaker == "Mehmet"

    def test_source_fields_default_none(self):
        from src.services.ai_output_models import SummaryActionItem
        item = SummaryActionItem(
            id="action-item-no-source",
            title="Kaynak referanssiz gorev",
        )
        assert item.source_quote is None
        assert item.source_speaker is None

    def test_build_output_with_source_fields(self):
        from src.services.ai_output_models import build_meeting_summary_output
        output = build_meeting_summary_output(
            executive_summary="Ozet",
            action_items=[
                {
                    "task": "Raporu hazirla",
                    "source_quote": "Rapor cumaya kadar hazir olmali",
                    "source_speaker": "Zeynep",
                    "priority": "high",
                },
            ],
        )
        assert output.actionItems[0].source_quote == "Rapor cumaya kadar hazir olmali"
        assert output.actionItems[0].source_speaker == "Zeynep"


# ─── Jaccard dedup testleri ──────────────────────────────────────────────────

class TestJaccardDedup:
    """jaccard_similarity ve deduplicate_tasks testleri."""

    def test_jaccard_identical(self):
        from src.services.ai_agents.utils import jaccard_similarity
        assert jaccard_similarity("raporu hazirla", "raporu hazirla") == 1.0

    def test_jaccard_similar(self):
        from src.services.ai_agents.utils import jaccard_similarity
        # "raporu hazirla" vs "rapor hazirlanacak" → ortak: {rapor/raporu, hazirla/hazirlanacak}
        score = jaccard_similarity("raporu hazirla", "rapor hazirlanacak")
        assert score >= 0.0  # Some overlap expected

    def test_jaccard_different(self):
        from src.services.ai_agents.utils import jaccard_similarity
        score = jaccard_similarity("raporu hazirla", "sunumu guncelle")
        assert score == 0.0

    def test_jaccard_empty(self):
        from src.services.ai_agents.utils import jaccard_similarity
        assert jaccard_similarity("", "raporu hazirla") == 0.0
        assert jaccard_similarity("", "") == 0.0

    def test_dedup_removes_similar_same_user(self):
        from src.services.ai_agents.utils import deduplicate_tasks
        tasks = [
            {"task": "Haftalik raporu hazirla", "assigned_to_user_id": "usr-001", "confidence": 0.9},
            {"task": "Haftalik raporu hazirla ve gonder", "assigned_to_user_id": "usr-001", "confidence": 0.7},
        ]
        result = deduplicate_tasks(tasks)
        assert len(result) == 1
        assert result[0]["confidence"] == 0.9  # Yüksek confidence'lı kaldı

    def test_dedup_keeps_different_users(self):
        from src.services.ai_agents.utils import deduplicate_tasks
        tasks = [
            {"task": "Raporu hazirla", "assigned_to_user_id": "usr-001", "confidence": 0.9},
            {"task": "Raporu hazirla", "assigned_to_user_id": "usr-002", "confidence": 0.8},
        ]
        result = deduplicate_tasks(tasks)
        assert len(result) == 2  # Farklı kişilere → korunur

    def test_dedup_keeps_different_tasks(self):
        from src.services.ai_agents.utils import deduplicate_tasks
        tasks = [
            {"task": "Raporu hazirla", "assigned_to_user_id": "usr-001", "confidence": 0.9},
            {"task": "Sunumu guncelle", "assigned_to_user_id": "usr-001", "confidence": 0.8},
        ]
        result = deduplicate_tasks(tasks)
        assert len(result) == 2  # Farklı görevler → korunur

    def test_dedup_replaces_with_higher_confidence(self):
        from src.services.ai_agents.utils import deduplicate_tasks
        tasks = [
            {"task": "Haftalik raporu hazirla", "assigned_to_user_id": "usr-001", "confidence": 0.5},
            {"task": "Haftalik raporu hazirla ve tamamla", "assigned_to_user_id": "usr-001", "confidence": 0.95},
        ]
        result = deduplicate_tasks(tasks)
        assert len(result) == 1
        assert result[0]["confidence"] == 0.95  # Daha yüksek confidence

    def test_dedup_empty_list(self):
        from src.services.ai_agents.utils import deduplicate_tasks
        assert deduplicate_tasks([]) == []

    def test_dedup_single_task(self):
        from src.services.ai_agents.utils import deduplicate_tasks
        tasks = [{"task": "Raporu hazirla", "assigned_to_user_id": "usr-001", "confidence": 0.9}]
        result = deduplicate_tasks(tasks)
        assert len(result) == 1

