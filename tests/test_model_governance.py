from loto7_v2_runner import promotion_decision


def ev(score60,max60,score120,max120):
    return {"windows":{
      "60":{"draws":60,"model":{"score":score60,"max_hits":max60}},
      "120":{"draws":120,"model":{"score":score120,"max_hits":max120}},
    }}


def test_challenger_must_win_both_windows():
    champ=ev(2.0,2.1,2.0,2.1)
    good=ev(2.05,2.11,2.06,2.12)
    bad=ev(2.10,2.2,1.99,2.2)
    assert promotion_decision(champ,good)[0] is True
    assert promotion_decision(champ,bad)[0] is False
