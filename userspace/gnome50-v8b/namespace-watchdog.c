#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <sched.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mount.h>
#include <sys/signalfd.h>
#include <sys/timerfd.h>
#include <sys/wait.h>
#include <unistd.h>

static unsigned char stack[1024 * 1024] __attribute__((aligned(16)));
static sigset_t original_mask;

static int run_child(void *data)
{
    char **args = data;
    if (mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL) < 0) {
        perror("private mount namespace");
        return 126;
    }
    if (getenv("LEMON_WATCHDOG_HEARTBEAT")) {
        int input = open("/dev/null", O_RDONLY | O_CLOEXEC);
        if (input < 0 || dup2(input, STDIN_FILENO) < 0)
            return 126;
        if (input != STDIN_FILENO)
            close(input);
    }
    sigprocmask(SIG_SETMASK, &original_mask, NULL);
    execvp(args[0], args);
    perror("execvp");
    return 126;
}

int main(int argc, char **argv)
{
    struct itimerspec limit = {0};
    sigset_t mask;
    int status;
    int result = 125;
    char *end;
    long seconds;

    if (argc < 3)
        return 125;
    seconds = strtol(argv[1], &end, 10);
    if (*end || seconds < 1 || seconds > 120)
        return 125;
    limit.it_value.tv_sec = seconds;

    sigemptyset(&mask);
    sigaddset(&mask, SIGCHLD);
    sigaddset(&mask, SIGINT);
    sigaddset(&mask, SIGTERM);
    sigaddset(&mask, SIGHUP);
    if (sigprocmask(SIG_BLOCK, &mask, &original_mask) < 0)
        return 125;
    int signal_fd = signalfd(-1, &mask, SFD_CLOEXEC);
    int timer_fd = timerfd_create(CLOCK_MONOTONIC, TFD_CLOEXEC);
    bool heartbeat = getenv("LEMON_WATCHDOG_HEARTBEAT") != NULL;
    int heartbeat_fd = heartbeat ? timerfd_create(CLOCK_MONOTONIC, TFD_CLOEXEC) : -1;
    struct itimerspec lease = {.it_value.tv_sec = 8};
    if (signal_fd < 0 || timer_fd < 0 ||
        (heartbeat && (heartbeat_fd < 0 ||
                       timerfd_settime(heartbeat_fd, 0, &lease, NULL) < 0)) ||
        timerfd_settime(timer_fd, 0, &limit, NULL) < 0) {
        perror("watchdog setup");
        return 125;
    }

    pid_t child = clone(run_child, stack + sizeof(stack),
                        CLONE_NEWPID | CLONE_NEWNS | CLONE_NEWNET | SIGCHLD, argv + 2);
    if (child < 0) {
        perror("clone");
        return 125;
    }
    fprintf(stderr, "WATCHDOG supervisor=%d namespace_init=%d limit=%ld\n",
            getpid(), child, seconds);

    struct pollfd fds[] = {
        {timer_fd, POLLIN, 0}, {signal_fd, POLLIN, 0},
        {heartbeat ? STDIN_FILENO : -1, POLLIN, 0}, {heartbeat_fd, POLLIN, 0}
    };
    for (;;) {
        int ready = poll(fds, sizeof(fds) / sizeof(fds[0]), -1);
        if (ready < 0 && errno == EINTR)
            continue;
        if (ready < 0)
            break;
        if (fds[0].revents) {
            fprintf(stderr, "WATCHDOG deadline\n");
            result = 124;
            break;
        }
        if (fds[3].revents) {
            fprintf(stderr, "WATCHDOG heartbeat expired\n");
            break;
        }
        if (fds[2].revents) {
            char bytes[128];
            if (read(STDIN_FILENO, bytes, sizeof(bytes)) <= 0 ||
                timerfd_settime(heartbeat_fd, 0, &lease, NULL) < 0) {
                fprintf(stderr, "WATCHDOG heartbeat disconnected\n");
                break;
            }
        }
        if (!fds[1].revents)
            continue;
        struct signalfd_siginfo info;
        if (read(signal_fd, &info, sizeof(info)) != sizeof(info))
            break;
        if (info.ssi_signo != SIGCHLD) {
            fprintf(stderr, "WATCHDOG aborted by signal %u\n", info.ssi_signo);
            result = 128 + info.ssi_signo;
            break;
        }
        if (waitpid(child, &status, WNOHANG) == child)
            return WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
    }

    /* The child is PID 1 of the private namespace. Its death kills all descendants. */
    if (kill(child, SIGKILL) < 0 && errno != ESRCH)
        perror("kill namespace init");
    while (waitpid(child, &status, 0) < 0 && errno == EINTR)
        ;
    return result;
}
