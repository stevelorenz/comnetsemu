# CHANGELOG

CHANGELOG is added until Beta v0.1.5, notable changes after this version MUST be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
And this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

## v0.1.8 - 2020-01-10

### Added

-  Add REST APIs in APPContainerManager.
-  Add two built-in examples ./examples/dockerhost_manage_appcontainer.py and ./examples/network_measurement.py .

### Changed

-   Change the version of Mininet to v2.3.0d6.
-   Add the built-in test container rebuilding in the update function of the install.sh.
-   Rename DockerContainer class in node.py to APPContainer.
-   Improve the documentation and parameter names in ./comnetsemu/net.py.

## v0.1.7 - 2019-12-13

### Added

-   Vagrant development environment with Libvirt as provider.

### Changed

-   Use APPContainerManager as the base class for all types of sibling containers including VNFContainer.

## v0.1.6 - 2019-11-05

### Added


### Changed

-   Current DockerHost implementation (in node.py) is refactored to support Docker-py v3.7.2 API.
    Builtin examples are also updated.

## v0.1.5 - 2019-08-30

### Added

-   Use the [override.py](./comnetsemu/overrides.py) approach to override `makeIntfPair` in `mininet.util`.
    This approach replaces the patch-based approach in v0.1.4.

### Changed

-   Use relative path for ComNetsEmu's dependency directory (default name: comnetsemu_dependencies).
    The installer script uses the directory containing the comnetsemu's source code as TOP_DIR.
    All source dependencies are downloaded/managed into "$TOP_DIR/comnetsemu_dependencies".
