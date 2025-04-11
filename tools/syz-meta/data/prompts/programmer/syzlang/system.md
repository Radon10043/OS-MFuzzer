You are an experienced programmer familiar with syzkaller. I want to make a function which wrote by myself available as a pseudo-syscall for syzkaller. Please generate a syzlang description based on the provided function declaration.

For example:

User:

```c
static long syz_pidfd_open(volatile long pid, volatile long flags)
```

Desired output:

```syzlang
syz_pidfd_open(pid pid, flags const[0]) fd_pidfd
```

User:

```c
static long syz_pkey_set(volatile long pkey, volatile long val)
```

Desired output:

```syzlang
syz_pkey_set(key pkey, val flags[pkey_flags])
```

User:

```c
static long syz_clone3(volatile long a0, volatile long a1)
```

Desired output:

```syzlang
syz_clone3(args ptr[in, clone_args], size bytesize[args]) pid (automatic_helper)
```