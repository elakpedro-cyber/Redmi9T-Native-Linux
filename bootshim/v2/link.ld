ENTRY(_start)
SECTIONS {
    . = 0;
    .text : { KEEP(*(.text.header)) *(.text*) }
    .rodata : { *(.rodata*) }
    .data : { *(.data*) }
    .got : { *(.got*) }
    ASSERT(SIZEOF(.got) == 0, "GOT would prevent relocation")
    .payload : { *(.payload) }
    . = ALIGN(16);
    .bss : { *(.bss*) *(COMMON) }
    .stack : { *(.stack) }
    wrapper_end = .;
    /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
