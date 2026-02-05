"""
Tests for the UI modules in src/ui/
"""
import pytest
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestUIImports:
    """Test that all UI modules can be imported without errors."""

    def test_import_components(self):
        """Test importing components module."""
        from src.ui import components
        assert hasattr(components, 'interactive_menu')
        assert hasattr(components, 'render_next_duty_panel')
        assert hasattr(components, 'select_date_interactive')

    def test_import_dashboard(self):
        """Test importing dashboard module."""
        from src.ui import dashboard
        assert hasattr(dashboard, 'show_future_duties')

    def test_import_daily_plan(self):
        """Test importing daily_plan module."""
        from src.ui import daily_plan
        assert hasattr(daily_plan, 'show_daily_plan')

    def test_import_staff(self):
        """Test importing staff module."""
        from src.ui import staff
        assert hasattr(staff, 'show_staff_search')
        assert hasattr(staff, 'show_colleague_search')

    def test_import_settings(self):
        """Test importing settings module."""
        from src.ui import settings
        assert hasattr(settings, 'show_settings_menu')

    def test_import_events(self):
        """Test importing events module."""
        from src.ui import events
        assert hasattr(events, 'show_events_menu')

    def test_import_absences(self):
        """Test importing absences module."""
        from src.ui import absences
        assert hasattr(absences, 'show_absences')

    def test_import_live(self):
        """Test importing live module."""
        from src.ui import live
        assert hasattr(live, 'show_live_monitor')

    def test_import_list_view(self):
        """Test importing list_view module."""
        from src.ui import list_view
        assert hasattr(list_view, 'show_plan_list')


class TestRenderNextDutyPanel:
    """Tests for render_next_duty_panel function."""

    @patch('src.ui.components.console')
    def test_render_with_none_duty(self, mock_console):
        """Test that None duty returns early without error."""
        from src.ui.components import render_next_duty_panel

        # Should not raise any exception
        render_next_duty_panel(None)
        mock_console.print.assert_not_called()

    @patch('src.ui.components.console')
    def test_render_with_duty_today(self, mock_console):
        """Test rendering a duty that is today."""
        from src.ui.components import render_next_duty_panel
        from src.models import Duty

        now = datetime.now()
        duty = Duty(
            begin=now.replace(hour=8, minute=0),
            end=now.replace(hour=16, minute=0),
            location="Wien",
            vehicle="RTW 1",
            duty_type="Rettungsdienst",
            crew=["Max Mustermann"],
            comment=""
        )

        render_next_duty_panel(duty)
        assert mock_console.print.called

    @patch('src.ui.components.console')
    def test_render_with_duty_tomorrow(self, mock_console):
        """Test rendering a duty that is tomorrow."""
        from src.ui.components import render_next_duty_panel
        from src.models import Duty

        tomorrow = datetime.now() + timedelta(days=1)
        duty = Duty(
            begin=tomorrow.replace(hour=7, minute=0),
            end=tomorrow.replace(hour=19, minute=0),
            location="Graz",
            vehicle="KTW 2",
            duty_type="KTW",
            crew=["Anna Schmidt", "Hans Huber", "Maria Maier"],
            comment=""
        )

        render_next_duty_panel(duty)
        assert mock_console.print.called

    @patch('src.ui.components.console')
    def test_render_with_no_vehicle(self, mock_console):
        """Test rendering a duty without vehicle info."""
        from src.ui.components import render_next_duty_panel
        from src.models import Duty

        now = datetime.now()
        duty = Duty(
            begin=now.replace(hour=8, minute=0),
            end=now.replace(hour=16, minute=0),
            location="Linz",
            vehicle="",
            duty_type="Dienst",
            crew=[],
            comment=""
        )

        render_next_duty_panel(duty)
        assert mock_console.print.called


class TestSendPdfViaBot:
    """Tests for send_pdf_via_bot function."""

    @patch('src.ui.components.console')
    @patch('src.ui.components.load_credentials')
    def test_send_without_config(self, mock_load_creds, mock_console):
        """Test that unconfigured bot returns False."""
        from src.ui.components import send_pdf_via_bot

        mock_load_creds.return_value = {}

        result = send_pdf_via_bot(MagicMock(), "/path/to/file.pdf", "Test")

        assert result is False

    @patch('src.ui.components.console')
    @patch('src.ui.components.load_credentials')
    @patch('src.ui.components.IncodeBot')
    def test_send_with_config(self, mock_bot_class, mock_load_creds, mock_console):
        """Test sending PDF with configured bot."""
        from src.ui.components import send_pdf_via_bot

        # Mock incode instance with username
        mock_incode = MagicMock()
        mock_incode.username = 'testuser'

        # Config must be in user-specific format (users array)
        mock_load_creds.return_value = {
            'users': [{
                'username': 'testuser',
                'telegram_token': 'test_token',
                'allowed_user_id': 12345
            }]
        }

        mock_bot = MagicMock()
        mock_bot.send_document.return_value = True
        mock_bot_class.return_value = mock_bot

        result = send_pdf_via_bot(mock_incode, "/path/to/file.pdf", "Test Caption")

        assert result is True
        mock_bot.send_document.assert_called_once_with(12345, "/path/to/file.pdf", "Test Caption")


class TestCenteredPrompt:
    """Tests for CenteredPrompt class."""

    def test_centered_prompt_exists(self):
        """Test that CenteredPrompt class exists."""
        from src.ui.components import CenteredPrompt
        from rich.prompt import Prompt

        assert issubclass(CenteredPrompt, Prompt)
        assert CenteredPrompt.prompt_suffix == ""


class TestSelectDateInteractiveModule:
    """Tests for select_date_interactive function signature."""

    def test_select_date_function_exists(self):
        """Test that select_date_interactive function exists."""
        from src.ui.components import select_date_interactive
        assert callable(select_date_interactive)


class TestInteractiveMenuModule:
    """Tests for interactive_menu function signature."""

    def test_menu_function_exists(self):
        """Test that interactive_menu function exists."""
        from src.ui.components import interactive_menu
        assert callable(interactive_menu)


class TestDashboardModule:
    """Tests for dashboard module functions."""

    def test_dashboard_exports(self):
        """Test that dashboard module has expected exports."""
        from src.ui import dashboard
        
        assert hasattr(dashboard, 'show_future_duties')
        assert callable(dashboard.show_future_duties)


class TestAbsencesModule:
    """Tests for absences module."""

    def test_absences_exports(self):
        """Test that absences module has expected exports."""
        from src.ui import absences
        
        assert hasattr(absences, 'show_absences')
        assert callable(absences.show_absences)


class TestEventsModule:
    """Tests for events module."""

    def test_events_module_exports(self):
        """Test that events module has expected exports."""
        from src.ui import events
        
        assert hasattr(events, 'show_events_menu')
        assert callable(events.show_events_menu)


class TestLiveModule:
    """Tests for live monitoring module."""

    def test_live_module_exports(self):
        """Test that live module has expected exports."""
        from src.ui import live
        
        assert hasattr(live, 'show_live_monitor')
        assert callable(live.show_live_monitor)


class TestListViewModule:
    """Tests for list view module."""

    def test_list_view_exports(self):
        """Test that list_view module has expected exports."""
        from src.ui import list_view
        
        assert hasattr(list_view, 'show_plan_list')
        assert callable(list_view.show_plan_list)


class TestSettingsModule:
    """Tests for settings module."""

    def test_settings_exports(self):
        """Test that settings module has expected exports."""
        from src.ui import settings
        
        assert hasattr(settings, 'show_settings_menu')
        assert callable(settings.show_settings_menu)


class TestStaffModule:
    """Tests for staff module."""

    def test_staff_exports(self):
        """Test that staff module has expected exports."""
        from src.ui import staff
        
        assert hasattr(staff, 'show_staff_search')
        assert hasattr(staff, 'show_colleague_search')
        assert callable(staff.show_staff_search)
        assert callable(staff.show_colleague_search)

