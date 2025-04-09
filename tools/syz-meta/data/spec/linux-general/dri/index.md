![](../logo.png)

[dri](../)/  DRM

  * [Edit](//secure.freedesktop.org/write/dri/ikiwiki.cgi?page=DRM&do=edit)
  * [Page History](https://cgit.freedesktop.org/wiki/dri/log/DRM.mdwn)
  * [Repo Info](https://secure.freedesktop.org/cgit/dri/)

## Direct Rendering Manager (DRM)

The DRM is a kernel module that gives direct hardware access to DRI clients.

This module deals with DMA, AGP memory management, resource locking, and
secure hardware access. In order to support multiple, simultaneous 3D
applications the 3D graphics hardware must be treated as a shared resource.
Locking is required to provide mutual exclusion. DMA transfers and the AGP
interface are used to send buffers of graphics commands to the hardware.
Finally, there must be security to prevent clients from escalating privilege
using the graphics hardware.

### Where does the DRM reside?

Since internal Linux kernel interfaces and data structures may be changed at
any time, DRI kernel modules must be specially compiled for a particular
kernel version. The DRI kernel modules reside in the
`/lib/modules/.../kernel/drivers/gpu/drm` directory. (The kernel modules were
in the `/lib/modules/.../kernel/drivers/char/drm` directory before version
2.6.26.) Normally, the X server automatically loads whatever DRI kernel
modules are needed.

For each 3D hardware driver there is a kernel module, each of which requires
the generic DRM support code.

The source code is at git://anongit.freedesktop.org/git/mesa/drm

### In what way does the DRM support the DRI?

The DRM supports the DRI in three major ways:

  1. The DRM provides synchronized access to the graphics hardware. The direct rendering system has multiple entities (i.e., the X server, multiple direct-rendering clients, and the kernel) competing for direct access to the graphics hardware. Hardware that is currently available for PC-class machines will lock up if more than one entity is accessing the hardware (e.g., if two clients intermingle requests in the command FIFO or (on some hardware) if one client reads the framebuffer while another writes the command FIFO). The DRM provides a single per-device hardware lock to synchronize access to the hardware. The hardware lock may be required when the X server performs 2D rendering, when a direct-rendering client is performing a software fallback that must read or write the frame buffer, or when the kernel is dispatching DMA buffers. This hardware lock may not be required for all hardware (e.g., high-end hardware may be able to intermingle command requests from multiple clients) or for all implementations (e.g., one that uses a page fault mechanism instead of an explicit lock). In the later case, the DRM would be extended to provide support for this mechanism. For more details on the hardware lock requirements and a discussion of the performance implications and implementation details, please see [FOM99]. 
  2. The DRM enforces the DRI security policy for access to the graphics hardware. The X server, running as root, usually obtains access to the frame buffer and MMIO regions on the graphics hardware by mapping these regions using `/dev/mem`. The direct-rendering clients, however, do not run as root, but still require similar mappings. Like `/dev/mem`, the DRM device interface allows clients to create these mappings, but with the following restrictions: * The client may only map regions if it has a current connection to the X server. This forces direct-rendering clients to obey the normal X server security policy (e.g., using `xauth`). * The client may only map regions if it can open `/dev/drm?`, which is only accessible by root and by a group specified in the XF86Config file (a file that only root can edit). This allows the system administrator to restrict direct rendering access to a group of trusted users. * The client may only map regions that the X server allows to be mapped. The X server may also restrict those mappings to be read-only. This allows regions with security implications (e.g., those containing registers that can start DMA) to be restricted. 
  3. The DRM provides a generic DMA engine. Most modern PC-class graphics hardware provides for DMA access to the command FIFO. Often, DMA access has been optimized so that it provides significantly better throughput than does MMIO access. For these cards, the DRM provides a DMA engine with the following features: * The X server can specify multiple pools of different sized buffers which are allocated and locked down. * The direct-rendering client maps these buffers into its virtual address space, using the DRM API. * The direct-rendering client reserves some of these buffers from the DRM, fills the buffers with commands, and requests that the DRM send the buffers to the graphics hardware. Small buffers are used to ensure that the X server can get the lock between buffer dispatches, thereby providing X server interactivity. Typical 40MB/s PCI transfer rates may require 10000 4kB buffer dispatches per second. * The DRM manages a queue of DMA buffers for each OpenGL GLXContext, and detects when a GLXContext switch is necessary. Hooks are provided so that a device-specific driver can perform the GLXContext switch in kernel-space, and a callback to the X server is provided when a device-specific driver is not available (for the sample implementation, the callback mechanism is used because it provides an example of the most generic method for GLXContext switching). The DRM also performs simple scheduling of DMA buffer requests to prevent GLXContext thrashing. When a DMA is swapped a significant amount of data must be read from and/or written to the graphics device (between 4kB and 64kB for typical hardware). * The DMA engine is generic in the sense that the X server provides information at run-time on how to perform DMA operations for the specific hardware installed on the machine. The X server does all of the hardware detection and setup. This allows easy bootstrapping for new graphics hardware under the DRI, while providing for later performance and capability enhancements through the use of a device-specific kernel driver. 

### Is it possible to make a DRI driver without a DRM driver in a piece of
hardware whereby we do all accelerations in PIO mode?

The kernel provides three main things:

  1. the ability to wait on a contended lock (the waiting process is put to sleep), and to free the lock of a dead process; 
  2. the ability to mmap areas of memory that non-root processes can't usually map; 
  3. the ability to handle hardware interruptions and a DMA queue. All of these are hard to do outside the kernel, but they aren't required components of a DRM driver. For example, the tdfx driver doesn't use hardware interrupts at all -- it is one of the simplest DRM drivers, and would be a good model for the hardware you are thinking about (in it's current form, it is quite generic). 

**Note:** DRI was designed with a very wide range of hardware in mind, ranging
from very low-end PC graphics cards through very high-end SGI-like hardware
(which may not even need the lock). The DRI is an infrastructure or framework
that is very flexible -- most of the example drivers we have use hardware
interrupts, but that isn't a requirement.

### Has the DRM driver support for or loading sub-drivers?

Although the [Faith99] states that the DRM driver has support for loading sub-
drivers by calling drmCreateSub, Linus didn't like that approach. He wanted
all drivers to be independent, so the top-level "DRM" module no longer exists
and each DRM module is independent.

### Is it possible to use floating point on the kernel?

You _can_ use FP, but you have to jump through hoops to do so, especially if
you're in an asynchronous context (i.e. interrupt or similar).

In process context (i.e. ioctl code) you could just decide that part of the
calling convention of the ioctl is that the FP register state is corrupted,
and use FP fairly freely - but realizing that FP usage is basically the same
as "access to user mode" and can cause traps.

Oh, and getting an FP exception in the kernel is _definitely_ illegal, and can
(and does) cause a hung box. The FP exception handling depends on a signal
handler cleaning the thing up.

In general, the rule would be: don't do it. It's possible, but there are a lot
of cases you have to worry about, and it would be a _lot_ better to do the FP
(including any coordinate snapping) in mesa in user mode, and maybe just
verify the values in the kernel (which can be done with fairly simple integer
arithmetic).

  * \-- [LinusTorvalds](../LinusTorvalds/)

### When to use semaphores?

  * _The problem appears to be that the DRM people are used to using semaphores to protect kernel data structures. That is**wrong**._ Follow-up, just in case somebody asks "what are semaphores there for then?" 

There are reasons to use semaphores, but they are not about protecting data
structures. They are mainly useful for protecting whole subsystems of code,
notably in filesystems where we use semaphores extensively to protect things
like concurrent access to a directory while doing lookups on it.

Examples:

  * directory cache lookups (kernel "dcache" data structure): protected by "dcache_lock" spinlock 
  * VFS callback into filesystem to do a lookup that wasn't cached protected by per-directory inode semaphore Basically, spinlocks protect data, while semaphores are more of a high-level "protect the concept" thing. 

I suspect that there is very little in the DRI code that would ever have a
good reason to use a semaphore, they just shouldn't be used at that kind of
low level (they might be useful for doing things like serializing device
opening etc, so I'm not saying that DRI should never ever use one, but you get
the idea).

  * \-- [LinusTorvalds](../LinusTorvalds/)

### What future changes are going to be made to the DRM?

There is a [NextDRMVersion](../NextDRMVersion/) page to put ideas for changes
to be made to the DRM if we should ever decide to eliminate compatibility with
previous versions.

* * *

[CategoryGlossary](../CategoryGlossary/), [CategoryFaq](../CategoryFaq/)

Last edited Sat 13 Apr 2013 11:15:48 PM UTC

