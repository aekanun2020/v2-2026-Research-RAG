# Container provenance

Inspected official registry manifests on 2026-09-20 before building. No upstream Dockerfile or application source was copied. The project's [Dockerfile](../../Dockerfile) uses these unmodified images, pinned by multi-platform index digest:

| Component | Resolved version | Index digest | Original upstream |
|---|---|---|---|
| Python runtime with Debian Bookworm | Python 3.12.14, `python:3.12-slim-bookworm` | `sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e` | [Official image source commit 688a0b8](https://github.com/docker-library/python/tree/688a0b86bb44289df16a363e9f41d90514c1a5f9/3.12/slim-bookworm) |
| uv build tool | `ghcr.io/astral-sh/uv:0.12.17` | `sha256:10787c682e4184e4f290de1171fd4703dc63de99221f10fe1c99002ce7fa9acc` | [Astral uv 0.12.17](https://github.com/astral-sh/uv/tree/0.12.17) |

The actual build used Linux arm64. Python's arm64 manifest is `sha256:eb5be8e5b4d0a159c237946bbdd06356dda5d19c30fc4f7843e8046d3a590333`; uv's is `sha256:93041623aae9443bddacaee1a13aa0dc96bde323e4159ba57d0e9a47a947e0f0`. No amd64/Windows run is claimed.

Original notices were fetched before the build and preserved byte-for-byte: [Python image MIT](python-image-LICENSE), [uv MIT](uv-LICENSE-MIT), [uv Apache-2.0](uv-LICENSE-APACHE), with upstream URLs and SHA-256 in [notice inventory](notices.json). The runtime base retains Python's `/usr/local/lib/python3.12/LICENSE.txt` and Debian component copyright files under `/usr/share/doc/`. This is not a claim that every base-image component uses MIT. uv is only present in the build stage.

Python dependencies are installed from the pinned [lockfile](../../uv.lock) into a new Linux virtual environment. Their installed license notices remain in its distribution metadata; the project also includes the [captured notices](../licenses/) and [current Linux inventory](../dependencies.json) and [macOS development inventory](../dependencies-macos-0.2.0.json). The local `.venv`, `.env`, workspace, credentials and test evidence are excluded from the build context by [`.dockerignore`](../../.dockerignore). No credentials are embedded in image layers.

References: [Docker port publishing](https://docs.docker.com/engine/network/port-publishing/), [official uv image guidance](https://docs.astral.sh/uv/guides/integration/docker/). The 0.2.0 image additionally includes the pinned original CPU embedding model; see [model provenance](../embedding-model/README.md). The implementation adds local embedding retrieval and document/chunk management. Git staging is not an import commit; no commit or push has been performed in this task.
