"""알림(Alert) 엔드포인트 테스트.

mock 가격소스는 1만~약11만원을 돌려주므로, 목표가를 아주 높게(lte) 잡으면
수동 체크에서 조건이 항상 충족되어 알림이 생성된다.
"""


def _watch_that_triggers(client, auth_headers):
    return client.post(
        "/watches",
        headers=auth_headers,
        json={"query": "무선 이어폰", "target_price": 10_000_000, "comparison": "lte"},
    ).json()["id"]


def test_alerts_empty_initially(client, auth_headers):
    assert client.get("/alerts", headers=auth_headers).json() == []


def test_check_creates_alert_then_listed(client, auth_headers):
    wid = _watch_that_triggers(client, auth_headers)
    chk = client.post(f"/watches/{wid}/check", headers=auth_headers)
    assert chk.status_code == 200
    body = chk.json()
    assert body["checked"] is True
    assert body["condition_met"] is True
    assert body["alert"] is not None

    alerts = client.get("/alerts", headers=auth_headers).json()
    assert len(alerts) >= 1
    assert alerts[0]["watch_id"] == wid
    assert alerts[0]["message"]  # AI/템플릿 문구가 채워짐


def test_delete_single_alert(client, auth_headers):
    wid = _watch_that_triggers(client, auth_headers)
    client.post(f"/watches/{wid}/check", headers=auth_headers)
    alert_id = client.get("/alerts", headers=auth_headers).json()[0]["id"]

    assert client.delete(f"/alerts/{alert_id}", headers=auth_headers).status_code == 204
    assert all(a["id"] != alert_id for a in client.get("/alerts", headers=auth_headers).json())


def test_clear_all_alerts(client, auth_headers):
    wid = _watch_that_triggers(client, auth_headers)
    client.post(f"/watches/{wid}/check", headers=auth_headers)
    assert len(client.get("/alerts", headers=auth_headers).json()) >= 1

    assert client.delete("/alerts", headers=auth_headers).status_code == 204
    assert client.get("/alerts", headers=auth_headers).json() == []
