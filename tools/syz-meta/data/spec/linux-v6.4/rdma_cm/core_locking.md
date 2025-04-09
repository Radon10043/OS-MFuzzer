# [The Linux Kernel](../index.html)

6.4.0

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
    * [Driver implementer's API guide](../driver-api/index.html)
    * [Core API Documentation](../core-api/index.html)
    * [Locking](../locking/index.html)
    * [Accounting](../accounting/index.html)
    * [Block](../block/index.html)
    * [CD-ROM](../cdrom/index.html)
    * [CPUFreq - CPU frequency and voltage scaling code in the Linux(TM) kernel](../cpu-freq/index.html)
    * [Frame Buffer](../fb/index.html)
    * [FPGA](../fpga/index.html)
    * [Human Interface Devices (HID)](../hid/index.html)
    * [I2C/SMBus Subsystem](../i2c/index.html)
    * [Industrial I/O](../iio/index.html)
    * [ISDN](../isdn/index.html)
    * [InfiniBand](index.html)
      * InfiniBand Midlayer Locking
      * [IP over InfiniBand](ipoib.html)
      * [Intel Omni-Path (OPA) Virtual Network Interface Controller (VNIC)](opa_vnic.html)
      * [Sysfs files](sysfs.html)
      * [Tag matching logic](tag_matching.html)
      * [Userspace MAD access](user_mad.html)
      * [Userspace verbs access](user_verbs.html)
    * [LEDs](../leds/index.html)
    * [NetLabel](../netlabel/index.html)
    * [Networking](../networking/index.html)
    * [PCMCIA](../pcmcia/index.html)
    * [Power Management](../power/index.html)
    * [TCM Virtual Device](../target/index.html)
    * [Timers](../timers/index.html)
    * [Serial Peripheral Interface (SPI)](../spi/index.html)
    * [1-Wire Subsystem](../w1/index.html)
    * [Watchdog Support](../watchdog/index.html)
    * [Virtualization Support](../virt/index.html)
    * [Input Documentation](../input/index.html)
    * [Hardware Monitoring](../hwmon/index.html)
    * [GPU Driver Developer's Guide](../gpu/index.html)
    * [Compute Accelerators](../accel/index.html)
    * [Security Documentation](../security/index.html)
    * [Sound Subsystem Documentation](../sound/index.html)
    * [Crypto API](../crypto/index.html)
    * [Filesystems in the Linux kernel](../filesystems/index.html)
    * [Memory Management Documentation](../mm/index.html)
    * [BPF Documentation](../bpf/index.html)
    * [USB support](../usb/index.html)
    * [PCI Bus Subsystem](../PCI/index.html)
    * [SCSI Subsystem](../scsi/index.html)
    * [Assorted Miscellaneous Devices Documentation](../misc-devices/index.html)
    * [Scheduler](../scheduler/index.html)
    * [MHI](../mhi/index.html)
    * [PECI Subsystem](../peci/index.html)
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

  * [Show Source](../_sources/infiniband/core_locking.rst.txt)

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

>>

>>   * modify_ah

>>

>>   * query_ah

>>

>>   * destroy_ah

>>

>>   * post_send

>>

>>   * post_recv

>>

>>   * poll_cq

>>

>>   * req_notify_cq

>>

>>

>
> which may not sleep and must be callable from any context.
>
> The corresponding functions exported to upper level protocol consumers:
>

>>   * rdma_create_ah

>>

>>   * rdma_modify_ah

>>

>>   * rdma_query_ah

>>

>>   * rdma_destroy_ah

>>

>>   * ib_post_send

>>

>>   * ib_post_recv

>>

>>   * ib_req_notify_cq

>>

>>

>
> are therefore safe to call from any context.
>
> In addition, the function
>

>>   * ib_dispatch_event

>>

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
> low-level driver to call a consumer's completion event handler directly from
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
> usable until the driver's call to [`ib_unregister_device()`](../driver-
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

(C)The kernel development community. | Powered by [Sphinx 5.0.1](http://sphinx-doc.org/) & [Alabaster 0.7.12](https://github.com/bitprophet/alabaster) | [Page source](../_sources/infiniband/core_locking.rst.txt)

