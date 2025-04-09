[ The Linux Kernel ](../index.html)

5.7.0

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
  * [Linux CPUFreq - CPU frequency and voltage scaling code in the Linux(TM) kernel](../cpu-freq/index.html)
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
    * Tag matching logic
      * Tag matching implementation
    * [Userspace MAD access](user_mad.html)
    * [Userspace verbs access](user_verbs.html)
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

  * [ext4 Data Structures and Algorithms](../filesystems/ext4/index.html)

  * [Translations](../translations/index.html)

__[The Linux Kernel](../index.html)

  * [Docs](../index.html) »
  * [InfiniBand](index.html) »
  * Tag matching logic
  * [ View page source](../_sources/infiniband/tag_matching.rst.txt)

* * *

# Tag matching logic¶

The MPI standard defines a set of rules, known as tag-matching, for matching
source send operations to destination receives. The following parameters must
match the following source and destination parameters:

  * Communicator
  * User tag - wild card may be specified by the receiver
  * Source rank – wild car may be specified by the receiver
  * Destination rank – wild

The ordering rules require that when more than one pair of send and receive
message envelopes may match, the pair that includes the earliest posted-send
and the earliest posted-receive is the pair that must be used to satisfy the
matching operation. However, this doesn’t imply that tags are consumed in the
order they are created, e.g., a later generated tag may be consumed, if
earlier tags can’t be used to satisfy the matching rules.

When a message is sent from the sender to the receiver, the communication
library may attempt to process the operation either after or before the
corresponding matching receive is posted. If a matching receive is posted,
this is an expected message, otherwise it is called an unexpected message.
Implementations frequently use different matching schemes for these two
different matching instances.

To keep MPI library memory footprint down, MPI implementations typically use
two different protocols for this purpose:

1\. The Eager protocol- the complete message is sent when the send is
processed by the sender. A completion send is received in the send_cq
notifying that the buffer can be reused.

2\. The Rendezvous Protocol - the sender sends the tag-matching header, and
perhaps a portion of data when first notifying the receiver. When the
corresponding buffer is posted, the responder will use the information from
the header to initiate an RDMA READ operation directly to the matching buffer.
A fin message needs to be received in order for the buffer to be reused.

## Tag matching implementation¶

There are two types of matching objects used, the posted receive list and the
unexpected message list. The application posts receive buffers through calls
to the MPI receive routines in the posted receive list and posts send messages
using the MPI send routines. The head of the posted receive list may be
maintained by the hardware, with the software expected to shadow this list.

When send is initiated and arrives at the receive side, if there is no pre-
posted receive for this arriving message, it is passed to the software and
placed in the unexpected message list. Otherwise the match is processed,
including rendezvous processing, if appropriate, delivering the data to the
specified receive buffer. This allows overlapping receive-side MPI tag
matching with computation.

When a receive-message is posted, the communication library will first check
the software unexpected message list for a matching receive. If a match is
found, data is delivered to the user buffer, using a software controlled
protocol. The UCX implementation uses either an eager or rendezvous protocol,
depending on data size. If no match is found, the entire pre-posted receive
list is maintained by the hardware, and there is space to add one more pre-
posted receive to this list, this receive is passed to the hardware. Software
is expected to shadow this list, to help with processing MPI cancel
operations. In addition, because hardware and software are not expected to be
tightly synchronized with respect to the tag-matching operation, this shadow
list is used to detect the case that a pre-posted receive is passed to the
hardware, as the matching unexpected message is being passed from the hardware
to the software.

[Next ](user_mad.html "Userspace MAD access") [ Previous](sysfs.html "Sysfs
files")

* * *

(C) Copyright The kernel development community

Built with [Sphinx](http://sphinx-doc.org/) using a
[theme](https://github.com/rtfd/sphinx_rtd_theme) provided by [Read the
Docs](https://readthedocs.org).

