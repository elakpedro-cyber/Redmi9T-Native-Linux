/* Query the existing SimpleDRM pipeline and allocate one unused dumb buffer. */
#include <errno.h>
#include <fcntl.h>
#include <linux/kd.h>
#include <linux/vt.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <drm/drm.h>
#include <drm/drm_mode.h>

#define PTR(p) ((uintptr_t)(p))

static void check(int rc, const char *what)
{
    if (rc < 0) {
        perror(what);
        exit(1);
    }
}

int main(int argc, char **argv)
{
    if (argc == 2 && strcmp(argv[1], "--gpu-topology") == 0) {
        const char *paths[] = {"/dev/dri/card0", "/dev/dri/card1", "/dev/dri/renderD128"};
        for (unsigned i = 0; i < sizeof(paths) / sizeof(paths[0]); i++) {
            int fd = open(paths[i], O_RDONLY | O_CLOEXEC);
            check(fd, paths[i]);
            char driver[64] = {0};
            struct drm_version version = {.name_len = sizeof(driver) - 1, .name = driver};
            struct drm_get_cap prime = {.capability = DRM_CAP_PRIME};
            struct drm_mode_card_res res = {0};
            check(ioctl(fd, DRM_IOCTL_VERSION, &version), "DRM version");
            check(ioctl(fd, DRM_IOCTL_GET_CAP, &prime), "DRM_CAP_PRIME");
            printf("%s driver=%s prime_import=%u prime_export=%u\n", paths[i], driver,
                   !!(prime.value & DRM_PRIME_CAP_IMPORT), !!(prime.value & DRM_PRIME_CAP_EXPORT));
            if (i < 2) {
                int rc = ioctl(fd, DRM_IOCTL_MODE_GETRESOURCES, &res);
                if (rc < 0 && i == 1 && errno == EOPNOTSUPP)
                    puts("  GETRESOURCES: EOPNOTSUPP (render-only)");
                else {
                    check(rc, "GETRESOURCES");
                    printf("  crtc=%u connectors=%u encoders=%u\n",
                           res.count_crtcs, res.count_connectors, res.count_encoders);
                }
            }
            close(fd);
        }
        return 0;
    }
    if (argc == 2 && strcmp(argv[1], "--restore-tty1") == 0) {
        int temporary = open("/dev/tty2", O_RDWR | O_CLOEXEC | O_NOCTTY);
        int original = open("/dev/tty1", O_RDWR | O_CLOEXEC | O_NOCTTY);
        struct vt_mode mode = {.mode = VT_AUTO};
        check(temporary, "restore open tty2");
        check(original, "restore open tty1");
        check(ioctl(temporary, VT_SETMODE, &mode), "restore VT_AUTO tty2");
        check(ioctl(temporary, KDSETMODE, KD_TEXT), "restore KD_TEXT tty2");
        check(ioctl(original, VT_ACTIVATE, 1), "restore activate tty1");
        check(ioctl(original, VT_WAITACTIVE, 1), "restore wait tty1");
        close(temporary);
        if (ioctl(original, VT_DISALLOCATE, 2) < 0) {
            if (errno != EBUSY)
                check(-1, "release temporary tty2");
            fputs("Temporary tty2 is still busy; tty1 is restored in text mode\n", stderr);
        } else {
            puts("Released temporary tty2");
        }
        close(original);
        puts("Restored tty1 and reset tty2 to KD_TEXT/VT_AUTO");
        return 0;
    }
    if (argc != 2 || strncmp(argv[1], "/dev/tty", 8) != 0)
        return 2;

    int vt = open(argv[1], O_RDONLY | O_CLOEXEC | O_NOCTTY);
    check(vt, "open VT");
    int kd_mode, fb = -1;
    struct vt_mode vt_mode;
    struct vt_stat vt_state;
    check(ioctl(vt, KDGETMODE, &kd_mode), "KDGETMODE");
    check(ioctl(vt, VT_GETMODE, &vt_mode), "VT_GETMODE");
    check(ioctl(vt, VT_GETSTATE, &vt_state), "VT_GETSTATE");
    printf("VT active=%u kd_mode=%d vt_mode=%u mask=0x%04x\n",
           vt_state.v_active, kd_mode, vt_mode.mode, vt_state.v_state);
    close(vt);

    /* FBIOGET_CON2FBMAP reads the console-to-fb mapping. */
    struct { uint32_t console, framebuffer; } map = {vt_state.v_active, 0};
    int f = open("/dev/fb0", O_RDONLY | O_CLOEXEC);
    check(f, "open fb0");
    check(ioctl(f, 0x460f, &map), "FBIOGET_CON2FBMAP");
    fb = map.framebuffer;
    printf("fbcon map: tty%u -> fb%d\n", map.console, fb);
    close(f);

    int fd = open("/dev/dri/card0", O_RDWR | O_CLOEXEC);
    check(fd, "open DRM");
    char driver[64] = {0};
    struct drm_version version = {.name_len = sizeof(driver) - 1, .name = driver};
    check(ioctl(fd, DRM_IOCTL_VERSION, &version), "DRM version");
    printf("DRM driver=%s\n", driver);
    if (strcmp(driver, "simpledrm") != 0 || fb != 0 || vt_state.v_active != 1 ||
        kd_mode != KD_TEXT || vt_mode.mode != VT_AUTO || (vt_state.v_state & (1 << 2)))
        return 3;

    uint32_t crtcs[8], conns[8], encoders[8];
    struct drm_mode_card_res resources = {
        .crtc_id_ptr = PTR(crtcs), .connector_id_ptr = PTR(conns),
        .encoder_id_ptr = PTR(encoders), .count_crtcs = 8,
        .count_connectors = 8, .count_encoders = 8,
    };
    check(ioctl(fd, DRM_IOCTL_MODE_GETRESOURCES, &resources), "GETRESOURCES");
    printf("resources: crtcs=%u connectors=%u encoders=%u\n",
           resources.count_crtcs, resources.count_connectors, resources.count_encoders);
    if (resources.count_crtcs != 1 || resources.count_connectors != 1 ||
        resources.count_encoders != 1)
        return 4;
    struct drm_mode_crtc crtc = {.crtc_id = crtcs[0]};
    check(ioctl(fd, DRM_IOCTL_MODE_GETCRTC, &crtc), "GETCRTC");
    printf("CRTC %u fb=%u mode_valid=%u mode=%ux%u clock=%u htotal=%u vtotal=%u flags=0x%x\n",
           crtc.crtc_id, crtc.fb_id, crtc.mode_valid, crtc.mode.hdisplay, crtc.mode.vdisplay,
           crtc.mode.clock, crtc.mode.htotal, crtc.mode.vtotal, crtc.mode.flags);
    struct drm_mode_modeinfo modes[8];
    struct drm_mode_get_connector conn = {
        .connector_id = conns[0], .modes_ptr = PTR(modes), .count_modes = 8,
    };
    /* A nonzero mode capacity avoids requesting a forced connector probe. */
    check(ioctl(fd, DRM_IOCTL_MODE_GETCONNECTOR, &conn), "GETCONNECTOR");
    printf("connector %u type=%u status=%u encoder=%u modes=%u\n",
           conn.connector_id, conn.connector_type, conn.connection, conn.encoder_id, conn.count_modes);
    if (conn.count_modes != 1 || !crtc.mode_valid ||
        crtc.mode.hdisplay != 1080 || crtc.mode.vdisplay != 2340 ||
        modes[0].hdisplay != crtc.mode.hdisplay || modes[0].vdisplay != crtc.mode.vdisplay ||
        modes[0].clock != crtc.mode.clock || modes[0].htotal != crtc.mode.htotal ||
        modes[0].vtotal != crtc.mode.vtotal || modes[0].flags != crtc.mode.flags)
        return 5;

    struct drm_set_client_cap cap = {.capability = DRM_CLIENT_CAP_UNIVERSAL_PLANES, .value = 1};
    check(ioctl(fd, DRM_IOCTL_SET_CLIENT_CAP, &cap), "UNIVERSAL_PLANES");
    uint32_t planes[8];
    struct drm_mode_get_plane_res pr = {.plane_id_ptr = PTR(planes), .count_planes = 8};
    check(ioctl(fd, DRM_IOCTL_MODE_GETPLANERESOURCES, &pr), "GETPLANERESOURCES");
    if (pr.count_planes != 1)
        return 6;
    uint32_t formats[64];
    struct drm_mode_get_plane plane = {
        .plane_id = planes[0], .format_type_ptr = PTR(formats), .count_format_types = 64,
    };
    check(ioctl(fd, DRM_IOCTL_MODE_GETPLANE, &plane), "GETPLANE");
    printf("plane %u CRTC=%u fb=%u formats=%u\n", plane.plane_id, plane.crtc_id,
           plane.fb_id, plane.count_format_types);
    int xrgb = 0;
    for (uint32_t i = 0; i < plane.count_format_types && i < 64; i++) {
        printf("format=%c%c%c%c\n", formats[i] & 255, formats[i] >> 8 & 255,
               formats[i] >> 16 & 255, formats[i] >> 24 & 255);
        xrgb |= formats[i] == 0x34325258; /* XR24 */
    }
    if (!xrgb || plane.crtc_id != crtc.crtc_id || plane.fb_id != crtc.fb_id)
        return 7;
    struct drm_get_cap dumb = {.capability = DRM_CAP_DUMB_BUFFER};
    check(ioctl(fd, DRM_IOCTL_GET_CAP, &dumb), "GET_CAP DUMB");
    if (!dumb.value)
        return 8;
    check(ioctl(fd, DRM_IOCTL_SET_MASTER), "SET_MASTER");
    puts("DRM master acquired temporarily");
    struct drm_mode_create_dumb bo = {.width = 1080, .height = 2340, .bpp = 32};
    check(ioctl(fd, DRM_IOCTL_MODE_CREATE_DUMB, &bo), "CREATE_DUMB");
    printf("unused dumb buffer: pitch=%u size=%llu\n", bo.pitch, (unsigned long long)bo.size);
    struct drm_mode_destroy_dumb destroy = {.handle = bo.handle};
    check(ioctl(fd, DRM_IOCTL_MODE_DESTROY_DUMB, &destroy), "DESTROY_DUMB");
    check(ioctl(fd, DRM_IOCTL_DROP_MASTER), "DROP_MASTER");
    close(fd);
    return 0;
}
