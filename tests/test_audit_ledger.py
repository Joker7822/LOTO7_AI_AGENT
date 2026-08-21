from audit_ledger import grade_ticket


def test_loto7_grades():
    main=(1,2,3,4,5,6,7); bonus=(8,9)
    assert grade_ticket((1,2,3,4,5,6,7),main,bonus)[2]=="1等"
    assert grade_ticket((1,2,3,4,5,6,8),main,bonus)[2]=="2等"
    assert grade_ticket((1,2,3,4,5,6,10),main,bonus)[2]=="3等"
    assert grade_ticket((1,2,3,4,5,10,11),main,bonus)[2]=="4等"
    assert grade_ticket((1,2,3,4,10,11,12),main,bonus)[2]=="5等"
    assert grade_ticket((1,2,3,8,10,11,12),main,bonus)[2]=="6等"
    assert grade_ticket((1,2,3,10,11,12,13),main,bonus)[2]=="はずれ"
