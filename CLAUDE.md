# Start here — Redmi9T-Native-Linux

Continue the existing project. Do not restart the Linux/GNOME port. The owner requested a compact transfer of the main work, not every old binary or log.

Read `handoff/START_HERE.md`, then `PROJECT_CHECKPOINT.md`, `TOUCHSCREEN_STAGE1_FINAL.md` and `TOUCHSCREEN_FIRST_LIVE_RESULTS.md`.

Current focus: the built-in Novatek NT36672A touchscreen, then finger input into the already working GNOME physical-LCD chain. GJS shutdown warnings are known and lower priority.

The main original workspace and large validated images remain on the owner's PC. Their exact locations and SHA-256 are in `handoff/LOCAL_LARGE_ARTIFACTS.json`. Do not overwrite them.

Do not automatically run flashing/reboot/hardware-test scripts from this repository. Ask the owner before a new live experiment. Never change UFS/GPT/boot/recovery/dtbo/vbmeta, PMIC, LCD supplies or panel initialization as part of routine preparation. MODULE_UNLOAD is disabled; do not assume rmmod works.

The old 63,732-byte CS1 DTB is revoked for active use. Runtime CS0 was established from stock source and the saved TWRP kernel. The most recent live session stopped before loading GENI/Novatek or issuing SPI commands: no real touch events have been obtained.

Important distinction: L9 `state=disabled` and `microvolts=1800000` are cached RPM-driver values, not physical voltage measurements. The previous agent declined SPI activation because electrical VDDIO was unverified; it did not establish that the physical rail is off. Review this evidence accurately rather than treating the cache as a hardware measurement.

Keep changes small. Answer the owner in concise Russian. Preserve the working v8b and GNOME Physical LCD v2.1.
