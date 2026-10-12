"""Tests for parsing hierarchy dumps and matching labels."""

from court_booker.screen import Match, Node, Screen

DUMP = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node content-desc="" bounds="[0,0][540,1600]" clickable="false">
    <node content-desc="18:00 - 19:00&#10;Hết chỗ" bounds="[38,1178][263,1262]" clickable="true" />
    <node content-desc="Tiếp tục" bounds="[35,1490][505,1584]" clickable="true" />
    <node content-desc="Xác nhận" bounds="[35,1490][505,1584]" clickable="false" />
    <node content-desc="no bounds" />
  </node>
</hierarchy>"""


def test_parse_keeps_labels_bounds_and_clickable():
    screen = Screen.parse(DUMP)

    assert [n.desc for n in screen.nodes] == ["", "18:00 - 19:00\nHết chỗ", "Tiếp tục", "Xác nhận"]
    assert screen.nodes[1].box == (38, 1178, 263, 1262)
    assert screen.nodes[2].clickable is True
    assert screen.nodes[3].clickable is False


def test_size_is_read_from_the_dump():
    assert Screen.parse(DUMP).size == (540, 1600)
    assert Screen([]).size == (0, 0)


def test_match_criteria():
    slot = Node("18:00 - 19:00\nHết chỗ", (38, 1178, 263, 1262), True)

    assert Match(prefix="18:00 - 19:00")(slot)
    assert Match(contains="Hết chỗ")(slot)
    assert Match(pattern=r"\d{2}:\d{2} - \d{2}:\d{2}.*")(slot)
    assert not Match(pattern=r"\d{2}:\d{2}")(slot)
    assert not Match(desc="18:00 - 19:00")(slot)
    assert not Match(prefix="18:00 - 19:00", clickable=False)(slot)


def test_find_respects_clickable():
    screen = Screen.parse(DUMP)

    assert screen.find(Match(desc="Xác nhận", clickable=True)) is None
    assert screen.find(Match(desc="Tiếp tục")).center == (270, 1537)
    assert len(screen.find_all(Match(prefix="18:00"))) == 1


def test_describe_lists_labelled_and_clickable_elements():
    screen = Screen.parse(DUMP)
    screen.nodes.append(Node("", (480, 180, 520, 220), True))

    assert screen.describe() == [
        "[38,1178][263,1262] clickable '18:00 - 19:00\\nHết chỗ'",
        "[35,1490][505,1584] clickable 'Tiếp tục'",
        "[35,1490][505,1584] 'Xác nhận'",
        "[480,180][520,220] clickable ''",
    ]
    assert Screen([]).describe() == []
