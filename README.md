# osusu_money
Susu project for Zhuwa Academy Software engineering course application

A small program that manages one rotating savings group (susu) in GHS.
Pure Python 3 standard library, with no dependencies (Python 3.8+).

## Files
- `susu.py` – the program (logic and CLI)
- `test_susu.py` – automated tests
- `susu.json` – created automatically in the current directory to save state

## Run

```bash
python3 susu.py create 50.00      # new group, 50.00 GHS per member per week
python3 susu.py add Ama           # add members (in join order)
python3 susu.py add Kofi
python3 susu.py add Esi
python3 susu.py pay Ama 50        # record a contribution (partial allowed)
python3 susu.py pay Esi 30
python3 susu.py close             # pays out only if everyone has paid in full
python3 susu.py pay Esi 20
python3 susu.py close             # Ama receives 150.00, week 2 begins
python3 susu.py report            # week, paid in full, owing, payout history
```

`create` starts a fresh group and overwrites any existing `susu.json`.
Delete `susu.json` to reset. Errors exit with code 2 and an `Error:` message.

## Tests

```bash
python3 -m unittest -v test_susu.py
```

Run from the folder containing both files. The 12 tests cover the example
scenario, partial payments, a week that cannot close, rejection of
unknown/duplicate members, zero/negative amounts and overpayments, exact money
handling, roster locking, a full cycle, and the report.

## Assumptions
1. Money is stored as integer pesewas (no floats). More than 2 decimal places is rejected, never rounded.
2. Members can only be added before any contribution or payout is recorded; after that the roster is locked.
3. Names are trimmed and unique ignoring case.
4. Payments apply to the current week only. Paying more than owed that week is rejected, so no credit carries over.
5. Payout = weekly amount x number of members, paid to the next member in join order. Closing an incomplete week changes nothing and reports who owes what.
6. Once every member has received a pot, the cycle is complete and further payments or closes are rejected.
7. Weekly contribution must be greater than zero and is fixed at creation.
