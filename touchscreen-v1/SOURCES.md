# Sources and licences

This bundle supplements the existing Redmi9T-Native-Linux v8b build. It does not contain a complete Linux tree, compiler, Alpine SDK, rootfs or personal firmware.

- `nvt-spi.c`, `nvt-frame.c/.h`: GPL-2.0-only, protocol/decoder derived from Xiaomi sources and the existing project decoder. Linux text included in `sources/linux/GPL-2.0`.
- `sources/xiaomi/NT36672A/`: unmodified MiCode lime-q-oss files from commit `02ca1a919564a9b176a79cce09c40977f833e9ac`. Their original headers apply. https://github.com/MiCode/Xiaomi_Kernel_OpenSource/tree/02ca1a919564a9b176a79cce09c40977f833e9ac/drivers/input/touchscreen/NT36672A
- `sources/xiaomi/spi-geni-qcom.c`: same Xiaomi commit, unmodified comparison source; original GPL header retained.
- `sources/linux/spi-geni-qcom.c`: unmodified comparison/build source from existing Linux commit `05441d697f7f9a927264f4058cbbc6a03dfcac9d`. Existing v8b kernel-out/Module.symvers and .config are required for the external-module build. `geni-stock-delay.patch` is a private local change; no upstream approval is claimed.
- `sources/freerdp/FreeRDP-3.32.2.tar.gz`: unmodified official release source archive, https://github.com/FreeRDP/FreeRDP/releases/tag/3.32.2 . FreeRDP/UWAC original licence files are inside the source archive (Apache-2.0). `freerdp-touch.patch` and build-client.sh describe the two local changes. The compiled client additionally uses the already distributed v2.1 FreeRDP runtime libraries.
- `touch-pointer.c`: MIT, see its SPDX header and `LICENSE-MIT`. It deliberately provides pointer emulation only.

Build paths refer to the existing WSL project/ARM64 SDK. No install/flash/load command is run by packaging. All included files have SHA-256 and size in the bundle manifest. Historical device evidence is distinguished from live read-only evidence in TOUCHSCREEN_V1_RESULTS.md.
