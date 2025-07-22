.PHONY: patch restore extract_patch

patch:
	@echo -n "Applying patch to syzkaller ... "
	@git -C syzkaller apply $(PWD)/SyzMeta.patch
	@echo "OK."

restore:
	@echo -n "Restoring syzkaller ... "
	@git -C syzkaller restore .
	@git -C syzkaller clean -fd
	@echo "OK."

extract_patch:
	@echo -n "Extracting patch from syzkaller ... "
	@git -C syzkaller diff > SyzMeta.patch
	@echo "OK."