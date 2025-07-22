PATCH ?=
OUT ?=

.PHONY: patch restore extract_patch

patch:
ifneq ($(origin PATCH), command line)
	$(error Please specify PATCH (e.g. make PATCH=patch/meta.patch patch))
endif
	@echo -n "Applying patch to syzkaller ... "
	@git -C syzkaller apply $(abspath $(PATCH))
	@echo "OK."

restore:
	@echo -n "Restoring syzkaller ... "
	@git -C syzkaller restore . 2>&1 > /dev/null
	@git -C syzkaller clean -fd 2>&1 > /dev/null
	@echo "OK."

extract_patch:
ifneq ($(origin OUT), command line)
	$(error OUT is not set, please provide a path for saveing patch (e.g. make OUT=patch/xxx.patch extract_patch))
endif
	@echo -n "Extracting patch from syzkaller ... "
	@git -C syzkaller add --all
	@git -C syzkaller diff --staged > $(abspath $(OUT))
	@git -C syzkaller reset 2>&1 > /dev/null
	@echo "OK."