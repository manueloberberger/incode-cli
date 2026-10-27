import copy
import json
from dataclasses import asdict
from datetime import datetime
from unittest.mock import patch
from src.parser import parse_personal_duties, fix_datetime
from src.utils import assignment_lines, duty_fingerprint, duty_identity
from src.ical import export_to_ics
from icalendar import Calendar


def payload():
    return {'data': [dict(dataGuid='synthetic-duty', dutyTypeName='Beruflich', shiftName='[FFA] Fernfahrt',
        begin='2030-01-20T05:00:00Z', end='2030-01-20T17:00:00Z',
        allocationInfo={'third': ['[ SEW ]', 'Demo C', '1003 RTW'],
                        'first': ['[ SEW ]', 'Demo A', '1001 RTW'],
                        'second': ['[ SEW ]', 'Demo B', '1002 KTW']},
        attendances=[dict(guid='second', begin='2030-01-20T09:00:00Z', end='2030-01-20T13:00:00Z'),
                     dict(guid='third', begin='2030-01-20T13:00:00Z', end='2030-01-20T17:00:00Z'),
                     dict(guid='first', begin='2030-01-20T05:00:00Z', end='2030-01-20T09:00:00Z')])]} 


def test_many_allocations_keep_one_duty_and_join_by_identity():
    duties = parse_personal_duties(payload())
    assert len(duties) == 1
    duty = duties[0]
    assert duty.duration_hours == 12
    assert [p['vehicle'] for p in duty.assignments] == ['1001 RTW', '1002 KTW', '1003 RTW']
    assert [p['crew'] for p in duty.assignments] == [['Demo A'], ['Demo B'], ['Demo C']]
    assert len(assignment_lines(duty.assignments)) == 3
    assert len(duty.crew) == 3


def test_cancelled_and_duplicate_parts_are_ignored():
    data = payload(); row = data['data'][0]
    row['attendances'][0]['isCanceled'] = True
    row['attendances'].append(copy.deepcopy(row['attendances'][1]))
    duty = parse_personal_duties(data)[0]
    assert not duty.is_cancelled
    assert len(duty.assignments) == 2
    assert '1002 KTW' not in duty.vehicle


def test_original_guid_and_missing_mapping_do_not_guess():
    data = payload(); row = data['data'][0]
    row['attendances'][0]['originalGuid'] = row['attendances'][0].pop('guid')
    row['attendances'][1]['guid'] = 'unknown'
    duty = parse_personal_duties(data)[0]
    assert duty.assignments[1]['vehicle'] == '1002 KTW'
    assert duty.assignments[2]['vehicle'] == ''
    assert 'Fahrzeug offen' in assignment_lines(duty.assignments)[2]


def test_malformed_json_legacy_labels_and_single_duty():
    data = payload(); row = data['data'][0]; row['attendances'] = 'broken'
    duty = parse_personal_duties(data)[0]
    assert len(duty.crew) == 3 and not duty.assignments
    row['allocationInfo'] = {'only': ['[ SEW ]', 'Demo', '1001 RTW']}
    row['attendances'] = json.dumps([dict(guid='only', begin=row['begin'], end=row['end'])])
    duty = parse_personal_duties(data)[0]
    assert duty.vehicle == '1001 RTW' and duty.assignments == []


def test_overnight_clips_outside_times_and_rejects_invalid():
    data = payload(); row = data['data'][0]
    row['end'] = '2030-01-21T05:00:00Z'
    row['attendances'][1]['end'] = '2030-01-21T09:00:00Z'
    row['attendances'][0]['end'] = '2030-01-20T04:00:00Z'
    duty = parse_personal_duties(data)[0]
    assert len(duty.assignments) == 2
    assert duty.assignments[-1]['end'] == fix_datetime(row['end']).isoformat()
    assert '21.01.' in assignment_lines(duty.assignments)[-1]


def test_boundary_change_is_detected_but_reordering_is_not():
    duty = parse_personal_duties(payload())[0]
    before = asdict(duty); after = copy.deepcopy(before)
    after['assignments'].reverse()
    assert duty_fingerprint(before) == duty_fingerprint(after)
    after['assignments'][0]['begin'] = '2030-01-20T15:00:00'
    assert duty_identity(before) == duty_identity(after)
    assert duty_fingerprint(before) != duty_fingerprint(after)


def test_calendar_keeps_one_event_with_all_parts(tmp_path):
    path = tmp_path / 'parts.ics'
    duty = parse_personal_duties(payload())[0]
    assert export_to_ics([duty], str(path))
    events = Calendar.from_ical(path.read_bytes()).walk('vevent')
    assert len(events) == 1
    assert events[0].decoded('dtend') - events[0].decoded('dtstart') == duty.end - duty.begin
    for vehicle in ['1001 RTW', '1002 KTW', '1003 RTW']:
        assert vehicle in str(events[0]['description'])


def test_cached_roundtrip_preserves_assignments():
    import asyncio
    from src.api_async import AsyncIncodeRequests
    duty = parse_personal_duties(payload())[0]
    stored = asdict(duty)
    stored['begin'] = duty.begin.isoformat(); stored['end'] = duty.end.isoformat()
    client = AsyncIncodeRequests('https://example.invalid')
    with patch.object(client, '_get_cached_data', return_value=[stored]) as cache:
        result = asyncio.run(client.load_future_duties())
    assert result[0].assignments == duty.assignments
    cache.assert_called_once_with('future_duties_v3_exclude_absences')


def test_pdf_many_parts_wraps_text(tmp_path):
    from src.pdf import export_to_pdf
    assert export_to_pdf([parse_personal_duties(payload())[0]], str(tmp_path / 'parts.pdf'))


def test_twenty_allocations_have_no_two_or_three_part_limit():
    data = payload(); row = data['data'][0]
    row['allocationInfo'] = {str(i): ['SEW', 'Demo '+str(i), str(1000+i)+' RTW'] for i in range(20)}
    row['attendances'] = [dict(guid=str(i), begin='2030-01-20T%02d:%02d:00Z'%(5+i//2, 30*(i%2)),
        end='2030-01-20T%02d:%02d:00Z'%(5+(i+1)//2, 30*((i+1)%2))) for i in range(20)]
    duty = parse_personal_duties(data)[0]
    assert len(duty.assignments) == 20
    assert duty.duration_hours == 12


def test_nonlist_attendances_do_not_break_legacy_duties():
    for value in ['null', '3', '{}', '[null, 3, {}]']:
        data = payload(); data['data'][0]['attendances'] = value
        duty = parse_personal_duties(data)[0]
        assert duty.duration_hours == 12 and not duty.is_cancelled
        assert not duty.assignments
