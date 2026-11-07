#include <errno.h>
#include <fcntl.h>
#include <linux/kd.h>
#include <linux/vt.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <sys/wait.h>
#include <unistd.h>

static void check(int condition, const char *name)
{
    if (!condition) {
        perror(name);
        exit(1);
    }
}

static int cleanup(void)
{
    pid_t child = fork();
    check(child >= 0, "fork");
    if (!child) {
        execl("/vt-cleanup", "vt-cleanup", "1", "2", NULL);
        _exit(127);
    }
    int status;
    check(waitpid(child, &status, 0) == child, "wait");
    return WIFEXITED(status) ? WEXITSTATUS(status) : 127;
}

int main(void)
{
    setbuf(stdout, NULL);
    int original = open("/dev/tty1", O_RDWR | O_NOCTTY);
    check(original >= 0, "open original");
    check(ioctl(original, VT_ACTIVATE, 1) == 0, "activate original");
    check(ioctl(original, VT_WAITACTIVE, 1) == 0, "wait original");
    int temporary = open("/dev/tty2", O_RDWR | O_NOCTTY);
    check(temporary >= 0, "open temporary");
    check(cleanup() == 2, "cleanup must refuse a live owner");
    puts("PASS: live VT2 fd owner refused");
    close(temporary);
    check(cleanup() == 0, "release after owner exits");
    check(cleanup() == 0, "idempotent cleanup");
    puts("PASS: owner exit, deferred references and idempotence");

    unsigned races = 0;
    for (int attempt = 0; attempt < 32; attempt++) {
        temporary = open("/dev/tty2", O_RDWR | O_NOCTTY);
        check(temporary >= 0, "open for old pattern");
        close(temporary);
        if (ioctl(original, VT_DISALLOCATE, 2) < 0) {
            check(errno == EBUSY, "expected EBUSY");
            races++;
        }
        check(cleanup() == 0, "v2 cleanup after old pattern");
    }
    printf("V1_IMMEDIATE_CLOSE_EBUSY=%u/32\n", races);
    if (!races)
        puts("NOTE: close race not reproduced on this VM kernel/scheduling");

    temporary = open("/dev/tty2", O_RDWR | O_NOCTTY);
    check(temporary >= 0, "allocate test VT");
    check(ioctl(temporary, KDSETMODE, KD_GRAPHICS) == 0, "graphics software mode");
    check(ioctl(original, VT_ACTIVATE, 2) == 0, "activate test VT");
    check(ioctl(original, VT_WAITACTIVE, 2) == 0, "wait test VT");
    close(temporary);
    check(cleanup() == 0, "restore inactive ownerless graphics VT");
    struct vt_stat state;
    int kd;
    check(ioctl(original, VT_GETSTATE, &state) == 0 && state.v_active == 1, "final VT1");
    check(ioctl(original, KDGETMODE, &kd) == 0 && kd == KD_TEXT, "final text mode");
    check(cleanup() == 0, "final repeated cleanup");
    puts("ALL_VT_TESTS_PASS");
    return 0;
}
