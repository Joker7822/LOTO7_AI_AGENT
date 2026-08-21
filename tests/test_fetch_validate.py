import datetime as dt
from fetch_validate import expected_new_round, parse_mizuho, validate_row


def test_expected_round_friday_20_jst():
    before={"回別":"第690回","抽せん日":"2026-08-14"}
    now=dt.datetime(2026,8,21,20,0,tzinfo=dt.timezone(dt.timedelta(hours=9)))
    assert expected_new_round(before,now)==(691,"2026-08-21")


def test_validate_latest_numbers():
    got=validate_row({"回別":"第691回","抽せん日":"2026-08-21","本数字":"01 02 03 04 05 06 07","ボーナス数字":"08 09"})
    assert got["round"]==691 and got["main"][-1]==7


def test_parse_mizuho_synthetic():
    html="""<html><body>ロト7 第691回 抽せん日 2026年8月21日 本数字 01 02 03 04 05 06 07 ボーナス数字 08 09 等級</body></html>"""
    got=parse_mizuho(html,691)
    assert got["round"]==691
    assert got["main"]==[1,2,3,4,5,6,7]
    assert got["bonus"]==[8,9]
