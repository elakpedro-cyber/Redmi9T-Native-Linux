/* Preserve variadic arguments, including FP registers, before tail-calling Wayland. */
.text
.global wl_proxy_marshal_flags
.type wl_proxy_marshal_flags, %function
wl_proxy_marshal_flags:
    sub sp, sp, #208
    stp x0, x1, [sp, #0]
    stp x2, x3, [sp, #16]
    stp x4, x5, [sp, #32]
    stp x6, x7, [sp, #48]
    str x30, [sp, #64]
    stp q0, q1, [sp, #80]
    stp q2, q3, [sp, #112]
    stp q4, q5, [sp, #144]
    stp q6, q7, [sp, #176]
    bl lemon_trace_wayland
    mov x16, x0
    ldp x0, x1, [sp, #0]
    ldp x2, x3, [sp, #16]
    ldp x4, x5, [sp, #32]
    ldp x6, x7, [sp, #48]
    ldr x30, [sp, #64]
    ldp q0, q1, [sp, #80]
    ldp q2, q3, [sp, #112]
    ldp q4, q5, [sp, #144]
    ldp q6, q7, [sp, #176]
    add sp, sp, #208
    br x16
.size wl_proxy_marshal_flags, .-wl_proxy_marshal_flags
.section .note.GNU-stack,"",%progbits
