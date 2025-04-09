[ The Linux Kernel ](../index.html)

5.5.0

  * [The Linux kernel user’s and administrator’s guide](../admin-guide/index.html)
  * [Kernel Build System](../kbuild/index.html)

  * [The Linux kernel firmware guide](../firmware-guide/index.html)

  * [The Linux kernel user-space API guide](../userspace-api/index.html)

  * [Working with the kernel development community](../process/index.html)
  * [Development tools for the kernel](../dev-tools/index.html)
  * [How to write kernel documentation](../doc-guide/index.html)
  * [Kernel Hacking Guides](../kernel-hacking/index.html)
  * [Linux Tracing Technologies](../trace/index.html)
  * [Kernel Maintainer Handbook](../maintainer/index.html)
  * [fault-injection](../fault-injection/index.html)
  * [Kernel Livepatching](../livepatch/index.html)

  * [The Linux driver implementer’s API guide](../driver-api/index.html)
  * [Core API Documentation](../core-api/index.html)
  * [locking](../locking/index.html)
  * [Accounting](../accounting/index.html)
  * [Block](../block/index.html)
  * [cdrom](../cdrom/index.html)
  * [Integrated Drive Electronics (IDE)](../ide/index.html)
  * [Frame Buffer](../fb/index.html)
  * [fpga](../fpga/index.html)
  * [Human Interface Devices (HID)](../hid/index.html)
  * [I2C/SMBus Subsystem](../i2c/index.html)
  * [Industrial I/O](../iio/index.html)
  * [ISDN](../isdn/index.html)
  * [InfiniBand](index.html)
    * [InfiniBand Midlayer Locking](core_locking.html)
    * [IP over InfiniBand](ipoib.html)
    * [Intel Omni-Path (OPA) Virtual Network Interface Controller (VNIC)](opa_vnic.html)
    * [Sysfs files](sysfs.html)
    * [Tag matching logic](tag_matching.html)
    * [Userspace MAD access](user_mad.html)
    * Userspace verbs access
      * User-kernel communication
      * Resource management
      * Memory pinning
      * /dev files
  * [LEDs](../leds/index.html)
  * [Linux Media Subsystem Documentation](../media/index.html)
  * [NetLabel](../netlabel/index.html)
  * [Linux Networking Documentation](../networking/index.html)
  * [pcmcia](../pcmcia/index.html)
  * [Power Management](../power/index.html)
  * [TCM Virtual Device](../target/index.html)
  * [timers](../timers/index.html)
  * [Serial Peripheral Interface (SPI)](../spi/index.html)
  * [1-Wire Subsystem](../w1/index.html)
  * [Linux Watchdog Support](../watchdog/index.html)
  * [Linux Virtualization Support](../virt/index.html)
  * [The Linux Input Documentation](../input/index.html)
  * [Linux Hardware Monitoring](../hwmon/index.html)
  * [Linux GPU Driver Developer’s Guide](../gpu/index.html)
  * [Security Documentation](../security/index.html)
  * [Linux Sound Subsystem Documentation](../sound/index.html)
  * [Linux Kernel Crypto API](../crypto/index.html)
  * [Filesystems in the Linux kernel](../filesystems/index.html)
  * [Linux Memory Management Documentation](../vm/index.html)
  * [BPF Documentation](../bpf/index.html)
  * [USB support](../usb/index.html)
  * [Linux PCI Bus Subsystem](../PCI/index.html)
  * [Assorted Miscellaneous Devices Documentation](../misc-devices/index.html)
  * [Intel Many Integrated Core (MIC) architecture](../mic/index.html)
  * [Linux Scheduler](../scheduler/index.html)

  * [Assembler Annotations](../asm-annotations.html)

  * [ARM Architecture](../arm/index.html)
  * [ARM64 Architecture](../arm64/index.html)
  * [IA-64 Architecture](../ia64/index.html)
  * [m68k Architecture](../m68k/index.html)
  * [MIPS-specific Documentation](../mips/index.html)
  * [Linux on the Nios II architecture](../nios2/nios2.html)
  * [OpenRISC Architecture](../openrisc/index.html)
  * [PA-RISC Architecture](../parisc/index.html)
  * [powerpc](../powerpc/index.html)
  * [RISC-V architecture](../riscv/index.html)
  * [s390 Architecture](../s390/index.html)
  * [SuperH Interfaces Guide](../sh/index.html)
  * [Sparc Architecture](../sparc/index.html)
  * [x86-specific Documentation](../x86/index.html)
  * [Xtensa Architecture](../xtensa/index.html)

  * [ext4 Data Structures and Algorithms](../filesystems/ext4/index.html)

  * [Translations](../translations/index.html)

__[The Linux Kernel](../index.html)

  * [Docs](../index.html) »
  * [InfiniBand](index.html) »
  * Userspace verbs access
  * [ View page source](../_sources/infiniband/user_verbs.rst.txt)

* * *

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

[Next ](../leds/index.html "LEDs") [ Previous](user_mad.html "Userspace MAD
access")

* * *

(C) Copyright The kernel development community

Built with [Sphinx](http://sphinx-doc.org/) using a
[theme](https://github.com/rtfd/sphinx_rtd_theme) provided by [Read the
Docs](https://readthedocs.org).

