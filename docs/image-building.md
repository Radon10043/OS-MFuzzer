# Cuttlefish

Args:
- VERSION: which version of cuttlefish to be installed.

Command:
```bash
docker build \
    -t cuttlefish \
    --network host \
    --build-arg VERSION=v1.16.0 \
    -f Dockerfile.cuttlefish .
```

NOTE:
- If `VERSION` is not specified, default to v1.15.0.
- You can delete the flag `--network host` if proxy is unnecessary for you.
- `cuttlefish.patch` patch the cuttlefish repository to perserve `http_proxy` and `https_proxy` during installation. But it is unnecessary if version >= v1.17.0.

# SyzMeta

Todo.

# Some useful links

- [github/android-cuttlefish](https://github.com/google/android-cuttlefish)