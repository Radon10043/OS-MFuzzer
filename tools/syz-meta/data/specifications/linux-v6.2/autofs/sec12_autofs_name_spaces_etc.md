With bind mounts and name spaces it is possible for an autofs filesystem to appear at multiple places in one or more filesystem name spaces. For this to work sensibly, the autofs filesystem should always be mounted "shared". e.g.

```
mount --make-shared /autofs/mount/point
```

The automount daemon is only able to manage a single mount location for an autofs filesystem and if mounts on that are not ‘shared’, other locations will not behave as expected. In particular access to those other locations will likely result in the ELOOP error

```
Too many levels of symbolic links
```