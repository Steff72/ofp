from decimal import Decimal

import pytest

from oo_bank import (
    Bank,
    InsufficientFunds,
    InvalidAmount,
    SameAccountTransfer,
    money,
)


def test_deposit_cash_updates_balance_and_journal():
    bank = Bank()
    account_id = bank.open_account("youth")
    before = len(bank.get_bank_journal())

    txn_id = bank.deposit_cash(account_id, 100)

    assert txn_id > 0
    assert bank.get_balance(account_id) == money(100)
    entries = bank.get_account_entries(account_id)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.amount_signed == money(100)
    assert entry.counterparty is None
    assert entry.type == "CASH_DEPOSIT"
    assert len(bank.get_bank_journal()) == before + 1


def test_transfer_applies_fee_for_private_account():
    bank = Bank()
    private_id = bank.open_account("private")
    youth_id = bank.open_account("youth")
    bank.deposit_cash(private_id, 100)
    before = len(bank.get_bank_journal())

    txn_ids = bank.transfer(private_id, youth_id, 10, "Taschengeld")

    assert len(txn_ids) == 2
    assert bank.get_balance(private_id) == money("89.50")
    assert bank.get_balance(youth_id) == money(10)
    assert bank.get_balance(bank.fee_income_account_id) == money("0.50")
    journal_types = [t.type for t in bank.get_bank_journal()[-2:]]
    assert journal_types == ["TRANSFER", "FEE"]
    assert len(bank.get_bank_journal()) == before + 2


def test_youth_account_blocks_overdraft():
    bank = Bank()
    youth_id = bank.open_account("youth")
    private_id = bank.open_account("private")
    bank.deposit_cash(youth_id, 10)

    with pytest.raises(InsufficientFunds):
        bank.transfer(youth_id, private_id, 50)

    assert bank.get_balance(youth_id) == money(10)
    assert len(bank.get_bank_journal()) == 1


def test_private_account_allows_overdraft_with_fee():
    bank = Bank()
    private_id = bank.open_account("private", overdraft_limit=500)
    youth_id = bank.open_account("youth")
    bank.deposit_cash(private_id, 50)

    txn_ids = bank.transfer(private_id, youth_id, 400)

    assert len(txn_ids) == 2
    assert bank.get_balance(private_id) == money("-354")
    assert bank.get_balance(youth_id) == money(400)
    assert bank.get_balance(bank.fee_income_account_id) == money(4)


def test_apply_interest_to_savings_accounts():
    bank = Bank()
    savings_id = bank.open_account("savings", rate="0.02")
    bank.deposit_cash(savings_id, 200)

    generated = bank.apply_interest_to_all_savings()

    assert len(generated) == 1
    assert bank.get_balance(savings_id) == money(204)
    assert bank.get_balance(bank.interest_expense_account_id) == money(-4)
    assert bank.get_bank_journal()[-1].type == "INTEREST"


def test_same_account_transfer_is_rejected_early():
    bank = Bank()
    acc_id = bank.open_account("youth")

    with pytest.raises(SameAccountTransfer):
        bank.transfer(acc_id, acc_id, 10)


def test_deposit_rejects_non_positive_amounts():
    bank = Bank()
    acc_id = bank.open_account("youth")

    with pytest.raises(InvalidAmount):
        bank.deposit_cash(acc_id, Decimal("-1"))
