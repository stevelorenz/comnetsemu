# CHANGELOG

CHANGELOG is added until Beta v0.1.5, notable changes after this version MUST be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
And this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

-   Support connecting Docker hosts running inside Vagrant VM to external network.
-   Better logging of application DockerContainer.

### Changed

-   Current DockerHost implementation will be refactored to support better docker_args.

## v0.1.5 - 2019-08-30

### Added

-   Use the [override.py](./comnetsemu/overrides.py) approach to override `makeIntfPair` in `mininet.util`.
    This approach replaces the patch-based approach in v0.1.4.

### Changed

-   Use relative path for ComNetsEmu's dependency directory (default name: comnetsemu_dependencies).
    The installer script uses the directory containing the comnetsemu's source code as TOP_DIR.
    All source dependencies are downloaded/managed into "$TOP_DIR/comnetsemu_dependencies".
