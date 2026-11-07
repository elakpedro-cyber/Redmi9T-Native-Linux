.section .text.header,"ax"
.global _start
_start:
    b entry
    nop
    .quad 0x80000
    .quad wrapper_end - _start
    .quad 0xa
    .quad 0, 0, 0
    .word 0x644d5241
    .word 0
entry:
    adrp x9, boot_stack_end
    add x9, x9, :lo12:boot_stack_end
    mov sp, x9
    bl bridge
    mov x1, xzr
    mov x2, xzr
    mov x3, xzr
    mov x9, #0x80000000
    dsb sy
    ic iallu
    dsb sy
    isb
    br x9

.section .payload,"a"
.balign 16
.global native_image, native_image_end, native_dtb, native_dtb_end
.hidden native_image, native_image_end, native_dtb, native_dtb_end
native_image:
    .incbin "Image"
native_image_end:
.balign 8
native_dtb:
    .incbin "mainline-v2.dtb"
native_dtb_end:
.section .stack,"aw",%nobits
.balign 16
    .space 16384
boot_stack_end:
