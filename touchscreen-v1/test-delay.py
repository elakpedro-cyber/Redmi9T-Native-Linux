from pathlib import Path
import re, subprocess, tempfile

header = Path(__file__).with_name('lemon-geni-delay.h').read_text()
header = re.sub(r'^#include <linux/[^>]+>\n', '', header, flags=re.M)
code = '#include <stdint.h>\n#include <assert.h>\n#include <errno.h>\n#include <stdio.h>\ntypedef uint32_t u32;\n' + header + r'''
int main(void) {
    u32 value = 0;
    assert(!lemon_geni_delay(0xffffffff, 200, 0, &value) && value == 0xfff32000);
    assert(!lemon_geni_delay(0, 1023, 1023, &value) && value == 0x000fffff);
    value = 0x12345678;
    assert(lemon_geni_delay(0, 1024, 0, &value) == -EINVAL && value == 0x12345678);
    assert(lemon_geni_delay(0, 0, 1024, &value) == -EINVAL && value == 0x12345678);
    puts("ARM64_GENI_RAW_COUNTER_PASS stock200 reserved_bits_preserved overflow_rejected");
}
'''
with tempfile.TemporaryDirectory() as directory:
    source = Path(directory) / 'test.c'
    source.write_text(code)
    exe = source.with_suffix('')
    subprocess.run(['aarch64-linux-gnu-gcc', '-O2', '-static', '-Wall', '-Wextra',
                    '-Werror', str(source), '-o', str(exe)], check=True)
    subprocess.run(['qemu-aarch64-static', str(exe)], check=True, timeout=5)
