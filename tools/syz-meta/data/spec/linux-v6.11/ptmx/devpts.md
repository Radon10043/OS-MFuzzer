[ ![Logo](../_static/logo.svg) ](../index.html)

# [The Linux Kernel](../index.html)

6.11.0

### Quick search

### Contents

  * [Development process](../process/development-process.html)
  * [Submitting patches](../process/submitting-patches.html)
  * [Code of conduct](../process/code-of-conduct.html)
  * [Maintainer handbook](../maintainer/index.html)
  * [All development-process docs](../process/index.html)

  * [Core API](../core-api/index.html)
  * [Driver APIs](../driver-api/index.html)
  * [Subsystems](../subsystem-apis.html)
    * [Core subsystems](../subsystem-apis.html#core-subsystems)
    * [Human interfaces](../subsystem-apis.html#human-interfaces)
    * [Networking interfaces](../subsystem-apis.html#networking-interfaces)
    * [Storage interfaces](../subsystem-apis.html#storage-interfaces)
      * [Filesystems in the Linux kernel](index.html)
      * [Block](../block/index.html)
      * [CD-ROM](../cdrom/index.html)
      * [SCSI Subsystem](../scsi/index.html)
      * [TCM Virtual Device](../target/index.html)
    * [Other subsystems](../subsystem-apis.html#other-subsystems)
  * [Locking](../locking/index.html)

  * [Licensing rules](../process/license-rules.html)
  * [Writing documentation](../doc-guide/index.html)
  * [Development tools](../dev-tools/index.html)
  * [Testing guide](../dev-tools/testing-overview.html)
  * [Hacking guide](../kernel-hacking/index.html)
  * [Tracing](../trace/index.html)
  * [Fault injection](../fault-injection/index.html)
  * [Livepatching](../livepatch/index.html)
  * [Rust](../rust/index.html)

  * [Administration](../admin-guide/index.html)
  * [Build system](../kbuild/index.html)
  * [Reporting issues](../admin-guide/reporting-issues.html)
  * [Userspace tools](../tools/index.html)
  * [Userspace API](../userspace-api/index.html)

  * [Firmware](../firmware-guide/index.html)
  * [Firmware and Devicetree](../devicetree/index.html)

  * [CPU architectures](../arch/index.html)

  * [Unsorted documentation](../staging/index.html)

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

(C)The kernel development community. | Powered by [Sphinx 5.3.0](https://www.sphinx-doc.org/) & [Alabaster 0.7.16](https://alabaster.readthedocs.io) | [Page source](../_sources/filesystems/devpts.rst.txt)

