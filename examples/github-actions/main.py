import sys


def python_version() -> str:
    """Return the running interpreter's version as ``major.minor``."""
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def main() -> None:
    print(f"Hello from Python {python_version()}!")


if __name__ == "__main__":
    main()
