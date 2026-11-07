from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / 'display-v8/qcom-lcdb-regulator-lemon.c').read_text()
stub = r"""
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
typedef uint8_t u8;
typedef uint32_t u32;
typedef long long ktime_t, s64;
#define BIT(x) (1u << (x))
#define GENMASK(h,l) (((2u << (h)) - 1) & ~((1u << (l)) - 1))
#define max(a,b) ((a) > (b) ? (a) : (b))
#define min(a,b) ((a) < (b) ? (a) : (b))
#define clamp(a,b,c) min(max(a,b),c)
#define DIV_ROUND_UP(a,b) (((a)+(b)-1)/(b))
#define dev_err(dev, fmt, ...) ((void)snprintf(NULL, 0, fmt, __VA_ARGS__))
#define lockdep_assert_held(...) ((void)0)

static pthread_mutex_t *lock_get(pthread_mutex_t *lock) {
    assert(!pthread_mutex_lock(lock)); return lock;
}
static void lock_put(pthread_mutex_t **lock) { assert(!pthread_mutex_unlock(*lock)); }
#define guard(kind) pthread_mutex_t *guard __attribute__((cleanup(lock_put))) = lock_get
static void usleep_range(int a, int b) { (void)a; (void)b; }
static ktime_t ktime_get(void) { return 30000; }
static s64 ktime_us_delta(ktime_t a, ktime_t b) { return a - b; }
struct device;
struct regulator_dev { void *data; unsigned id; };
#define rdev_get_drvdata(r) ((r)->data)
#define rdev_get_id(r) ((r)->id)

struct regmap {
    unsigned v[256], n, fail_at, fail_at2, fail_after, off_attempts, on_attempts;
    unsigned sc_status_read, status_reads, voltage_writes;
    bool down, fail_off, ready_stuck;
};
static int regmap_read(struct regmap *r, unsigned addr, unsigned *val) {
    if (r->down) return -EIO;
    ++r->n;
    if (r->n == r->fail_at || r->n == r->fail_at2) return -EIO;
    if (addr == 0x10 && ++r->status_reads == r->sc_status_read)
        r->v[addr] |= 2;
    *val = r->v[addr]; return 0;
}
static int regmap_write(struct regmap *r, unsigned addr, unsigned val) {
    ++r->n;
    bool fail = r->n == r->fail_at || r->n == r->fail_at2;
    if (addr == 0x46) {
        if (val) r->on_attempts++; else r->off_attempts++;
        if (!val && r->fail_off) return -EIO;
    }
    if (r->down || (fail && !r->fail_after)) return -EIO;
    r->v[addr] = val;
    if (addr == 0x71 || addr == 0x81) r->voltage_writes++;
    if (addr == 0x46 && !r->ready_stuck)
        r->v[0x10] = val ? 1 : 0;
    return fail ? -EIO : 0;
}
static int regmap_update_bits(struct regmap *r, unsigned addr, unsigned mask, unsigned val) {
    unsigned old;
    int ret = regmap_read(r, addr, &old);
    return ret ?: regmap_write(r, addr, (old & ~mask) | val);
}
#define regmap_set_bits(r,a,m) regmap_update_bits(r,a,m,m)
#define regmap_read_poll_timeout(r,a,v,cond,s,t) ({ \
    int e = regmap_read(r,a,&v); e ?: ((cond) ? 0 : -ETIMEDOUT); })
"""
definitions = source[source.index('#define LCDB_INT_RT_STS'):source.index('static const struct regulator_ops')]
definitions = definitions.replace('struct mutex lock;', 'pthread_mutex_t lock;')
irq = source[source.index('static bool qcom_lcdb_handle_irq'):source.index('static irqreturn_t')]
init = source[source.index('static int qcom_lcdb_suspend_off'):source.index('static int qcom_lcdb_probe')]
checks = r"""
static void setup(struct regmap *p, struct qcom_lcdb *l, struct regulator_dev *a,
                  struct regulator_dev *b) {
    memset(p, 0, sizeof(*p));
    memset(l, 0, sizeof(*l));
    assert(!pthread_mutex_init(&l->lock, NULL));
    l->regmap = p;
    assert(!qcom_lcdb_hw_init(l));
    assert(!p->on_attempts && !p->off_attempts);
    *a = (struct regulator_dev){l, LCDB_LDO};
    *b = (struct regulator_dev){l, LCDB_NCP};
    assert(qcom_lcdb_enable(a) == -EAGAIN);
    assert(!qcom_lcdb_set_voltage_sel(a, qcom_lcdb_uV_to_sel(5500000)));
    assert(!qcom_lcdb_set_voltage_sel(b, qcom_lcdb_uV_to_sel(5500000)));
    assert(qcom_lcdb_get_voltage_sel(a) == (int)qcom_lcdb_uV_to_sel(5500000));
    l->armed = true;
    p->n = p->status_reads = 0;
}
static void blocked(struct qcom_lcdb *l, struct regulator_dev *a) {
    unsigned n = l->regmap->n;
    assert(qcom_lcdb_enable(a) == -EIO);
    assert(qcom_lcdb_enable(a) == -EIO);
    assert(l->regmap->n == n);
}
static void *enable_thread(void *arg) {
    assert(!qcom_lcdb_enable(arg));
    return NULL;
}
static void *disable_thread(void *arg) {
    assert(!qcom_lcdb_disable(arg));
    return NULL;
}
static void *abort_thread(void *arg) {
    int ret = qcom_lcdb_disable(arg);
    assert(ret == 0 || ret == -EIO);
    return NULL;
}
static void *irq_thread(void *arg) {
    qcom_lcdb_handle_irq(arg);
    return NULL;
}
int main(void) {
    struct regmap p;
    struct qcom_lcdb l;
    struct regulator_dev a,b;
    unsigned enable_ops, off_ops;
    pthread_t t1,t2;
    for (unsigned sc = 2; sc <= 5; sc++) {
        setup(&p,&l,&a,&b);
        p.sc_status_read = sc;
        assert(qcom_lcdb_enable(&a) == -EIO);
        assert(l.state == LCDB_FAULT && p.off_attempts == 1);
        assert(p.voltage_writes == 2 + (sc > 3 ? 2 * (sc - 3) : 0));
        blocked(&l,&a);
        assert(!pthread_mutex_destroy(&l.lock));
    }
    setup(&p,&l,&a,&b);
    assert(!qcom_lcdb_suspend_off(&l));
    assert(qcom_lcdb_enable(&a) == -EBUSY && !p.on_attempts);
    assert(qcom_lcdb_set_voltage_sel(&a, 12) == -EBUSY);
    assert(!qcom_lcdb_resume_off(&l) && !p.on_attempts);
    assert(!qcom_lcdb_enable(&a));
    assert(qcom_lcdb_suspend_off(&l) == -EBUSY && !p.off_attempts);
    assert(!qcom_lcdb_disable(&a));
    assert(!qcom_lcdb_suspend_off(&l));
    p.v[LCDB_LDO_FORCE_PD_CTL] = LCDB_LDO_FORCE_PD_EN;
    assert(qcom_lcdb_resume_off(&l) == -EIO && l.state == LCDB_UNKNOWN);
    assert(p.on_attempts == 1 && p.off_attempts == 1);
    blocked(&l,&a);
    assert(!pthread_mutex_destroy(&l.lock));

    setup(&p,&l,&a,&b);
    assert(!qcom_lcdb_enable(&a));
    enable_ops = p.n;
    p.n = 0;
    assert(!qcom_lcdb_disable(&a));
    off_ops = p.n;
    assert(!pthread_mutex_destroy(&l.lock));
    for (unsigned i=1; i<=enable_ops; i++) {
        for (unsigned after=0; after<2; after++) {
            setup(&p,&l,&a,&b);
            p.fail_at=i; p.fail_after=after;
            assert(qcom_lcdb_enable(&a)<0);
            assert(l.state==LCDB_FAULT || l.state==LCDB_UNKNOWN);
            assert(!p.v[LCDB_ENABLE_CTL1]);
            blocked(&l,&a);
            assert(!pthread_mutex_destroy(&l.lock));
        }
    }
    for (unsigned i=1; i<=off_ops; i++) {
        for (unsigned after=0; after<2; after++) {
            setup(&p,&l,&a,&b);
            assert(!qcom_lcdb_enable(&a));
            p.n=0; p.fail_at=i; p.fail_after=after;
            assert(qcom_lcdb_disable(&a)<0);
            assert(l.state==LCDB_FAULT || l.state==LCDB_UNKNOWN);
            unsigned attempts=p.off_attempts;
            qcom_lcdb_disable(&a);
            assert(p.off_attempts==attempts);
            blocked(&l,&a);
            assert(!pthread_mutex_destroy(&l.lock));
        }
    }
    setup(&p,&l,&a,&b);
    p.v[LCDB_ENABLE_CTL1]=LCDB_MODULE_EN;
    assert(qcom_lcdb_enable(&a)<0 && l.state==LCDB_UNKNOWN);
    assert(p.off_attempts==0);
    blocked(&l,&a);
    assert(!pthread_mutex_destroy(&l.lock));
    setup(&p,&l,&a,&b);
    assert(!qcom_lcdb_enable(&a));
    p.v[LCDB_INT_RT_STS]=0;
    assert(qcom_lcdb_enable(&b)<0 && l.state==LCDB_FAULT);
    assert(p.off_attempts==1);
    blocked(&l,&a);
    assert(!pthread_mutex_destroy(&l.lock));
    setup(&p,&l,&a,&b);
    p.ready_stuck=true;
    assert(qcom_lcdb_enable(&a)==-ETIMEDOUT && l.state==LCDB_FAULT);
    assert(!p.v[LCDB_ENABLE_CTL1]);
    blocked(&l,&a);
    assert(!pthread_mutex_destroy(&l.lock));
    setup(&p,&l,&a,&b);
    p.ready_stuck=true; p.fail_off=true;
    assert(qcom_lcdb_enable(&a)==-ETIMEDOUT && l.state==LCDB_UNKNOWN);
    assert(p.v[LCDB_ENABLE_CTL1] && p.off_attempts==1);
    blocked(&l,&a);
    assert(!pthread_mutex_destroy(&l.lock));
    setup(&p,&l,&a,&b);
    assert(!qcom_lcdb_enable(&a));
    p.down=true;
    assert(qcom_lcdb_handle_irq(&l) && l.state==LCDB_UNKNOWN);
    assert(!qcom_lcdb_handle_irq(&l));
    assert(qcom_lcdb_is_enabled(&a)==-EIO);
    blocked(&l,&a);
    assert(!pthread_mutex_destroy(&l.lock));
    for (unsigned i=0; i<32; i++) {
        setup(&p,&l,&a,&b);
        assert(!pthread_create(&t1,NULL,enable_thread,&a));
        assert(!pthread_create(&t2,NULL,enable_thread,&b));
        pthread_join(t1,NULL); pthread_join(t2,NULL);
        assert(l.enabled_mask==3 && p.on_attempts==1);
        assert(!pthread_create(&t1,NULL,disable_thread,&a));
        assert(!pthread_create(&t2,NULL,disable_thread,&b));
        pthread_join(t1,NULL); pthread_join(t2,NULL);
        assert(l.state==LCDB_DISABLED && !l.enabled_mask && p.off_attempts==1);
        assert(!qcom_lcdb_is_enabled(&a));
        assert(!pthread_mutex_destroy(&l.lock));
        setup(&p,&l,&a,&b);
        assert(!qcom_lcdb_enable(&a));
        p.v[LCDB_INT_RT_STS]|=LCDB_SC_ERROR_RT_STS;
        assert(!pthread_create(&t1,NULL,irq_thread,&l));
        assert(!pthread_create(&t2,NULL,irq_thread,&l));
        pthread_join(t1,NULL); pthread_join(t2,NULL);
        assert(l.state==LCDB_FAULT && p.off_attempts==1);
        blocked(&l,&a);
        assert(!pthread_mutex_destroy(&l.lock));
    }
    for (unsigned i=0; i<32; i++) {
        setup(&p,&l,&a,&b);
        assert(!qcom_lcdb_enable(&a));
        p.v[LCDB_INT_RT_STS]|=LCDB_SC_ERROR_RT_STS;
        assert(!pthread_create(&t1,NULL,irq_thread,&l));
        /* Use a wrapper which allows -EIO when the normal disable sees SC first. */
        assert(!pthread_create(&t2,NULL,abort_thread,&a));
        pthread_join(t1,NULL); pthread_join(t2,NULL);
        assert(l.state==LCDB_FAULT && p.off_attempts==1);
        blocked(&l,&a);
        assert(!pthread_mutex_destroy(&l.lock));
    }
    /* The last enable read fails, followed by each shutdown I/O step. */
    for (unsigned i=1; i<=off_ops-2; i++) {
        for (unsigned after=0; after<2; after++) {
            setup(&p,&l,&a,&b);
            p.fail_at=enable_ops; p.fail_at2=enable_ops+i; p.fail_after=after;
            assert(qcom_lcdb_enable(&a)==-EIO && l.state==LCDB_UNKNOWN);
            assert(qcom_lcdb_is_enabled(&a)==-EIO && p.off_attempts==1);
            unsigned n=p.n;
            assert(qcom_lcdb_disable(&a)==-EIO && qcom_lcdb_disable(&b)==-EIO);
            assert(!qcom_lcdb_handle_irq(&l));
            blocked(&l,&a);
            assert(p.n==n);
            assert(!pthread_mutex_destroy(&l.lock));
        }
    }
    for (unsigned i=0; i<32; i++) {
        setup(&p,&l,&a,&b);
        assert(!qcom_lcdb_enable(&a));
        assert(!pthread_create(&t1,NULL,enable_thread,&b));
        assert(!pthread_create(&t2,NULL,disable_thread,&a));
        pthread_join(t1,NULL); pthread_join(t2,NULL);
        assert(l.state==LCDB_ENABLED && l.enabled_mask==BIT(LCDB_NCP));
        assert(!qcom_lcdb_disable(&b));
        assert(l.state==LCDB_DISABLED && p.on_attempts==p.off_attempts);
        assert(!pthread_mutex_destroy(&l.lock));
    }
    printf("PASS: C driver core, %u single I/O faults, %u nested faults, timeout, PMIC loss, readback mismatch, 128 threaded cases, 4 SC ramp points and suspend/resume\n",
           2*(enable_ops+off_ops), 2*(off_ops-2));
}
"""
with tempfile.TemporaryDirectory(prefix="lemon-lcdb-c-") as tmp:
    src = Path(tmp) / 'lcdb.c'
    src.write_text(stub + definitions + irq + init + checks)
    exe = src.with_suffix('')
    subprocess.run(['cc','-Wall','-Wextra','-Werror','-pthread',src,'-o',exe],check=True)
    subprocess.run([exe],check=True,timeout=15)
