"""The committed driver APK against its sources; no SDK, JDK or build runs."""

import importlib.util
import json
import zipfile
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "build_driver.py"
_spec = importlib.util.spec_from_file_location("build_driver", TOOL)
build_driver = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_driver)


def test_the_committed_apk_is_built_from_the_sources():
    record = json.loads((build_driver.ASSETS / build_driver.HASH_NAME).read_text("utf-8"))

    # Changed sources need `python tools/build_driver.py` and the new APK committed.
    assert record["sources_sha256"] == build_driver.sources_hash()


def test_the_committed_apk_holds_code_and_a_manifest():
    with zipfile.ZipFile(build_driver.ASSETS / build_driver.APK_NAME) as apk:
        names = apk.namelist()

    assert "AndroidManifest.xml" in names
    assert "classes.dex" in names


def test_the_sources_hash_covers_paths_and_contents(tmp_path):
    (tmp_path / "a.txt").write_bytes(b"one")
    first = build_driver.sources_hash(tmp_path)
    (tmp_path / "a.txt").write_bytes(b"two")
    second = build_driver.sources_hash(tmp_path)
    (tmp_path / "a.txt").rename(tmp_path / "b.txt")

    assert len({first, second, build_driver.sources_hash(tmp_path)}) == 3
