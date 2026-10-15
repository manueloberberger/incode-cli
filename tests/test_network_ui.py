"""User-facing recovery, filtered exports and live-notification results."""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import io

import pytest
from rich.console import Console
from src.exceptions import ApiError
from src.models import Duty
from src.config import theme


def test_network_view_can_retry_and_cancel():
    from src.ui.network import network_view
    action = MagicMock(side_effect=[ApiError('offline'), 'loaded'])
    with patch('src.ui.network.console'), patch('src.ui.network.get_key', return_value='r'):
        assert network_view(action)() == 'loaded'
    action = MagicMock(side_effect=ApiError('offline'))
    with patch('src.ui.network.console'), patch('src.ui.network.get_key', return_value='q'):
        assert network_view(action)() is None
    assert action.call_count == 1


def test_statistics_filter_applies_to_export_and_totals():
    from src.ui.dashboard import show_future_duties
    now = datetime.now()
    past = Duty(now - timedelta(days=2), now - timedelta(days=2) + timedelta(hours=8),
                vehicle='7220 KTWB', duty_type='SEW Tag')
    future = Duty(now + timedelta(days=2), now + timedelta(days=2, hours=12), vehicle='BKTW')
    api = MagicMock(data_status='Live-Abruf: Test')
    api.load_future_duties.return_value = [past, future]
    output = io.StringIO()
    with patch('src.ui.dashboard.console', Console(file=output, width=160, theme=theme)), \
         patch('src.ui.dashboard.clear_screen'), patch('src.ui.dashboard.flush_input'), \
         patch('src.ui.dashboard.wait_for_return'), \
         patch('src.ui.dashboard.get_key', side_effect=['f', 'p', 'q']), \
         patch('src.ui.dashboard.interactive_menu', return_value='completed'), \
         patch('src.ui.dashboard.export_to_pdf', return_value=True) as export:
        show_future_duties(api)
    assert export.call_args.args[0] == [past]
    assert 'Dienst-Statistik' in output.getvalue()
    assert 'KTWB' in output.getvalue()
    assert 'Geleistet' in output.getvalue()


@pytest.mark.parametrize('sent', [True, False])
def test_live_fetches_fresh_data_and_reports_real_send_result(sent):
    from src.ui.live import show_live_monitor
    api = MagicMock(username='test')
    api.load_daily_plan.return_value = [{'begin': datetime(2026, 10, 20, 7),
                                        'end': datetime(2026, 10, 20, 19),
                                        'vehicle': 'RTW', 'crew': {}}]
    with patch('src.ui.live.interactive_menu', return_value='today'), \
         patch('src.ui.live.load_credentials', return_value={'users': [
             {'username': 'test', 'telegram_token': 'fake', 'allowed_user_id': 123}]}), \
         patch('src.ui.live.prompt_yes_no', return_value=True), \
         patch('src.ui.live.centered_input', return_value='1'), \
         patch('src.ui.live.clear_screen'), patch('src.ui.live.console') as console, \
         patch('src.ui.live.show_daily_plan'), patch('src.ui.live.export_to_pdf', return_value=True), \
         patch('src.ui.live.send_pdf_via_bot', return_value=sent), \
         patch('src.ui.live.get_key', return_value='\x1b'):
        show_live_monitor(api)
    assert api.load_daily_plan.call_args.kwargs == {'use_cache': False}
    output = str(console.print.call_args_list)
    assert ('Telegram gesendet.' in output) is sent
    assert ('Telegram-Versand fehlgeschlagen.' in output) is not sent


def test_live_failure_keeps_display_and_can_exit():
    from src.ui.live import show_live_monitor
    api = MagicMock(username='test')
    api.load_daily_plan.side_effect = ApiError('offline')
    with patch('src.ui.live.interactive_menu', return_value='today'), \
         patch('src.ui.live.load_credentials', return_value={'users': []}), \
         patch('src.ui.live.centered_input', return_value='1'), \
         patch('src.ui.live.time.sleep'), patch('src.ui.live.clear_screen'), \
         patch('src.ui.live.console'), patch('src.ui.live.show_daily_plan') as display, \
         patch('src.ui.live.send_pdf_via_bot') as send, \
         patch('src.ui.live.get_key', return_value='\x1b'):
        show_live_monitor(api)
    display.assert_not_called()
    send.assert_not_called()


def test_compact_statistics_omit_shift_labels_but_include_all_hours():
    from src.ui.dashboard import _render_statistics
    now = datetime(2026, 10, 15)
    first = Duty(datetime(2026, 10, 1, 7), datetime(2026, 10, 1, 19),
                 vehicle='RTWA', location='Teststation', duty_type='SEW Tag 07-19')
    second = Duty(datetime(2026, 10, 2, 18), datetime(2026, 10, 2, 20),
                  location='Teststation', duty_type='Fortbildung Sonderkurs')
    output = io.StringIO()
    with patch('src.ui.dashboard.console', Console(file=output, width=160, theme=theme)):
        _render_statistics([first, second], now)
    text = output.getvalue()
    assert 'Dienst-Statistik' in text
    assert 'Dienststellen' in text
    assert 'Fortbildung' in text
    assert '14' in text
    assert 'Dienstarten' not in text
    assert 'SEW Tag 07-19' not in text
    assert 'Fortbildung Sonderkurs' not in text
