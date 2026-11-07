#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/kd.h>
#include <linux/vt.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <time.h>
#include <unistd.h>

static void fail(const char *operation)
{
    perror(operation);
    exit(1);
}

static long long monotonic_ms(void)
{
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now))
        fail("clock");
    return now.tv_sec * 1000LL + now.tv_nsec / 1000000;
}

static int holders(int target)
{
    DIR *proc = opendir("/proc");
    struct dirent *process;
    int count = 0;
    if (!proc)
        fail("open proc");
    while ((process = readdir(proc))) {
        char *end;
        long pid = strtol(process->d_name, &end, 10);
        if (*end || pid < 1 || pid == getpid())
            continue;
        char path[128], line[4096];
        snprintf(path, sizeof(path), "/proc/%ld/stat", pid);
        FILE *file = fopen(path, "r");
        if (file) {
            if (fgets(line, sizeof(line), file)) {
                char state, *fields = strrchr(line, ')');
                int parent, group, session;
                long long tty;
                if (fields && sscanf(fields + 1, " %c %d %d %d %lld",
                                     &state, &parent, &group, &session, &tty) == 5 &&
                    tty == (long long)makedev(4, target)) {
                    printf("VT_HOLDER pid=%ld controlling_tty=%d\n", pid, target);
                    count++;
                }
            }
            fclose(file);
        }
        snprintf(path, sizeof(path), "/proc/%ld/fd", pid);
        DIR *fds = opendir(path);
        if (!fds) {
            if (errno != ENOENT && errno != ESRCH)
                fail("inspect process fds");
            continue;
        }
        struct dirent *entry;
        while ((entry = readdir(fds))) {
            struct stat st;
            if (fstatat(dirfd(fds), entry->d_name, &st, 0) == 0 && S_ISCHR(st.st_mode)) {
                if (st.st_rdev == makedev(4, target)) {
                    printf("VT_HOLDER pid=%ld fd=%s tty=%d\n", pid, entry->d_name, target);
                    count++;
                } else if (st.st_rdev == makedev(226, 0)) {
                    printf("DRM_HOLDER pid=%ld fd=%s card=0\n", pid, entry->d_name);
                    count++;
                }
            }
        }
        closedir(fds);
    }
    closedir(proc);
    return count;
}

int main(int argc, char **argv)
{
    if (argc != 3 || strcmp(argv[1], "1") || strcmp(argv[2], "2")) {
        fprintf(stderr, "Usage: vt-cleanup 1 2 (owned test VT2 -> original VT1)\n");
        return 1;
    }
    if (holders(2)) {
        fputs("VT_BUSY_OWNERS_REMAIN: no modes or ownership changed\n", stderr);
        return 2;
    }
    int original = open("/dev/tty1", O_RDWR | O_CLOEXEC | O_NOCTTY);
    if (original < 0)
        fail("open tty1");
    struct vt_stat state;
    if (ioctl(original, VT_GETSTATE, &state))
        fail("VT_GETSTATE");
    if (state.v_active != 1 && state.v_active != 2) {
        fputs("Unexpected active VT, refusing switch\n", stderr);
        return 2;
    }
    if (state.v_active == 2) {
        int temporary = open("/dev/tty2", O_RDWR | O_CLOEXEC | O_NOCTTY);
        struct vt_mode mode = {.mode = VT_AUTO};
        if (temporary < 0 || ioctl(temporary, VT_SETMODE, &mode) ||
            ioctl(temporary, KDSETMODE, KD_TEXT))
            fail("restore owned tty2");
        close(temporary);
        if (ioctl(original, VT_ACTIVATE, 1) || ioctl(original, VT_WAITACTIVE, 1))
            fail("activate tty1");
    }
    int kd;
    struct vt_mode mode;
    if (ioctl(original, KDGETMODE, &kd) || ioctl(original, VT_GETMODE, &mode))
        fail("verify original VT");
    if (kd != KD_TEXT || mode.mode != VT_AUTO) {
        fputs("Original VT1 is not KD_TEXT/VT_AUTO\n", stderr);
        return 2;
    }
    puts("TTY1_RESTORED");

    /* Some kernels compare an unallocated VC (NULL) to an empty selection
     * (also NULL), returning EBUSY on a second VT_DISALLOCATE. */
    if (access("/sys/class/vc", F_OK) == 0 &&
        access("/sys/class/vc/vcs2", F_OK) < 0 && errno == ENOENT) {
        puts("VT2_ALREADY_RELEASED");
        close(original);
        return 0;
    }

    long long deadline = monotonic_ms() + 2500;
    unsigned busy = 0;
    for (;;) {
        /* GETSTATE reads port references without reopening the temporary TTY.
         * Last close may still be waiting for the kernel's release_one_tty work. */
        if (ioctl(original, VT_GETSTATE, &state))
            fail("poll VT state");
        if (!(state.v_state & (1U << 2))) {
            if (ioctl(original, VT_DISALLOCATE, 2) == 0) {
                printf("VT2_RELEASED deferred_checks=%u\n", busy);
                close(original);
                return 0;
            }
            if (errno != EBUSY)
                fail("VT_DISALLOCATE");
        }
        if (monotonic_ms() >= deadline) {
            holders(2);
            fputs("VT2_RETAINED_BUSY: tty1 restored; no forced release\n", stderr);
            close(original);
            return 2;
        }
        struct timespec interval = {.tv_nsec = 10000000};
        nanosleep(&interval, NULL);
        busy++;
    }
}
