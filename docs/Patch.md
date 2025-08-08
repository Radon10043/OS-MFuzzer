# Patch description

- release.patch: Only add support for metamorphic fuzzing
- debug.patch: On the basis of meta.patch, modify Makefile for debugging
- create-image.patch: build a disk image without `mount` and `umount`, which can be used in `docker build`
- cuttlefish.patch: patch google/android-cuttlefish, preserve `http_proxy` and `https_proxy` during `tools/buildutils/build-packages.sh` running
- offline.patch: add support for syzkaller or SyzMeta offline running (if they are built first time, they will donwload mockery from internet automatically).