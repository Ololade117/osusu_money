import unittest

from susu import SusuGroup, SusuError, parse_money, fmt


def make(*names, amount="50.00"):
    g = SusuGroup(amount)
    for n in names:
        g.add_member(n)
    return g


class TestSusu(unittest.TestCase):
    def test_example_scenario(self):
        g = make("Ama", "Kofi", "Esi")
        g.contribute("Ama", "50")
        g.contribute("Kofi", "50")
        g.contribute("Esi", "30")
        paid, msg = g.close_week()
        self.assertFalse(paid)
        self.assertIn("Esi owes 20.00", msg)
        g.contribute("Esi", "20")
        paid, msg = g.close_week()
        self.assertTrue(paid)
        self.assertEqual(g.payouts, [(1, "Ama", 15000)])
        self.assertEqual(g.week, 2)
        self.assertEqual(g.members[len(g.payouts)], "Kofi")

    def test_partial_payment_tracks_remaining(self):
        g = make("Ama", "Kofi")
        self.assertEqual(g.contribute("Ama", "20.50"), 2950)
        self.assertEqual(g.contribute("Ama", "29.50"), 0)
        self.assertEqual(g.outstanding(), {"Kofi": 5000})

    def test_week_cannot_close_when_unpaid(self):
        g = make("Ama", "Kofi")
        g.contribute("Ama", "50")
        paid, msg = g.close_week()
        self.assertFalse(paid)
        self.assertIn("Kofi owes 50.00", msg)
        self.assertEqual(g.week, 1)
        self.assertEqual(g.payouts, [])

    def test_rejects_unknown_member(self):
        g = make("Ama")
        with self.assertRaises(SusuError):
            g.contribute("Zed", "10")

    def test_rejects_duplicate_member_case_insensitive(self):
        g = make("Ama")
        with self.assertRaises(SusuError):
            g.add_member(" ama ")

    def test_rejects_zero_and_negative(self):
        g = make("Ama")
        for bad in ("0", "0.00", "-5"):
            with self.assertRaises(SusuError):
                g.contribute("Ama", bad)

    def test_rejects_overpayment(self):
        g = make("Ama")
        g.contribute("Ama", "30")
        with self.assertRaises(SusuError):
            g.contribute("Ama", "20.01")
        self.assertEqual(g.paid["Ama"], 3000)  # unchanged

    def test_exact_money_no_float_errors(self):
        g = make("Ama", amount="0.10")
        g.contribute("Ama", "0.10")
        self.assertEqual(g.outstanding(), {})
        self.assertEqual(parse_money("0.1") + parse_money("0.2"),
                         parse_money("0.3"))
        with self.assertRaises(SusuError):
            parse_money("1.005")  # never rounded
        self.assertEqual(fmt(5), "0.05")

    def test_roster_locked_after_first_payment(self):
        g = make("Ama", "Kofi")
        g.contribute("Ama", "10")
        with self.assertRaises(SusuError):
            g.add_member("Esi")

    def test_full_cycle_pays_in_join_order(self):
        g = make("Ama", "Kofi", "Esi")
        for _ in range(3):
            for m in g.members:
                g.contribute(m, "50")
            self.assertTrue(g.close_week()[0])
        self.assertEqual([p[1] for p in g.payouts], ["Ama", "Kofi", "Esi"])
        self.assertTrue(all(p[2] == 15000 for p in g.payouts))
        self.assertTrue(g.finished)
        with self.assertRaises(SusuError):
            g.close_week()

    def test_invalid_weekly_amount(self):
        with self.assertRaises(SusuError):
            SusuGroup("0")
        with self.assertRaises(SusuError):
            SusuGroup("abc")

    def test_report_contents(self):
        g = make("Ama", "Kofi")
        g.contribute("Ama", "50")
        g.contribute("Kofi", "10")
        r = g.report()
        self.assertIn("Current week: 1", r)
        self.assertIn("Paid in full: Ama", r)
        self.assertIn("Kofi 40.00", r)
        self.assertIn("(none yet)", r)


if __name__ == "__main__":
    unittest.main()