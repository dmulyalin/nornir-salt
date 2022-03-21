import setuptools

__version__ = "0.10.1"
__author__ = "Denis Mulyalin <d.mulyalin@gmail.com>"

with open("README.md", "r", encoding="utf8") as f:
    README = f.read()

with open("requirements.txt", "r", encoding="utf8") as f:
    REQUIREMENTS = [i for i in f.read().splitlines() if i.strip()]

with open("requirements-dev.txt", "r", encoding="utf8") as f:
    REQUIREMENTS_DEV = [i for i in f.read().splitlines() if i.strip()]

with open("requirements-prodmax.txt", "r", encoding="utf8") as f:
    REQUIREMENTS_PRODMAX = [i for i in f.read().splitlines() if i.strip()]

with open("requirements-prodmin.txt", "r", encoding="utf8") as f:
    REQUIREMENTS_PRODMIN = [i for i in f.read().splitlines() if i.strip()]

setuptools.setup(
    name="nornir_salt",
    version=__version__,
    author=__author__,
    author_email="d.mulyalin@gmail.com",
    description="Nornir plugins used with SALTSTACK",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/dmulyalin/nornir-salt",
    packages=setuptools.find_packages(),
    extras_require={
        "dev": REQUIREMENTS_DEV + REQUIREMENTS_PRODMAX,
        "prodmax": REQUIREMENTS_PRODMAX,
        "prodmin": REQUIREMENTS_PRODMIN,
    },
    classifiers=[
        "Topic :: Utilities",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.6",
    install_requires=REQUIREMENTS,
    entry_points="""
    [nornir.plugins.inventory]
    DictInventory=nornir_salt.plugins.inventory:DictInventory

    [nornir.plugins.runners]
    QueueRunner=nornir_salt.plugins.runners:QueueRunner
    RetryRunner=nornir_salt.plugins.runners:RetryRunner

    [nornir.plugins.connections]
    ncclient=nornir_salt.plugins.connections:NcclientPlugin
    http=nornir_salt.plugins.connections:HTTPPlugin
    pygnmi=nornir_salt.plugins.connections:PyGNMIPlugin
    ConnectionsPool=nornir_salt.plugins.connections:ConnectionsPool
    pyats=nornir_salt.plugins.connections:PyATSUnicon
    """,
    data_files=[('', ['requirements.txt', 'requirements-dev.txt', 'requirements-prodmax.txt', 'requirements-prodmin.txt'])]
)
