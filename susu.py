import json
import sys
from decimal import Decimal, InvalidOperation


class SusuError(Exception):
    pass


def parse_money(value) -> int:
    """Parse a money string/number into integer pesewas, exactly."""
    try:
        d = Decimal(str(value).strip())
    except (InvalidOperation, AttributeError):
        raise SusuError(f"Invalid amount: {value!r}")
    if not d.is_finite():
        raise SusuError(f"Invalid amount: {value!r}")
    cents = d * 100
    if cents != cents.to_integral_value():
        raise SusuError("Amount may have at most 2 decimal places.")
    return int(cents)


def fmt(p: int) -> str:
    return f"{p // 100}.{p % 100:02d}"

class SusuGroup:
    def __init__(self, weekly_amount):
        amt = parse_money(weekly_amount)
        if amt <= 0:
            raise SusuError("Weekly contribution must be greater than zero.")
        self.weekly = amt
        self.members = []        # original display names, in join order
        self.paid = {}           # key -> pesewas paid this week
        self.week = 1
        self.payouts = []        # (week, member, amount_pesewas)
        self.locked = False      # True once any payment/close has happened

    # ---------- helpers ----------
    @staticmethod
    def _key(name):
        return name.strip().casefold()

    def _find(self, name):
        k = self._key(name or "")
        for m in self.members:
            if self._key(m) == k:
                return m
        raise SusuError(f"Unknown member: {name!r}")

    @property
    def finished(self):
        return len(self.payouts) >= len(self.members) > 0

    def _owed(self, member):
        return self.weekly - self.paid.get(member, 0)

    # ---------- operations ----------
    def add_member(self, name):
        name = (name or "").strip()
        if not name:
            raise SusuError("Member name cannot be empty.")
        if self.locked:
            raise SusuError("Roster is locked: members can only be added "
                            "before any contribution is recorded.")
        if any(self._key(m) == self._key(name) for m in self.members):
            raise SusuError(f"Duplicate member: {name!r}")
        self.members.append(name)
        self.paid[name] = 0

    def contribute(self, name, amount):
        if self.finished:
            raise SusuError("The cycle is complete; no more contributions.")
        member = self._find(name)
        amt = parse_money(amount)
        if amt <= 0:
            raise SusuError("Amount must be greater than zero.")
        owed = self._owed(member)
        if amt > owed:
            raise SusuError(f"{member} only owes {fmt(owed)} this week; "
                            f"cannot pay {fmt(amt)}.")
        self.paid[member] += amt
        self.locked = True
        return owed - amt  # remaining

    def outstanding(self):
        return {m: self._owed(m) for m in self.members if self._owed(m) > 0}

    def close_week(self):
        """Returns (paid_out: bool, message)."""
        if not self.members:
            raise SusuError("No members in the group.")
        if self.finished:
            raise SusuError("The cycle is complete; nothing to close.")
        owing = self.outstanding()
        if owing:
            lines = [f"{m} owes {fmt(a)}" for m, a in owing.items()]
            return False, "Week not closed. " + "; ".join(lines)
        recipient = self.members[len(self.payouts)]
        pot = self.weekly * len(self.members)
        self.payouts.append((self.week, recipient, pot))
        self.locked = True
        closed = self.week
        self.week += 1
        for m in self.members:
            self.paid[m] = 0
        msg = f"Week {closed} closed. {recipient} receives {fmt(pot)}."
        if self.finished:
            msg += " Cycle complete."
        else:
            msg += f" Week {self.week} begins; next recipient: " \
                   f"{self.members[len(self.payouts)]}."
        return True, msg

    def report(self):
        out = [f"Weekly contribution: GHS {fmt(self.weekly)}",
               f"Members ({len(self.members)}): " + ", ".join(self.members)]
        if self.finished:
            out.append("Status: cycle complete.")
        else:
            out.append(f"Current week: {self.week}")
            if self.members:
                out.append(f"Receiving this week: "
                           f"{self.members[len(self.payouts)]}")
            full = [m for m in self.members if self._owed(m) == 0]
            owing = self.outstanding()
            out.append("Paid in full: " + (", ".join(full) or "none"))
            out.append("Owing: " + ("; ".join(
                f"{m} {fmt(a)}" for m, a in owing.items()) or "none"))
        out.append("Payout history:")
        if self.payouts:
            out += [f"  Week {w}: {m} received {fmt(a)}"
                    for w, m, a in self.payouts]
        else:
            out.append("  (none yet)")
        return "\n".join(out)

    # ---------- persistence ----------
    def to_dict(self):
        return {"weekly": self.weekly, "members": self.members,
                "paid": self.paid, "week": self.week,
                "payouts": self.payouts, "locked": self.locked}

    @classmethod
    def from_dict(cls, d):
        g = cls(fmt(d["weekly"]))
        g.members, g.paid, g.week = d["members"], d["paid"], d["week"]
        g.payouts = [tuple(p) for p in d["payouts"]]
        g.locked = d["locked"]
        return g


# ---------- CLI ----------
STATE = "susu.json"
USAGE = """Usage:
  susu.py create <weekly_amount>
  susu.py add <name>
  susu.py pay <name> <amount>
  susu.py close
  susu.py report"""


def main(argv):
    if not argv:
        print(USAGE); return 1
    cmd, args = argv[0], argv[1:]
    try:
        if cmd == "create":
            if len(args) != 1:
                raise SusuError("create needs: <weekly_amount>")
            g = SusuGroup(args[0])
            print(f"Group created: GHS {fmt(g.weekly)} per week.")
        else:
            try:
                with open(STATE) as f:
                    g = SusuGroup.from_dict(json.load(f))
            except FileNotFoundError:
                raise SusuError("No group yet. Run: create <weekly_amount>")
            if cmd == "add" and len(args) == 1:
                g.add_member(args[0]); print(f"Added {args[0].strip()}.")
            elif cmd == "pay" and len(args) == 2:
                rem = g.contribute(args[0], args[1])
                print("Recorded. " + (f"Still owes {fmt(rem)}." if rem
                                      else "Paid in full."))
            elif cmd == "close" and not args:
                print(g.close_week()[1])
            elif cmd == "report" and not args:
                print(g.report())
            else:
                print(USAGE); return 1
        with open(STATE, "w") as f:
            json.dump(g.to_dict(), f)
        return 0
    except SusuError as e:
        print(f"Error: {e}"); return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))