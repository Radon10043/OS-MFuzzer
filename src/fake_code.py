FAKE_SYZ_MR = """
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <fcntl.h>
#include <signal.h>
#include <sys/wait.h>
#include <errno.h>
#include <sys/mount.h>

// Helper function to create a directory path recursively, renamed to avoid conflicts.
static int mr1_mkdir_p(const char* path)
{
	char* p, * temp_path;
	int ret = 0;

	temp_path = strdup(path);
	if (temp_path == NULL) {
		perror("[SyzMeta]: strdup failed");
		return -1;
	}

	// Start from the first character after the initial '/'
	for (p = temp_path + 1; *p; p++) {
		if (*p == '/') {
			*p = '\0';
			if (mkdir(temp_path, 0755) != 0 && errno != EEXIST) {
				perror("[SyzMeta]: mkdir failed");
				ret = -1;
				break;
			}
			*p = '/';
		}
	}
	if (ret == 0 && mkdir(temp_path, 0755) != 0 && errno != EEXIST) {
		perror("[SyzMeta]: mkdir failed");
		ret = -1;
	}
	free(temp_path);
	return ret;
}

// Helper function to write content to a file, renamed to avoid conflicts.
static int mr1_write_file(const char* path, const char* content)
{
	int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
	if (fd == -1) {
		perror("[SyzMeta]: open file for writing failed");
		return -1;
	}
	ssize_t written = write(fd, content, strlen(content));
	close(fd);
	if (written != (ssize_t)strlen(content)) {
		fprintf(stderr, "[SyzMeta]: short write to file\n");
		return -1;
	}
	return 0;
}

// The MR implementation
static long syz_mr(volatile long a0, volatile long a1)
{
	// The input parameters are unused in this MR, but included for compatibility.
	(void)a0;
	(void)a1;

	// Check for root privileges, which are required for mount operations
	if (getuid() != 0) {
		fprintf(stderr, "[SyzMeta]: This test must be run as root.\n");
		return -1;
	}

	// Define constants for paths and commands
	const char* automount_path = "/usr/sbin/automount";
	const char* map_file = "/tmp/auto.mr1.map";
	const char* mnt_point = "/tmp/auto.mr1.mnt";
	const char* src_dir = "/tmp/serverA/export/proj";
	const char* fup_dir = "/tmp/serverB/export/proj_new";
	const char* access_path = "/tmp/auto.mr1.mnt/proj";
	const int timeout = 3; // autofs timeout in seconds

	// 1. Preliminary preparation and cleanup from previous runs
	char command[256];
	snprintf(command, sizeof(command), "umount -l %s >/dev/null 2>&1", access_path);
	if (system(command)) {
		// Use result to suppress -Wunused-result. Failure is ok for cleanup.
	}
	snprintf(command, sizeof(command), "umount -l %s >/dev/null 2>&1", mnt_point);
	if (system(command)) {
		// Use result to suppress -Wunused-result. Failure is ok for cleanup.
	}

	// Create directories for the test
	if (mr1_mkdir_p(mnt_point) || mr1_mkdir_p(src_dir) || mr1_mkdir_p(fup_dir)) {
		fprintf(stderr, "[SyzMeta]: Failed to create necessary directories.\n");
		return -1;
	}

	// --- Source Execution ---

	// 2.1. Create the initial automount map file for the source execution
	char map_content_src[256];
	snprintf(map_content_src, sizeof(map_content_src), "proj -fstype=none,bind :%s", src_dir);
	if (mr1_write_file(map_file, map_content_src) != 0) {
		return -1;
	}

	// 2.2. Fork and execute the automount daemon
	pid_t automount_pid = fork();
	if (automount_pid == -1) {
		perror("[SyzMeta]: fork failed");
		return -1;
	}

	if (automount_pid == 0) { // Child process
		int fd = open("/dev/null", O_WRONLY);
		if (fd != -1) {
			dup2(fd, 1);
			dup2(fd, 2);
			close(fd);
		}
		char timeout_str[16];
		snprintf(timeout_str, sizeof(timeout_str), "--timeout=%d", timeout);
		execl(automount_path, "automount", "--foreground", timeout_str, mnt_point, "file", map_file, (char*)NULL);
		perror("[SyzMeta]: execl automount failed");
		exit(1);
	}

	sleep(2); // Give automount time to start

	// 2.3. Trigger the source mount and get the output
	struct stat st_src;
	if (stat(access_path, &st_src) != 0) {
		perror("[SyzMeta]: Source stat failed, mount was not triggered");
		kill(automount_pid, SIGKILL);
		waitpid(automount_pid, NULL, 0);
		return -1;
	}
	ino_t ino_src = st_src.st_ino;

	// --- Follow-up Execution ---

	// 3.1. Wait for the automatic unmount
	sleep(timeout + 1);

	struct stat st_check;
	if (stat(access_path, &st_check) == 0) {
		if (umount2(access_path, MNT_FORCE) != 0) {
			perror("[SyzMeta]: Failed to explicitly unmount for follow-up");
			kill(automount_pid, SIGKILL);
			waitpid(automount_pid, NULL, 0);
			return -1;
		}
		sleep(1);
	}

	// 3.2. Update the automount map file
	char map_content_fup[256];
	snprintf(map_content_fup, sizeof(map_content_fup), "proj -fstype=none,bind :%s", fup_dir);
	if (mr1_write_file(map_file, map_content_fup) != 0) {
		kill(automount_pid, SIGKILL);
		waitpid(automount_pid, NULL, 0);
		return -1;
	}

	// 3.3. Trigger a map reload
	if (kill(automount_pid, SIGHUP) != 0) {
		perror("[SyzMeta]: Failed to send SIGHUP to automount");
		kill(automount_pid, SIGKILL);
		waitpid(automount_pid, NULL, 0);
		return -1;
	}
	sleep(1); // Give automount time to reload

	// 3.4. Trigger the follow-up mount and get the output
	struct stat st_fup;
	if (stat(access_path, &st_fup) != 0) {
		perror("[SyzMeta]: Follow-up stat failed");
		kill(automount_pid, SIGKILL);
		waitpid(automount_pid, NULL, 0);
		return -1;
	}
	ino_t ino_fup = st_fup.st_ino;

	// 4. Output Relation Check
	if (ino_src == ino_fup) {
		fprintf(stderr, "[SyzMeta]: MR is violated!\n");
	}

	// --- Cleanup ---
	kill(automount_pid, SIGKILL);
	waitpid(automount_pid, NULL, 0);

	snprintf(command, sizeof(command), "umount -l %s >/dev/null 2>&1", mnt_point);
	if (system(command)) {
		// Use result to suppress -Wunused-result. Failure is ok for cleanup.
	}
	remove(map_file);
	rmdir(mnt_point);
	rmdir(src_dir);
	rmdir("/tmp/serverA/export");
	rmdir("/tmp/serverA");
	rmdir(fup_dir);
	rmdir("/tmp/serverB/export");
	rmdir("/tmp/serverB");

	return 0;
}
"""