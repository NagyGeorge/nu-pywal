"""wal - setup.py"""

import os

import setuptools

# Check Python version first
LONG_DESC = open("README.md").read()


# Get version from __init__.py without importing the module
def get_version():
    version_file = os.path.join(os.path.dirname(__file__), "pywal", "settings.py")
    with open(version_file) as f:
        for line in f:
            if line.startswith("__version__"):
                return line.split('"')[1]
    raise RuntimeError("Unable to find version string.")


VERSION = get_version()
DOWNLOAD = f"https://github.com/dylanaraps/pywal/archive/{VERSION}.tar.gz"

setuptools.setup(
    name="pywal",
    version=VERSION,
    author="Dylan Araps",
    author_email="dylan.araps@gmail.com",
    description="Generate and change color-schemes on the fly",
    long_description_content_type="text/markdown",
    long_description=LONG_DESC,
    keywords="wal colorscheme terminal-emulators changing-colorschemes",
    license="MIT",
    url="https://github.com/dylanaraps/pywal",
    download_url=DOWNLOAD,
    classifiers=[
        "Environment :: X11 Applications",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    packages=["pywal"],
    entry_points={"console_scripts": ["wal=pywal.__main__:main"]},
    python_requires=">=3.8",
    test_suite="tests",
    include_package_data=True,
    zip_safe=False,
)
