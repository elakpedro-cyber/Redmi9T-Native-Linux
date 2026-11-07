"""Offline LCDB safety contract and fault matrix. No hardware backend."""
from collections import Counter
from dataclasses import dataclass, field
from itertools import product
import unittest


class Fault(Exception):
    pass


@dataclass
class FakePmic:
    faults: dict = field(default_factory=dict)
    trace: list = field(default_factory=list)
    enabled: bool = False
    ready: bool = False
    pull_down: bool = False
    boost: int = 0
    ldo: int = 0
    ncp: int = 0

    def op(self, step, field=None, value=None):
        self.trace.append(step)
        fault = self.faults.pop(step, None)
        if fault == "before":
            raise Fault(step)
        if field:
            setattr(self, field, value)
        if fault == "after":
            raise Fault(step)

    def expect(self, step, condition):
        self.op(step)
        if not condition:
            raise Fault(step)


SHUTDOWN = ("pd-on", "module-off", "read-enable-off", "wait-discharge",
            "read-ready-off", "pd-off")
RAILS = {"ldo", "ncp"}


class Lcdb:
    def __init__(self, pmic):
        self.pmic = pmic
        self.users = set()
        self.state = "unverified"
        self.latched = False
        self.errors = []
        # Even when control is confirmed off, software has no voltage evidence.
        self.bias_voltage = "unmeasured"

    def confirm_initial_state(self):
        self.pmic.expect("handoff-read", not self.pmic.enabled and not self.pmic.ready)
        self.state = "control-off"

    def _shutdown(self):
        p = self.pmic
        failures = []
        # Attempt all steps, retaining each error. This is a proposed contract,
        # conditional on PMI632 permitting module-off even if pull-down failed.
        for operation in (
            lambda: p.op("pd-on", "pull_down", True),
            lambda: p.op("module-off", "enabled", False),
            lambda: p.expect("read-enable-off", not p.enabled),
            lambda: p.op("wait-discharge"),
            lambda: p.expect("read-ready-off", not p.ready),
            lambda: p.op("pd-off", "pull_down", False),
        ):
            try:
                operation()
            except Fault as error:
                failures.append(str(error))
        self.errors.extend(failures)
        self.state = "unknown" if failures else "control-off"
        self.latched |= bool(failures)
        return failures

    def enable(self, rail):
        assert rail in RAILS
        if self.latched or self.state not in {"control-off", "on"}:
            raise Fault("enable-blocked")
        if rail in self.users:
            return
        p = self.pmic
        try:
            if not self.users:
                p.op("module-ready")
                for target in ("boost", "ldo", "ncp"):
                    p.op(f"initial-{target}", target, 4650 if target == "boost" else 4500)
                self.state = "unknown"
                p.op("module-on", "enabled", True)
                p.op("vreg-ok", "ready", True)
                for level in (5000, 5500):
                    for target in ("boost", "ldo", "ncp"):
                        p.op(f"ramp-{level}-{target}", target, level + 150 if target == "boost" else level)
            # Software consumer acquisition, since both physical outputs share enable.
            p.op(f"acquire-{rail}")
        except Fault as error:
            self.abort(str(error))
            raise
        self.users.add(rail)
        self.state = "on"

    def disable(self, rail):
        assert rail in RAILS
        if rail not in self.users:
            return
        self.users.remove(rail)
        if not self.users:
            failures = self._shutdown()
            if failures:
                raise Fault(failures[0])

    def abort(self, reason):
        self.errors.append(reason)
        self.latched = True
        self.users.clear()
        self._shutdown()


class SafetyTests(unittest.TestCase):
    def new(self, **kwargs):
        pmic = FakePmic(**kwargs)
        lcdb = Lcdb(pmic)
        lcdb.confirm_initial_state()
        return pmic, lcdb

    def assert_latched(self, pmic, lcdb):
        trace = pmic.trace[:]
        for rail in RAILS:
            with self.assertRaisesRegex(Fault, "enable-blocked"):
                lcdb.enable(rail)
            lcdb.disable(rail)
        self.assertEqual(pmic.trace, trace)
        self.assertEqual(lcdb.bias_voltage, "unmeasured")

    def test_handoff_requires_verified_off(self):
        for args in ({"enabled": True}, {"ready": True}, {"faults": {"handoff-read": "before"}}):
            with self.subTest(args=args):
                pmic = FakePmic(**args)
                lcdb = Lcdb(pmic)
                with self.assertRaises(Fault):
                    lcdb.confirm_initial_state()
                with self.assertRaisesRegex(Fault, "enable-blocked"):
                    lcdb.enable("ldo")
                self.assertEqual(pmic.trace, ["handoff-read"])

    def test_shared_gate_and_repeat(self):
        pmic, lcdb = self.new()
        lcdb.disable("ldo")
        lcdb.enable("ldo")
        lcdb.enable("ldo")
        lcdb.enable("ncp")
        lcdb.disable("ldo")
        lcdb.disable("ldo")
        self.assertTrue(pmic.enabled)
        self.assertEqual(lcdb.users, {"ncp"})
        # Model hardware reaction to off for this successful path.
        pmic.ready = False
        lcdb.disable("ncp")
        lcdb.disable("ncp")
        self.assertEqual(lcdb.state, "control-off")
        self.assertEqual(tuple(pmic.trace[-6:]), SHUTDOWN)
        self.assertEqual(Counter(pmic.trace)["module-on"], 1)
        self.assertEqual(lcdb.bias_voltage, "unmeasured")

    def test_enable_failure_matrix(self):
        pmic, lcdb = self.new()
        lcdb.enable("ldo")
        lcdb.enable("ncp")
        for step, mode in product(pmic.trace[1:], ("before", "after")):
            with self.subTest(step=step, mode=mode):
                chip, model = self.new(faults={step: mode})
                with self.assertRaisesRegex(Fault, step):
                    model.enable("ldo")
                    model.enable("ncp")
                self.assertEqual(tuple(chip.trace[-6:]), SHUTDOWN)
                self.assertEqual(model.state, "unknown" if chip.ready else "control-off")
                self.assertFalse(chip.enabled)
                self.assertEqual(model.errors[0], step)
                self.assert_latched(chip, model)

    def test_partial_ramp_register_state(self):
        for mode, expected_ncp in (("before", 5000), ("after", 5500)):
            with self.subTest(mode=mode):
                pmic, model = self.new(faults={"ramp-5500-ncp": mode})
                with self.assertRaisesRegex(Fault, "ramp-5500-ncp"):
                    model.enable("ldo")
                self.assertEqual((pmic.boost, pmic.ldo, pmic.ncp), (5650, 5500, expected_ncp))
                self.assertFalse(pmic.enabled)
                self.assertEqual(model.state, "unknown")
                self.assert_latched(pmic, model)

    def test_shutdown_failure_matrix(self):
        for step, mode, trigger in product(SHUTDOWN, ("before", "after"),
                                           ("last-disable", "panel-prepare", "short-circuit")):
            with self.subTest(step=step, mode=mode, trigger=trigger):
                chip, model = self.new(faults={step: mode})
                model.enable("ldo")
                model.enable("ncp")
                chip.ready = False
                if trigger == "last-disable":
                    model.disable("ncp")
                    with self.assertRaisesRegex(Fault, step):
                        model.disable("ldo")
                else:
                    model.abort(trigger)
                    self.assertEqual(model.errors[0], trigger)
                self.assertEqual(tuple(chip.trace[-6:]), SHUTDOWN)
                self.assertIn(step, model.errors)
                self.assertEqual(model.state, "unknown")
                self.assert_latched(chip, model)

    def test_timeout_with_failed_rollback(self):
        for rollback in SHUTDOWN:
            with self.subTest(rollback=rollback):
                chip, model = self.new(faults={"vreg-ok": "before", rollback: "before"})
                with self.assertRaisesRegex(Fault, "vreg-ok"):
                    model.enable("ldo")
                self.assertEqual(model.errors[:2], ["vreg-ok", rollback])
                if rollback == "module-off":
                    self.assertEqual(model.errors[2:], ["read-enable-off"])
                self.assertEqual(model.state, "unknown")
                self.assert_latched(chip, model)

    def test_panel_abort_and_short_circuit_without_retry(self):
        for trigger in ("panel-prepare", "short-circuit"):
            with self.subTest(trigger=trigger):
                chip, model = self.new()
                model.enable("ldo")
                model.enable("ncp")
                chip.ready = False
                model.abort(trigger)
                self.assertEqual(model.state, "control-off")
                self.assertFalse(chip.enabled)
                self.assertEqual(tuple(chip.trace[-6:]), SHUTDOWN)
                self.assert_latched(chip, model)


if __name__ == "__main__":
    unittest.main(verbosity=2)

