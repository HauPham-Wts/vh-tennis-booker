"""Build the on-device agent APK with the Android SDK tools alone (no Gradle).

Needs a JDK 17 or later (JAVA_HOME, else javac on PATH) and the Android SDK packages
"platforms;android-35" and "build-tools;35.0.0" (ANDROID_HOME, ANDROID_SDK_ROOT, else
D:/Tools/android-sdk). The APK takes its version from the Python package and is signed with
the Android debug key (~/.android/debug.keystore, created when missing, as Android Studio
does), so every build on a machine can update the agent already installed.

Usage:
    python tools/build_agent.py        # writes android/build/court-agent.apk
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SOURCES = REPO / "android" / "app" / "src" / "main"
OUT = REPO / "android" / "build"
APK_NAME = "court-agent.apk"
DEFAULT_SDK = Path("D:/Tools/android-sdk")
PLATFORM = "android-35"
BUILD_TOOLS = "35.0.0"
MIN_SDK = 30
TARGET_SDK = 35
JAVA_RELEASE = "11"
KEYSTORE = Path.home() / ".android" / "debug.keystore"
KEY_ALIAS = "androiddebugkey"
KEY_PASSWORD = "android"
# Build tools that are batch files on Windows and shell scripts elsewhere.
SCRIPT_TOOLS = {"d8", "apksigner"}


def package_version(repo: Path = REPO) -> str:
    """Return ``__version__`` of the Python package, which the APK shares."""
    text = (repo / "src" / "court_booker" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__ = "([^"]+)"', text, re.MULTILINE)
    if match is None:
        raise SystemExit("No __version__ in src/court_booker/__init__.py")
    return match.group(1)


def version_code(version: str) -> int:
    """Return Android's increasing version number for ``version``: 0.8.0 is 800."""
    match = re.match(r"(\d+)\.(\d+)\.(\d+)", version)
    if match is None:
        raise ValueError(f"Not a version: {version!r}")
    major, minor, patch = (int(part) for part in match.groups())
    return major * 10_000 + minor * 100 + patch


def find_sdk(environ: dict[str, str]) -> Path:
    """Return the Android SDK folder named by the environment, else the default one."""
    for name in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        if environ.get(name):
            return Path(environ[name])
    return DEFAULT_SDK


def sdk_tool(sdk: Path, name: str, windows: bool) -> Path:
    """Return the path of build tool ``name`` (aapt2, d8, zipalign, apksigner)."""
    suffix = (".bat" if name in SCRIPT_TOOLS else ".exe") if windows else ""
    return sdk / "build-tools" / BUILD_TOOLS / f"{name}{suffix}"


def jdk_tool(name: str, environ: dict[str, str], windows: bool) -> str:
    """Return the JDK tool ``name`` (javac, keytool) from JAVA_HOME, else from PATH."""
    if environ.get("JAVA_HOME"):
        return str(Path(environ["JAVA_HOME"]) / "bin" / (f"{name}.exe" if windows else name))
    found = shutil.which(name)
    if found is None:
        raise SystemExit(f"{name} not found: install a JDK 17 or later or set JAVA_HOME")
    return found


def run(command: list[object]) -> None:
    subprocess.run([str(part) for part in command], check=True)


def build(sdk: Path, environ: dict[str, str], windows: bool) -> Path:
    """Build the signed APK and return its path."""
    android_jar = sdk / "platforms" / PLATFORM / "android.jar"
    if not android_jar.exists():
        raise SystemExit(
            f"{android_jar} not found: install the SDK packages "
            f'"platforms;{PLATFORM}" and "build-tools;{BUILD_TOOLS}"'
        )
    version = package_version()
    work = OUT / "work"
    shutil.rmtree(work, ignore_errors=True)
    (work / "classes").mkdir(parents=True)
    (work / "dex").mkdir()

    def tool(name: str) -> Path:
        return sdk_tool(sdk, name, windows)

    run([tool("aapt2"), "compile", "--dir", SOURCES / "res", "-o", work / "res.zip"])
    run([
        tool("aapt2"), "link", "-I", android_jar, "--manifest", SOURCES / "AndroidManifest.xml",
        "--min-sdk-version", MIN_SDK, "--target-sdk-version", TARGET_SDK,
        "--version-code", version_code(version), "--version-name", version,
        "-o", work / "unsigned.apk", work / "res.zip",
    ])  # fmt: skip
    sources = sorted((SOURCES / "java").rglob("*.java"))
    run([
        jdk_tool("javac", environ, windows), "-source", JAVA_RELEASE, "-target", JAVA_RELEASE,
        "-Xlint:-options", "-classpath", android_jar, "-d", work / "classes", *sources,
    ])  # fmt: skip
    classes = sorted((work / "classes").rglob("*.class"))
    dex = work / "dex"
    run([tool("d8"), "--lib", android_jar, "--min-api", MIN_SDK, "--output", dex, *classes])
    with zipfile.ZipFile(work / "unsigned.apk", "a") as apk:
        apk.write(work / "dex" / "classes.dex", "classes.dex")
    run([tool("zipalign"), "-p", "-f", "4", work / "unsigned.apk", work / "aligned.apk"])
    if not KEYSTORE.exists():
        KEYSTORE.parent.mkdir(parents=True, exist_ok=True)
        run([
            jdk_tool("keytool", environ, windows), "-genkeypair", "-keystore", KEYSTORE,
            "-alias", KEY_ALIAS, "-storepass", KEY_PASSWORD, "-keypass", KEY_PASSWORD,
            "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000",
            "-dname", "CN=Android Debug,O=Android,C=US",
        ])  # fmt: skip
    apk = OUT / APK_NAME
    run([
        tool("apksigner"), "sign", "--ks", KEYSTORE, "--ks-key-alias", KEY_ALIAS,
        "--ks-pass", f"pass:{KEY_PASSWORD}", "--key-pass", f"pass:{KEY_PASSWORD}",
        "--v4-signing-enabled", "false", "--out", apk, work / "aligned.apk",
    ])  # fmt: skip
    shutil.rmtree(work)
    return apk


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sdk", type=Path, help="Android SDK folder (default: see above)")
    args = parser.parse_args()
    environ = dict(os.environ)
    apk = build(args.sdk or find_sdk(environ), environ, windows=sys.platform == "win32")
    print(f"Built {apk.relative_to(REPO)} ({apk.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
