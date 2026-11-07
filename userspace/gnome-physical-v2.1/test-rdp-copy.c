#include <assert.h>
#include <string.h>
#include <stdio.h>
#include <freerdp/codec/color.h>
int main(void)
{
    BYTE src[16] = {1,2,3,255, 4,5,6,255, 7,8,9,255, 10,11,12,255};
    BYTE dst[16] = {0};
    assert(freerdp_image_copy(dst, PIXEL_FORMAT_BGRA32, 8, 0, 0, 2, 2,
                            src, PIXEL_FORMAT_BGRA32, 8, 0, 0, NULL, 0));
    assert(memcmp(src, dst, sizeof(src)) == 0);
    puts("RDP_COPY_PIXELS_UNCHANGED_PASS");
    return 0;
}
