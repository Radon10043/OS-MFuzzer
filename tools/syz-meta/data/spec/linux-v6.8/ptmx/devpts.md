[ ![Logo](../_static/logo.svg) ](../index.html)

# [The Linux Kernel](../index.html)

6.8.0

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
    * [Core subsystems](../subsystem-apis.html#core-subsystems)
    * [Human interfaces](../subsystem-apis.html#human-interfaces)
    * [Networking interfaces](../subsystem-apis.html#networking-interfaces)
    * [Storage interfaces](../subsystem-apis.html#storage-interfaces)
      * [Filesystems in the Linux kernel](index.html)
      * [Block](../block/index.html)
      * [CD-ROM](../cdrom/index.html)
      * [SCSI Subsystem](../scsi/index.html)
      * [TCM Virtual Device](../target/index.html)
      * [Accounting](../accounting/index.html)
      * [CPUFreq - CPU frequency and voltage scaling code in the Linux(TM) kernel](../cpu-freq/index.html)
      * [FPGA](../fpga/index.html)
      * [I2C/SMBus Subsystem](../i2c/index.html)
      * [Industrial I/O](../iio/index.html)
      * [PCMCIA](../pcmcia/index.html)
      * [Serial Peripheral Interface (SPI)](../spi/index.html)
      * [1-Wire Subsystem](../w1/index.html)
      * [Watchdog Support](../watchdog/index.html)
      * [Virtualization Support](../virt/index.html)
      * [Hardware Monitoring](../hwmon/index.html)
      * [Compute Accelerators](../accel/index.html)
      * [Security Documentation](../security/index.html)
      * [Crypto API](../crypto/index.html)
      * [BPF Documentation](../bpf/index.html)
      * [USB support](../usb/index.html)
      * [PCI Bus Subsystem](../PCI/index.html)
      * [Assorted Miscellaneous Devices Documentation](../misc-devices/index.html)
      * [PECI Subsystem](../peci/index.html)
      * [WMI Subsystem](../wmi/index.html)
      * [TEE Subsystem](../tee/index.html)
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
  * [Reliability, Availability and Serviceability features](../RAS/ras.html)

  * [Translations](../translations/index.html)

### This Page

  * [Show Source](../_sources/filesystems/devpts.rst.txt)

# The Devpts Filesystem¶

Each mount of the devpts filesystem is now distinct such that ptys and their
indices allocated in one mount are independent from ptys and their indices in
all other mounts.

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

(C)The kernel development community. | Powered by [Sphinx 5.0.1](http://sphinx-doc.org/) & [Alabaster 0.7.12](https://github.com/bitprophet/alabaster) | [Page source](../_sources/filesystems/devpts.rst.txt)

