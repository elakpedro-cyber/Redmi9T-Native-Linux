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
    msr daifset, #0xf
    isb
    mrs x10, CurrentEL
    cmp x10, #4
    b.eq .Lel1
    cmp x10, #8
    b.ne .Lbad_el
    mrs x11, sctlr_el2
    b .Lcheck_control
.Lel1:
    mrs x11, sctlr_el1
.Lcheck_control:
    tbnz x11, #0, .Lbad_control
    tbnz x11, #2, .Lbad_control
    adr x10, _start
    tst x10, #0xfff
    b.ne .Lbad_alignment
    adrp x9, boot_stack_end
    add x9, x9, :lo12:boot_stack_end
    mov sp, x9
    bl bridge
    msr daifset, #0xf
    isb
    mov x1, xzr
    mov x2, xzr
    mov x3, xzr
    mov x9, #0x80000000
    dsb sy
    ic iallu
    dsb sy
    isb
    br x9
.Lbad_el:
    mov x0, #11
    b halt
.Lbad_control:
    mov x0, #12
    b halt
.Lbad_alignment:
    mov x0, #32
    b halt

// Both helpers operate on physical-address ranges while stage-1 MMU is off.
// Firmware must permit VA cache maintenance and preserve coherent identity PA.
.global prepare_range_poc, clean_range_poc
.hidden prepare_range_poc, clean_range_poc
prepare_range_poc:
    dsb sy
    add x1, x0, x1
    mrs x2, ctr_el0
    ubfx x2, x2, #16, #4
    mov x3, #4
    lsl x3, x3, x2
    sub x4, x3, #1
    bic x0, x0, x4
.global prepare_range_poc_line
prepare_range_poc_line:
    dc civac, x0
    add x0, x0, x3
    cmp x0, x1
    b.lo prepare_range_poc_line
    dsb sy
    ret
clean_range_poc:
    dsb sy
    add x1, x0, x1
    mrs x2, ctr_el0
    ubfx x2, x2, #16, #4
    mov x3, #4
    lsl x3, x3, x2
    sub x4, x3, #1
    bic x0, x0, x4
.global clean_range_poc_line
clean_range_poc_line:
    dc cvac, x0
    add x0, x0, x3
    cmp x0, x1
    b.lo clean_range_poc_line
    dsb sy
    ret

.section .payload,"a"
.balign 16
.global native_image, native_image_end, native_dtb, native_dtb_end
.hidden native_image, native_image_end, native_dtb, native_dtb_end
native_image:
    .incbin "Image"
native_image_end:
.balign 8
native_dtb:
    .incbin "mainline.dtb"
native_dtb_end:
.section .stack,"aw",%nobits
.balign 16
    .space 16384
boot_stack_end:
