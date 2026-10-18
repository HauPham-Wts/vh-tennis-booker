"""Tests for the agent build tool; no SDK, JDK or build runs."""

import importlib.util
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "build_agent.py"
_spec = importlib.util.spec_from_file_location("build_agent", TOOL)
build_agent = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_agent)


def test_version_code_grows_with_the_version():
    assert build_agent.version_code("0.7.0") == 700
    assert build_agent.version_code("0.8.0") == 800
    assert build_agent.version_code("0.10.2") == 1002
    assert build_agent.version_code("1.0.0") == 10000


def test_version_code_rejects_a_non_version():
    with pytest.raises(ValueError):
        build_agent.version_code("dev")


def test_the_apk_shares_the_package_version():
    from court_booker import __version__

    assert build_agent.package_version() == __version__


def test_sdk_comes_from_the_environment_first():
    assert build_agent.find_sdk({"ANDROID_HOME": "a", "ANDROID_SDK_ROOT": "b"}) == Path("a")
    assert build_agent.find_sdk({"ANDROID_SDK_ROOT": "b"}) == Path("b")
    assert build_agent.find_sdk({}) == build_agent.DEFAULT_SDK


def test_build_tools_are_scripts_or_programs_by_platform():
    sdk = Path("sdk")
    tools = sdk / "build-tools" / build_agent.BUILD_TOOLS
    assert build_agent.sdk_tool(sdk, "d8", windows=True) == tools / "d8.bat"
    assert build_agent.sdk_tool(sdk, "aapt2", windows=True) == tools / "aapt2.exe"
    assert build_agent.sdk_tool(sdk, "d8", windows=False) == tools / "d8"
    assert build_agent.sdk_tool(sdk, "aapt2", windows=False) == tools / "aapt2"


def test_jdk_tools_come_from_java_home():
    tool = build_agent.jdk_tool("javac", {"JAVA_HOME": "jdk"}, windows=True)
    assert Path(tool) == Path("jdk") / "bin" / "javac.exe"
