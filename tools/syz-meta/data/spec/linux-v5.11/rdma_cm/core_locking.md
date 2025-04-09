[ The Linux Kernel ](../index.html)

5.11.0

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
  * [InfiniBand](index.html)
    * InfiniBand Midlayer Locking
      * Sleeping and interrupt context
        * Reentrancy
        * Callbacks
        * Hot-plug
    * [IP over InfiniBand](ipoib.html)
    * [Intel Omni-Path (OPA) Virtual Network Interface Controller (VNIC)](opa_vnic.html)
    * [Sysfs files](sysfs.html)
    * [Tag matching logic](tag_matching.html)
    * [Userspace MAD access](user_mad.html)
    * [Userspace verbs access](user_verbs.html)
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
  * [Nios II Specific Documentation](../nios2/index.html)
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

  * [Unsorted Documentation](../staging/index.html)
  * [Atomic Types](../staging/index.html#atomic-types)
  * [Atomic bitops](../staging/index.html#atomic-bitops)
  * [Memory Barriers](../staging/index.html#memory-barriers)
  * [General notification mechanism](../watch_queue.html)

  * [Translations](../translations/index.html)

__[The Linux Kernel](../index.html)

  * [Docs](../index.html) »
  * [InfiniBand](index.html) »
  * InfiniBand Midlayer Locking
  * [ View page source](../_sources/infiniband/core_locking.rst.txt)

* * *

# InfiniBand Midlayer Locking¶

> This guide is an attempt to make explicit the locking assumptions made by
> the InfiniBand midlayer. It describes the requirements on both low-level
> drivers that sit below the midlayer and upper level protocols that use the
> midlayer.

## Sleeping and interrupt context¶

> With the following exceptions, a low-level driver implementation of all of
> the methods in struct ib_device may sleep. The exceptions are any methods
> from the list:
>

>>   * create_ah

>>   * modify_ah

>>   * query_ah

>>   * destroy_ah

>>   * post_send

>>   * post_recv

>>   * poll_cq

>>   * req_notify_cq

>>

>
> which may not sleep and must be callable from any context.
>
> The corresponding functions exported to upper level protocol consumers:
>

>>   * rdma_create_ah

>>   * rdma_modify_ah

>>   * rdma_query_ah

>>   * rdma_destroy_ah

>>   * ib_post_send

>>   * ib_post_recv

>>   * ib_req_notify_cq

>>

>
> are therefore safe to call from any context.
>
> In addition, the function
>

>>   * ib_dispatch_event

>>

>
> used by low-level drivers to dispatch asynchronous events through the
> midlayer is also safe to call from any context.

### Reentrancy¶

> All of the methods in struct ib_device exported by a low-level driver must
> be fully reentrant. The low-level driver is required to perform all
> synchronization necessary to maintain consistency, even if multiple function
> calls using the same object are run simultaneously.
>
> The IB midlayer does not perform any serialization of function calls.
>
> Because low-level drivers are reentrant, upper level protocol consumers are
> not required to perform any serialization. However, some serialization may
> be required to get sensible results. For example, a consumer may safely call
> ib_poll_cq() on multiple CPUs simultaneously. However, the ordering of the
> work completion information between different calls of ib_poll_cq() is not
> defined.

### Callbacks¶

> A low-level driver must not perform a callback directly from the same
> callchain as an ib_device method call. For example, it is not allowed for a
> low-level driver to call a consumer’s completion event handler directly from
> its post_send method. Instead, the low-level driver should defer this
> callback by, for example, scheduling a tasklet to perform the callback.
>
> The low-level driver is responsible for ensuring that multiple completion
> event handlers for the same CQ are not called simultaneously. The driver
> must guarantee that only one CQ event handler for a given CQ is running at a
> time. In other words, the following situation is not allowed:
>  
>  
>           CPU1                                    CPU2
>  
>     low-level driver ->
>       consumer CQ event callback:
>         /* ... */
>         ib_req_notify_cq(cq, ...);
>                                           low-level driver ->
>         /* ... */                           consumer CQ event callback:
>                                               /* ... */
>         return from CQ event handler
>  
>
> The context in which completion event and asynchronous event callbacks run
> is not defined. Depending on the low-level driver, it may be process
> context, softirq context, or interrupt context. Upper level protocol
> consumers may not sleep in a callback.

### Hot-plug¶

> A low-level driver announces that a device is ready for use by consumers
> when it calls [`ib_register_device()`](../driver-
> api/infiniband.html#c.ib_register_device "ib_register_device"), all
> initialization must be complete before this call. The device must remain
> usable until the driver’s call to [`ib_unregister_device()`](../driver-
> api/infiniband.html#c.ib_unregister_device "ib_unregister_device") has
> returned.
>
> A low-level driver must call [`ib_register_device()`](../driver-
> api/infiniband.html#c.ib_register_device "ib_register_device") and
> [`ib_unregister_device()`](../driver-
> api/infiniband.html#c.ib_unregister_device "ib_unregister_device") from
> process context. It must not hold any semaphores that could cause deadlock
> if a consumer calls back into the driver across these calls.
>
> An upper level protocol consumer may begin using an IB device as soon as the
> add method of its struct ib_client is called for that device. A consumer
> must finish all cleanup and free all resources relating to a device before
> returning from the remove method.
>
> A consumer is permitted to sleep in its add and remove methods.

[Next ](ipoib.html "IP over InfiniBand") [ Previous](index.html "InfiniBand")

* * *

(C) Copyright The kernel development community

Built with [Sphinx](http://sphinx-doc.org/) using a
[theme](https://github.com/rtfd/sphinx_rtd_theme) provided by [Read the
Docs](https://readthedocs.org).

