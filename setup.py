import setuptools

__version__ = "0.8.0"
__author__ = "Denis Mulyalin"

with open("README.md", "r") as f:
    README = f.read()

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
    extras_require={},
    classifiers=[
        "Topic :: Utilities",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.6",
    install_requires=["nornir==3.*"],
    entry_points="""
    [nornir.plugins.inventory]
    DictInventory=nornir_salt:DictInventory

    [nornir.plugins.runners]
    QueueRunner=nornir_salt:QueueRunner
    RetryRunner=nornir_salt:RetryRunner

    [nornir.plugins.connections]
    ncclient=nornir_salt:NcclientPlugin
    http=nornir_salt:HTTPPlugin
    pygnmi=nornir_salt:PyGNMIPlugin
    ConnectionsPool=nornir_salt:ConnectionsPool
    pyats=nornir_salt:PyATSUnicon
    """,
)
