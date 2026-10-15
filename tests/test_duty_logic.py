"""Regression cases for data shared by CLI and future interfaces."""
from dataclasses import asdict, replace
from datetime import datetime, timedelta

import pytest

from src.models import Duty
from src.utils import (duty_identity, merge_duties, vehicle_category, duty_hours,
                       filter_duties, duty_fingerprint)


@pytest.fixture
def duty():
    return Duty(datetime(2026, 10, 15, 7), datetime(2026, 10, 15, 19),
                vehicle='7213 RTWA', location='Test A', duty_type='SEW Tag 07-19',
                crew=['Test A', 'Test B'], source_id='shift-1', source_scope='test-account')


def test_simultaneous_duties_and_archive_duplicates(duty):
    other = replace(duty, source_id='shift-2', vehicle='KTW')
    assert len(merge_duties([duty, other], [replace(duty)])) == 2


def test_legacy_simultaneous_duties_survive(duty):
    first = replace(duty, source_id=None)
    second = replace(first, vehicle='KTW')
    assert len(merge_duties([first, second], [replace(first)])) == 2


def test_merge_keeps_current_details_and_enriches_missing_fields(duty):
    current = replace(duty, location='', crew=['Current'])
    merged = merge_duties([current], [duty])
    assert len(merged) == 1
    assert merged[0].location == 'Test A'
    assert merged[0].crew == ['Current']


def test_upstream_identity_survives_time_vehicle_and_crew_changes(duty):
    changed = replace(duty, begin=duty.begin + timedelta(hours=1), vehicle='KTW', crew=['New'])
    assert duty_identity(duty) == duty_identity(changed)
    assert duty_identity(duty) != duty_identity(replace(duty, source_scope='other-account'))


def test_legacy_identity_normalizes_datetime_strings(duty):
    duty = replace(duty, source_id=None)
    data = asdict(duty)
    data['begin'] = duty.begin.isoformat()
    data['end'] = duty.end.isoformat()
    assert duty_identity(duty) == duty_identity(data)


@pytest.mark.parametrize('vehicle,expected', [
    ('7213 RTWA', 'RTWA'), ('7220 KTWB', 'KTWB'), ('123 BKTW', 'BKTW'),
    ('7204 RTW', 'RTW'), ('7223 KTW', 'KTW'), (None, 'Ohne Fahrzeug'),
])
def test_vehicle_tokens(vehicle, expected):
    assert vehicle_category(vehicle) == expected


def test_stats_classify_completed_ongoing_future_cancelled(duty):
    now = datetime(2026, 10, 15, 12)
    past = replace(duty, begin=duty.begin - timedelta(days=1), end=duty.end - timedelta(days=1))
    future = replace(duty, begin=duty.begin + timedelta(days=1), end=duty.end + timedelta(days=1))
    cancelled = replace(duty, is_cancelled=True)
    duties = [past, duty, future, cancelled]
    assert duty_hours(duties, now) == {'2026-10': (12, 24)}
    assert filter_duties(duties, 'completed', now) == [past]
    assert filter_duties(duties, 'planned', now) == [duty, future]
    assert filter_duties(duties, 'month:2026-11', now) == []


def test_change_fingerprint_ignores_order_but_detects_details(duty):
    data = asdict(duty)
    assert duty_fingerprint(data) == duty_fingerprint(dict(data, crew=list(reversed(duty.crew))))
    for field, value in [('crew', ['New']), ('location', 'Test B'), ('comment', 'New')]:
        assert duty_fingerprint(data) != duty_fingerprint(dict(data, **{field: value}))


@pytest.mark.parametrize('location,vehicle,label,expected', [
    ('OST Feistritz/Drau', '7213 RTWA', 'Beruflich', 'SEW'),
    ('OST Feistritz/Drau', None, 'SEW Tag 07-19', 'SEW'),
    ('Feistritz an der Drau', None, 'Tagdienst', 'SEW'),
    ('OST Feistritz/Drau', None, 'Fortbildung', 'Fortbildung'),
    ('OST Feistritz/Drau', None, 'Ambulanzdienst', 'Ambulanzdienst'),
    ('BST Villach', '7207 RTWA', 'Beruflich', 'RTWA'),
    ('BST Villach', '7207 RTWA', 'SEW Tag 07-19', 'SEW'),
    ('BST Villach', '7204 RTW', 'RTW Tag', 'RTW'),
    ('BST Villach', '7220 KTWB', 'Beruflich', 'KTWB'),
    ('Feistritz/Gail', None, 'Beruflich', 'Ohne Fahrzeug'),
])
def test_service_category_uses_confirmed_station_rule(duty, location, vehicle, label, expected):
    from src.utils import duty_category
    assert duty_category(replace(duty, location=location, vehicle=vehicle, duty_type=label)) == expected
