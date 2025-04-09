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
    * IP over InfiniBand
      * Partitions and P_Keys
      * Datagram vs Connected modes
      * Stateless offloads
      * Interrupt moderation
      * Debugging Information
      * References
    * [Intel Omni-Path (OPA) Virtual Network Interface Controller (VNIC)](opa_vnic.html)
    * [Sysfs files](sysfs.html)
    * [Tag matching logic](tag_matching.html)
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
  * IP over InfiniBand
  * [ View page source](../_sources/infiniband/ipoib.rst.txt)

* * *

# IP over InfiniBand¶

> The ib_ipoib driver is an implementation of the IP over InfiniBand protocol
> as specified by RFC 4391 and 4392, issued by the IETF ipoib working group.
> It is a “native” implementation in the sense of setting the interface type
> to ARPHRD_INFINIBAND and the hardware address length to 20 (earlier
> proprietary implementations masqueraded to the kernel as ethernet
> interfaces).

## Partitions and P_Keys¶

> When the IPoIB driver is loaded, it creates one interface for each port
> using the P_Key at index 0. To create an interface with a different P_Key,
> write the desired P_Key into the main interface’s /sys/class/net/<intf
> name>/create_child file. For example:
>  
>  
>     echo 0x8001 > /sys/class/net/ib0/create_child
>  
>
> This will create an interface named ib0.8001 with P_Key 0x8001. To remove a
> subinterface, use the “delete_child” file:
>  
>  
>     echo 0x8001 > /sys/class/net/ib0/delete_child
>  
>
> The P_Key for any interface is given by the “pkey” file, and the main
> interface for a subinterface is in “parent.”
>
> Child interface create/delete can also be done using IPoIB’s rtnl_link_ops,
> where children created using either way behave the same.

## Datagram vs Connected modes¶

> The IPoIB driver supports two modes of operation: datagram and connected.
> The mode is set and read through an interface’s /sys/class/net/<intf
> name>/mode file.
>
> In datagram mode, the IB UD (Unreliable Datagram) transport is used and so
> the interface MTU has is equal to the IB L2 MTU minus the IPoIB
> encapsulation header (4 bytes). For example, in a typical IB fabric with a
> 2K MTU, the IPoIB MTU will be 2048 - 4 = 2044 bytes.
>
> In connected mode, the IB RC (Reliable Connected) transport is used.
> Connected mode takes advantage of the connected nature of the IB transport
> and allows an MTU up to the maximal IP packet size of 64K, which reduces the
> number of IP packets needed for handling large UDP datagrams, TCP segments,
> etc and increases the performance for large messages.
>
> In connected mode, the interface’s UD QP is still used for multicast and
> communication with peers that don’t support connected mode. In this case, RX
> emulation of ICMP PMTU packets is used to cause the networking stack to use
> the smaller UD MTU for these neighbours.

## Stateless offloads¶

> If the IB HW supports IPoIB stateless offloads, IPoIB advertises TCP/IP
> checksum and/or Large Send (LSO) offloading capability to the network stack.
>
> Large Receive (LRO) offloading is also implemented and may be turned on/off
> using ethtool calls. Currently LRO is supported only for checksum offload
> capable devices.
>
> Stateless offloads are supported only in datagram mode.

## Interrupt moderation¶

> If the underlying IB device supports CQ event moderation, one can use
> ethtool to set interrupt mitigation parameters and thus reduce the overhead
> incurred by handling interrupts. The main code path of IPoIB doesn’t use
> events for TX completion signaling so only RX moderation is supported.

## Debugging Information¶

> By compiling the IPoIB driver with CONFIG_INFINIBAND_IPOIB_DEBUG set to ‘y’,
> tracing messages are compiled into the driver. They are turned on by setting
> the module parameters debug_level and mcast_debug_level to 1. These
> parameters can be controlled at runtime through files in
> /sys/module/ib_ipoib/.
>
> CONFIG_INFINIBAND_IPOIB_DEBUG also enables files in the debugfs virtual
> filesystem. By mounting this filesystem, for example with:
>  
>  
>     mount -t debugfs none /sys/kernel/debug
>  
>
> it is possible to get statistics about multicast groups from the files
> /sys/kernel/debug/ipoib/ib0_mcg and so on.
>
> The performance impact of this option is negligible, so it is safe to enable
> this option with debug_level set to 0 for normal operation.
>
> CONFIG_INFINIBAND_IPOIB_DEBUG_DATA enables even more debug output in the
> data path when data_debug_level is set to 1. However, even with the output
> disabled, enabling this configuration option will affect performance,
> because it adds tests to the fast path.

## References¶

> Transmission of IP over InfiniBand (IPoIB) (RFC 4391)
>     <http://ietf.org/rfc/rfc4391.txt>
> IP over InfiniBand (IPoIB) Architecture (RFC 4392)
>     <http://ietf.org/rfc/rfc4392.txt>
> IP over InfiniBand: Connected Mode (RFC 4755)
>     <http://ietf.org/rfc/rfc4755.txt>

[Next ](opa_vnic.html "Intel Omni-Path \(OPA\) Virtual Network Interface
Controller \(VNIC\)") [ Previous](core_locking.html "InfiniBand Midlayer
Locking")

* * *

(C) Copyright The kernel development community

Built with [Sphinx](http://sphinx-doc.org/) using a
[theme](https://github.com/rtfd/sphinx_rtd_theme) provided by [Read the
Docs](https://readthedocs.org).

