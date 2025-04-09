[ The Linux Kernel ](../index.html)

5.8.0

  * [The Linux kernel user’s and administrator’s guide](../admin-guide/index.html)
  * [Kernel Build System](../kbuild/index.html)

  * [The Linux kernel firmware guide](../firmware-guide/index.html)
  * [Open Firmware and Device Tree](../devicetree/index.html)

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
  * [Linux CPUFreq - CPU frequency and voltage scaling code in the Linux(TM) kernel](../cpu-freq/index.html)
  * [Integrated Drive Electronics (IDE)](../ide/index.html)
  * [Frame Buffer](../fb/index.html)
  * [fpga](../fpga/index.html)
  * [Human Interface Devices (HID)](../hid/index.html)
  * [I2C/SMBus Subsystem](../i2c/index.html)
  * [Industrial I/O](../iio/index.html)
  * [ISDN](../isdn/index.html)
  * [InfiniBand](../infiniband/index.html)
  * [LEDs](../leds/index.html)
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
  * [Filesystems in the Linux kernel](index.html)
    * [Core VFS documentation](index.html#core-vfs-documentation)
      * [Overview of the Linux Virtual File System](vfs.html)
      * [Pathname lookup](path-lookup.html)
      * [Linux Filesystems API summary](api-summary.html)
      * [splice and pipes](splice.html)
      * [Locking](locking.html)
      * [Directory Locking](directory-locking.html)
      * The Devpts Filesystem
      * [Linux Directory Notification](dnotify.html)
      * [Fiemap Ioctl](fiemap.html)
      * [File management in the Linux kernel](files.html)
      * [File Locking Release Notes](locks.html)
      * [Mandatory File Locking For The Linux Operating System](mandatory-locking.html)
      * [fILESYSTEM Mount API](mount_api.html)
      * [PARAMETER DESCRIPTION](mount_api.html#parameter-description)
      * [Quota subsystem](quota.html)
      * [The seq_file Interface](seq_file.html)
      * [Shared Subtrees](sharedsubtree.html)
      * [Accessing PCI device resources through sysfs](sysfs-pci.html)
      * [Sysfs tagging](sysfs-tagging.html)
      * [Automount Support](automount-support.html)
      * [Filesystem Caching](caching/index.html)
      * [Changes since 2.5.0:](porting.html)
    * [Filesystem support layers](index.html#filesystem-support-layers)
    * [Filesystems](index.html#filesystems)
  * [Linux Memory Management Documentation](../vm/index.html)
  * [BPF Documentation](../bpf/index.html)
  * [USB support](../usb/index.html)
  * [Linux PCI Bus Subsystem](../PCI/index.html)
  * [Linux SCSI Subsystem](../scsi/index.html)
  * [Assorted Miscellaneous Devices Documentation](../misc-devices/index.html)
  * [Linux Scheduler](../scheduler/index.html)
  * [MHI](../mhi/index.html)

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

  * [ext4 Data Structures and Algorithms](ext4/index.html)

  * [Translations](../translations/index.html)

__[The Linux Kernel](../index.html)

  * [Docs](../index.html) »
  * [Filesystems in the Linux kernel](index.html) »
  * The Devpts Filesystem
  * [ View page source](../_sources/filesystems/devpts.rst.txt)

* * *

# The Devpts Filesystem¶

Each mount of the devpts filesystem is now distinct such that ptys and their
indicies allocated in one mount are independent from ptys and their indicies
in all other mounts.

All mounts of the devpts filesystem now create a `/dev/pts/ptmx` node with
permissions `0000`.

To retain backwards compatibility the a ptmx device node (aka any node created
with `mknod name c 5 2`) when opened will look for an instance of devpts under
the name `pts` in the same directory as the ptmx device node.

As an option instead of placing a `/dev/ptmx` device node at `/dev/ptmx` it is
possible to place a symlink to `/dev/pts/ptmx` at `/dev/ptmx` or to bind mount
`/dev/ptx/ptmx` to `/dev/ptmx`. If you opt for using the devpts filesystem in
this manner devpts should be mounted with the `ptmxmode=0666`, or `chmod 0666
/dev/pts/ptmx` should be called.

Total count of pty pairs in all instances is limited by sysctls:

    
    
    kernel.pty.max = 4096       - global limit
    kernel.pty.reserve = 1024   - reserved for filesystems mounted from the initial mount namespace
    kernel.pty.nr               - current count of ptys
    

Per-instance limit could be set by adding mount option `max=<count>`.

This feature was added in kernel 3.4 together with `sysctl
kernel.pty.reserve`.

In kernels older than 3.4 sysctl `kernel.pty.max` works as per-instance limit.

[Next ](dnotify.html "Linux Directory Notification") [ Previous](directory-
locking.html "Directory Locking")

* * *

(C) Copyright The kernel development community

Built with [Sphinx](http://sphinx-doc.org/) using a
[theme](https://github.com/rtfd/sphinx_rtd_theme) provided by [Read the
Docs](https://readthedocs.org).

