[ ![Logo](../_static/logo.svg) ](../index.html)

# [The Linux Kernel](../index.html)

6.10.0

### Quick search

### Contents

  * [Development process](../process/development-process.html)
  * [Submitting patches](../process/submitting-patches.html)
  * [Code of conduct](../process/code-of-conduct.html)
  * [Maintainer handbook](../maintainer/index.html)
  * [All development-process docs](../process/index.html)

  * [Core API](../core-api/index.html)
  * [Driver APIs](../driver-api/index.html)
  * [Subsystems](../subsystem-apis.html)
    * [Core subsystems](../subsystem-apis.html#core-subsystems)
    * [Human interfaces](../subsystem-apis.html#human-interfaces)
    * [Networking interfaces](../subsystem-apis.html#networking-interfaces)
      * [Networking](../networking/index.html)
      * [NetLabel](../netlabel/index.html)
      * [InfiniBand](index.html)
      * [ISDN](../isdn/index.html)
      * [MHI](../mhi/index.html)
    * [Storage interfaces](../subsystem-apis.html#storage-interfaces)
    * [Other subsystems](../subsystem-apis.html#other-subsystems)
  * [Locking](../locking/index.html)

  * [Licensing rules](../process/license-rules.html)
  * [Writing documentation](../doc-guide/index.html)
  * [Development tools](../dev-tools/index.html)
  * [Testing guide](../dev-tools/testing-overview.html)
  * [Hacking guide](../kernel-hacking/index.html)
  * [Tracing](../trace/index.html)
  * [Fault injection](../fault-injection/index.html)
  * [Livepatching](../livepatch/index.html)
  * [Rust](../rust/index.html)

  * [Administration](../admin-guide/index.html)
  * [Build system](../kbuild/index.html)
  * [Reporting issues](../admin-guide/reporting-issues.html)
  * [Userspace tools](../tools/index.html)
  * [Userspace API](../userspace-api/index.html)

  * [Firmware](../firmware-guide/index.html)
  * [Firmware and Devicetree](../devicetree/index.html)

  * [CPU architectures](../arch/index.html)

  * [Unsorted documentation](../staging/index.html)

  * [Translations](../translations/index.html)

### This Page

  * [Show Source](../_sources/infiniband/user_verbs.rst.txt)

English

  * [Chinese (Simplified)](../translations/zh_CN/infiniband/user_verbs.html)

# Userspace verbs access¶

> The ib_uverbs module, built by enabling CONFIG_INFINIBAND_USER_VERBS,
> enables direct userspace access to IB hardware via “verbs,” as described in
> chapter 11 of the InfiniBand Architecture Specification.
>
> To use the verbs, the libibverbs library, available from
> <https://github.com/linux-rdma/rdma-core>, is required. libibverbs contains
> a device-independent API for using the ib_uverbs interface. libibverbs also
> requires appropriate device-dependent kernel and userspace driver for your
> InfiniBand hardware. For example, to use a Mellanox HCA, you will need the
> ib_mthca kernel module and the libmthca userspace driver be installed.

## User-kernel communication¶

> Userspace communicates with the kernel for slow path, resource management
> operations via the /dev/infiniband/uverbsN character devices. Fast path
> operations are typically performed by writing directly to hardware registers
> mmap()ed into userspace, with no system call or context switch into the
> kernel.
>
> Commands are sent to the kernel via write()s on these device files. The ABI
> is defined in drivers/infiniband/include/ib_user_verbs.h. The structs for
> commands that require a response from the kernel contain a 64-bit field used
> to pass a pointer to an output buffer. Status is returned to userspace as
> the return value of the write() system call.

## Resource management¶

> Since creation and destruction of all IB resources is done by commands
> passed through a file descriptor, the kernel can keep track of which
> resources are attached to a given userspace context. The ib_uverbs module
> maintains idr tables that are used to translate between kernel pointers and
> opaque userspace handles, so that kernel pointers are never exposed to
> userspace and userspace cannot trick the kernel into following a bogus
> pointer.
>
> This also allows the kernel to clean up when a process exits and prevent one
> process from touching another process’s resources.

## Memory pinning¶

> Direct userspace I/O requires that memory regions that are potential I/O
> targets be kept resident at the same physical address. The ib_uverbs module
> manages pinning and unpinning memory regions via get_user_pages() and
> put_page() calls. It also accounts for the amount of memory pinned in the
> process’s pinned_vm, and checks that unprivileged processes do not exceed
> their RLIMIT_MEMLOCK limit.
>
> Pages that are pinned multiple times are counted each time they are pinned,
> so the value of pinned_vm may be an overestimate of the number of pages
> pinned by a process.

## /dev files¶

> To create the appropriate character device files automatically with udev, a
> rule like:
>  
>  
>     KERNEL=="uverbs*", NAME="infiniband/%k"
>  
>
> can be used. This will create device nodes named:
>  
>  
>     /dev/infiniband/uverbs0
>  
>
> and so on. Since the InfiniBand userspace verbs should be safe for use by
> non-privileged processes, it may be useful to add an appropriate MODE or
> GROUP to the udev rule.

(C)The kernel development community. | Powered by [Sphinx 5.0.1](http://sphinx-doc.org/) & [Alabaster 0.7.12](https://github.com/bitprophet/alabaster) | [Page source](../_sources/infiniband/user_verbs.rst.txt)

