# InfiniBand Midlayer Locking

This guide is an attempt to make explicit the locking assumptions made by the InfiniBand midlayer. It describes the requirements on both low-level drivers that sit below the midlayer and upper level protocols that use the midlayer.

## Sleeping and interrupt context

With the following exceptions, a low-level driver implementation of all of the methods in struct ib\_device may sleep. The exceptions are any methods from the list:

+   create\_ah

+   modify\_ah

+   query\_ah

+   destroy\_ah

+   post\_send

+   post\_recv

+   poll\_cq

+   req\_notify\_cq


which may not sleep and must be callable from any context.

The corresponding functions exported to upper level protocol consumers:

+   rdma\_create\_ah

+   rdma\_modify\_ah

+   rdma\_query\_ah

+   rdma\_destroy\_ah

+   ib\_post\_send

+   ib\_post\_recv

+   ib\_req\_notify\_cq

are therefore safe to call from any context.

In addition, the function

+   ib\_dispatch\_event

used by low-level drivers to dispatch asynchronous events through the midlayer is also safe to call from any context.

### Reentrancy

All of the methods in struct ib\_device exported by a low-level driver must be fully reentrant. The low-level driver is required to perform all synchronization necessary to maintain consistency, even if multiple function calls using the same object are run simultaneously.

The IB midlayer does not perform any serialization of function calls.

Because low-level drivers are reentrant, upper level protocol consumers are not required to perform any serialization. However, some serialization may be required to get sensible results. For example, a consumer may safely call ib\_poll\_cq() on multiple CPUs simultaneously. However, the ordering of the work completion information between different calls of ib\_poll\_cq() is not defined.

### Callbacks

A low-level driver must not perform a callback directly from the same callchain as an ib\_device method call. For example, it is not allowed for a low-level driver to call a consumer’s completion event handler directly from its post\_send method. Instead, the low-level driver should defer this callback by, for example, scheduling a tasklet to perform the callback.

The low-level driver is responsible for ensuring that multiple completion event handlers for the same CQ are not called simultaneously. The driver must guarantee that only one CQ event handler for a given CQ is running at a time. In other words, the following situation is not allowed:

```
       CPU1                                    CPU2

 low-level driver -
   consumer CQ event callback:
     /* ... */
     ib_req_notify_cq(cq, ...);
                                       low-level driver -
     /* ... */                           consumer CQ event callback:
                                           /* ... */
     return from CQ event handler
```

The context in which completion event and asynchronous event callbacks run is not defined. Depending on the low-level driver, it may be process context, softirq context, or interrupt context. Upper level protocol consumers may not sleep in a callback.

### Hot-plug

A low-level driver announces that a device is ready for use by consumers when it calls [`ib_register_device()`](https://www.kernel.org/doc/html/v6.2/driver-api/infiniband.html#c.ib_register_device "ib_register_device"), all initialization must be complete before this call. The device must remain usable until the driver’s call to [`ib_unregister_device()`](https://www.kernel.org/doc/html/v6.2/driver-api/infiniband.html#c.ib_unregister_device "ib_unregister_device") has returned.

A low-level driver must call [`ib_register_device()`](https://www.kernel.org/doc/html/v6.2/driver-api/infiniband.html#c.ib_register_device "ib_register_device") and [`ib_unregister_device()`](https://www.kernel.org/doc/html/v6.2/driver-api/infiniband.html#c.ib_unregister_device "ib_unregister_device") from process context. It must not hold any semaphores that could cause deadlock if a consumer calls back into the driver across these calls.

An upper level protocol consumer may begin using an IB device as soon as the add method of its struct ib\_client is called for that device. A consumer must finish all cleanup and free all resources relating to a device before returning from the remove method.

A consumer is permitted to sleep in its add and remove methods.