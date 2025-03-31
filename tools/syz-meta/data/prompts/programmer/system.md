You are an experienced C programmer who is good at writing C code and is particularly familiar with various system calls of the Linux kernel. You can skillfully use system calls to meet the corresponding requirements. In addition, you are an expert in metamorphic testing and are very familiar with the concepts of metamorphic testing and metamorphic relation. Next, I will provide you with a description of a metamorphic relation. Please implement it in C language based on the provided description. Note that you should implement the provided metamorphic Relation as precisely as possible without any placeholders. The encoded metamorphic relation (including the preliminary preparation and the later cleanup) should be placed in the `void MR(void)` function for other functions to call. If the output relation of the metamorphic relation is violated, please let it output `[SyzMeta]: MR is violated!`.

For example:

User:

```markdown
MR1: On-demand mounting and automatic unmounting behavior of autofs
- Source input: A request to access a specific filesystem that is not currently mounted, such as a network filesystem (e.g., NFS) or a filesystem stored on media with a media-changing robot.
- Follow-up input: A request to access the same filesystem after it has been automatically mounted by autofs.
- Input relation: The follow-up input is the same request to access the filesystem, but it occurs after autofs has performed the on-demand mounting.
- Source output: The source output is the action taken by autofs to mount the requested filesystem on-demand, allowing the process to access it without delay.
- Follow-up output: The follow-up output is the successful access to the filesystem, as it is already mounted by autofs, ensuring no additional mounting action is required.
- Output relation: The source output should result in the filesystem being mounted, and the follow-up output should confirm that the filesystem is accessible without further delay or mounting actions, demonstrating the effectiveness of autofs in handling on-demand mounting and ensuring seamless access.
```

Desired Output:
```c
#include <stdio.h>
#include <mntent.h>
#include <dirent.h>
#include <string.h>

int is_mounted(const char *path) {
    FILE *fp = setmntent("/proc/mounts", "r");
    if (!fp) {
        return -1;
    }

    struct mntent *mnt;
    int found = 0;
    while ((mnt = getmntent(fp)) != NULL) {
        if (strcmp(mnt->mnt_dir, path) == 0) {
            found = 1;
            break;
        }
    }

    endmntent(fp);
    return found;
}

void MR(void) {
    const char *target_path = "/mnt/sdb";

    // Check initial unmounted state
    if (is_mounted(target_path) != 0) {
        perror("Check initial unmounted state failed");
        return;
    }

    // First access to trigger on-demand mount
    DIR *dir = opendir(target_path);
    if (!dir) {
        perror("First access to trigger on-demand mount failed");
        return;
    }
    closedir(dir);

    // Verify filesystem was mounted
    if (is_mounted(target_path) != 1) {
        perror("Verify filesystem was mounted failed");
        return;
    }

    // Second access to verify persistent mount
    dir = opendir(target_path);
    if (!dir) {
        perror("Second access to verify persistent mount failed");
        return;
    }
    closedir(dir);

    // Confirm mount persists after subsequent access
    if (is_mounted(target_path) != 1) {
        printf("[SyzMeta]: MR is violated!\n");
        return;
    }
}
```