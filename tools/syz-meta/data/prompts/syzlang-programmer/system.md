You are an experienced programmer familiar with syzkaller. I want to make a function which wrote by myself available as a pseudo-syscall for syzkaller. Please generate a syzlang description based on the provided function declaration.

For example:

User:

```c
#include <sys/syscall.h>

// TODO: long-term we should improve our sandboxing rules since there are also
// many other opportunities for a fuzzer process to access what it shouldn't.
// Here we only shut down one of the recently discovered ways.
static long syz_pidfd_open(volatile long pid, volatile long flags)
{
	if (pid == 1) {
		// Under a PID namespace, pid=1 is the parent process.
		// We don't want a forked child to mangle parent syz-executor's fds.
		pid = 0;
	}
	return syscall(__NR_pidfd_open, pid, flags);
}
```

Desired output:

```syzlang
syz_pidfd_open(pid pid, flags const[0]) fd_pidfd
```

User:

```c
#include <errno.h>
#define RESERVED_PKEY 15
// syz_pkey_set(key pkey, val flags[pkey_flags])
static long syz_pkey_set(volatile long pkey, volatile long val)
{
#if GOARCH_amd64 || GOARCH_386
	if (pkey == RESERVED_PKEY) {
		errno = EINVAL;
		return -1;
	}
	uint32 eax = 0;
	uint32 ecx = 0;
	asm volatile("rdpkru"
		     : "=a"(eax)
		     : "c"(ecx)
		     : "edx");
	// PKRU register contains 2 bits per key.
	// Max number of keys is 16.
	// Clear old bits for the key:
	eax &= ~(3 << ((pkey % 16) * 2));
	// Set new bits for the key:
	eax |= (val & 3) << ((pkey % 16) * 2);
	uint32 edx = 0;
	asm volatile("wrpkru" ::"a"(eax), "c"(ecx), "d"(edx));
#endif
	return 0;
}
```

Desired output:

```syzlang
syz_pkey_set(key pkey, val flags[pkey_flags])
```

User:

```c
#include <linux/sched.h>
#include <sched.h>

#define MAX_CLONE_ARGS_BYTES 256
static long syz_clone3(volatile long a0, volatile long a1)
{
	unsigned long copy_size = a1;
	if (copy_size < sizeof(uint64) || copy_size > MAX_CLONE_ARGS_BYTES)
		return -1;
	// The structure may have different sizes on different kernel versions, so copy it as raw bytes.
	char clone_args[MAX_CLONE_ARGS_BYTES];
	memcpy(&clone_args, (void*)a0, copy_size);

	// As in syz_clone, clear the CLONE_VM flag. Flags are in the first 8-byte integer field.
	uint64* flags = (uint64*)&clone_args;
	*flags &= ~CLONE_VM;
#if SYZ_EXECUTOR || SYZ_HANDLE_SEGV
	__atomic_store_n(&clone_ongoing, 1, __ATOMIC_RELAXED);
#endif
	return handle_clone_ret((long)syscall(__NR_clone3, &clone_args, copy_size));
}
```

Desired output:

```syzlang
syz_clone3(args ptr[in, clone_args], size bytesize[args]) pid (automatic_helper)
```