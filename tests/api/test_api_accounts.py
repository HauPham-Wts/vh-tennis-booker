from court_booker import history
from court_booker.events import EventKind, Reporter


def test_no_account_told_its_subdivision_yet(client):
    assert client.get("/api/accounts").json() == []


def test_each_account_comes_with_the_subdivision_it_told_last(client, context):
    store = history.History(history.connect(context.data.database))
    report = Reporter(store)
    report(EventKind.RUN_STARTED, trigger="dry_run", dry_run=True, version="0.16.0", device=1)
    report(EventKind.ACCOUNT_SUBDIVISION, subdivision="bs")
    report(EventKind.RUN_STARTED, trigger="dry_run", dry_run=True, version="0.16.0", device=0)
    report(EventKind.ACCOUNT_SUBDIVISION, subdivision="khu-b")  # of a later catalog
    store.close()

    accounts = client.get("/api/accounts").json()

    assert [(item["device"], item["subdivision"]) for item in accounts] == [(1, "bs")]
