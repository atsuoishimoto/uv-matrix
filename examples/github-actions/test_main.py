from main import python_version


def test_python_version_format():
    major, minor = python_version().split(".")
    assert major.isdigit() and minor.isdigit()
