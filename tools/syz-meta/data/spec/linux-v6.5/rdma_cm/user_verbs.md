# [The Linux Kernel](../index.html)

6.5.0

### Quick search

### Contents

  * [A guide to the Kernel Development Process](../process/development-process.html)
  * [Submitting patches: the essential guide to getting your code into the kernel](../process/submitting-patches.html)
  * [Code of conduct](../process/code-of-conduct.html)
  * [Kernel Maintainer Handbook](../maintainer/index.html)
  * [All development-process docs](../process/index.html)

  * [Core API Documentation](../core-api/index.html)
  * [Driver implementer's API guide](../driver-api/index.html)
  * [Kernel subsystem documentation](../subsystem-apis.html)
    * [Human interfaces](../subsystem-apis.html#human-interfaces)
    * [Storage interfaces](../subsystem-apis.html#storage-interfaces)
      * [Filesystems in the Linux kernel](../filesystems/index.html)
      * [Block](../block/index.html)
      * [CD-ROM](../cdrom/index.html)
      * [SCSI Subsystem](../scsi/index.html)
      * [TCM Virtual Device](../target/index.html)
      * [Driver implementer's API guide](../driver-api/index.html)
      * [Core API Documentation](../core-api/index.html)
      * [Locking](../locking/index.html)
      * [Accounting](../accounting/index.html)
      * [CPUFreq - CPU frequency and voltage scaling code in the Linux(TM) kernel](../cpu-freq/index.html)
      * [FPGA](../fpga/index.html)
      * [I2C/SMBus Subsystem](../i2c/index.html)
      * [Industrial I/O](../iio/index.html)
      * [ISDN](../isdn/index.html)
      * [InfiniBand](index.html)
      * [LEDs](../leds/index.html)
      * [NetLabel](../netlabel/index.html)
      * [Networking](../networking/index.html)
      * [PCMCIA](../pcmcia/index.html)
      * [Power Management](../power/index.html)
      * [Timers](../timers/index.html)
      * [Serial Peripheral Interface (SPI)](../spi/index.html)
      * [1-Wire Subsystem](../w1/index.html)
      * [Watchdog Support](../watchdog/index.html)
      * [Virtualization Support](../virt/index.html)
      * [Hardware Monitoring](../hwmon/index.html)
      * [Compute Accelerators](../accel/index.html)
      * [Security Documentation](../security/index.html)
      * [Crypto API](../crypto/index.html)
      * [Memory Management Documentation](../mm/index.html)
      * [BPF Documentation](../bpf/index.html)
      * [USB support](../usb/index.html)
      * [PCI Bus Subsystem](../PCI/index.html)
      * [Assorted Miscellaneous Devices Documentation](../misc-devices/index.html)
      * [Scheduler](../scheduler/index.html)
      * [MHI](../mhi/index.html)
      * [PECI Subsystem](../peci/index.html)
      * [WMI Subsystem](../wmi/index.html)
  * [Locking in the kernel](../locking/index.html)

  * [Linux kernel licensing rules](../process/license-rules.html)
  * [How to write kernel documentation](../doc-guide/index.html)
  * [Development tools for the kernel](../dev-tools/index.html)
  * [Kernel Testing Guide](../dev-tools/testing-overview.html)
  * [Kernel Hacking Guides](../kernel-hacking/index.html)
  * [Linux Tracing Technologies](../trace/index.html)
  * [fault-injection](../fault-injection/index.html)
  * [Kernel Livepatching](../livepatch/index.html)
  * [Rust](../rust/index.html)

  * [The Linux kernel user's and administrator's guide](../admin-guide/index.html)
  * [The kernel build system](../kbuild/index.html)
  * [Reporting issues](../admin-guide/reporting-issues.html)
  * [User-space tools](../tools/index.html)
  * [The Linux kernel user-space API guide](../userspace-api/index.html)

  * [The Linux kernel firmware guide](../firmware-guide/index.html)
  * [Open Firmware and Devicetree](../devicetree/index.html)

  * [CPU Architectures](../arch/index.html)

  * [Unsorted Documentation](../staging/index.html)

  * [Translations](../translations/index.html)

### This Page

  * [Show Source](../_sources/infiniband/user_verbs.rst.txt)

# Userspace verbs access¶

> The ib_uverbs module, built by enabling CONFIG_INFINIBAND_USER_VERBS,
> enables direct userspace access to IB hardware via "verbs," as described in
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
> process from touching another process's resources.

## Memory pinning¶

> Direct userspace I/O requires that memory regions that are potential I/O
> targets be kept resident at the same physical address. The ib_uverbs module
> manages pinning and unpinning memory regions via get_user_pages() and
> put_page() calls. It also accounts for the amount of memory pinned in the
> process's pinned_vm, and checks that unprivileged processes do not exceed
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

