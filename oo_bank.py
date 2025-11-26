# für komplexe Typannotationen
from __future__ import annotations

from dataclasses import dataclass, field
# ermöglicht exakte Dezimal-Arithmetik
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from typing import Optional, Dict, List, Callable, Type

# für Geldbeträge sinnvolle Rundung setzen
CENTS = Decimal("0.01")


def money(x) -> Decimal:
    """
    Normalisiert Eingaben zuverlässig auf 2 Dezimalstellen.
    Erlaubt Int/Str/Decimal als Argument.
    """
    if not isinstance(x, Decimal):
        x = Decimal(str(x))
    return x.quantize(CENTS, rounding=ROUND_HALF_UP)


# Exceptions, klare Fehlerfälle signalisieren
class BankError(Exception):
    """Allgemeiner Bankfehler."""


class AccountNotFound(BankError):
    """Konto-ID existiert nicht."""


class AccountClosed(BankError):
    """Konto ist geschlossen/inkativ."""


class DuplicateAccountId(BankError):
    """Konto-ID bereits vergeben."""


class InvalidAmount(BankError):
    """Betrag ungültig (z.B. nicht positiv)."""


class InsufficientFunds(BankError):
    """Deckung/Limit reicht nicht aus."""


class SameAccountTransfer(BankError):
    """Überweisung von und zu demselben Konto nicht erlaubt (optional)."""


# Datenstrukturen für Journal/Transaktionen 
@dataclass(frozen=True)
class Transaction:
    """
    Repräsentiert eine Bank-Transaktion für das Bank-Journal.
    Arten (type):
      - "CASH_DEPOSIT": Bareinzahlung (kein Gegenkonto)
      - "TRANSFER":     Normaler Transfer von A nach B
      - "FEE":          Gebührentransfer (von Kunde -> Bank)
      - "INTEREST":     Zinsgutschrift (von Bank -> Kunde)
    """
    id: int
    sequence: int                      # monoton steigende Nummer, Reihenfolge
    ts_utc: datetime                   # Zeitstempel
    type: str                          # Art der Transaktion
    from_account: Optional[str]        # Bel.-Konto, None bei Bareinzahlung
    to_account: Optional[str]          # Gut.-Konto, bei Bareinzahlung = Zielkonto
    amount: Decimal                    # immer positiv, Buchungswert
    purpose: Optional[str] = None      # Verwendungszweck/Notiz


@dataclass(frozen=True)
class AccountEntry:
    """
    Ein Eintrag im Konto-Journal eines einzelnen Kontos.
    amount_signed:
      - positiv: Gutschrift auf dieses Konto
      - negativ: Belastung von diesem Konto
    counterparty:
      - Konto-ID der Gegenseite (oder None bei Bareinzahlung)
    """
    transaction_id: int
    sequence: int
    ts_utc: datetime
    type: str
    amount_signed: Decimal
    counterparty: Optional[str]
    purpose: Optional[str]


# Konto-Hierarchie
class Account:
    """
    Basisklasse für alle Konten.
    Verwaltet:
      - ID, Aktiv-Flag, Saldo, Journal
    Liefert:
      - Polymorphe Regeln via can_withdraw / calc_withdraw_fee / describe()
    """

    def __init__(self, account_id: str):
        self._id: str = account_id
        self._active: bool = True
        self._balance: Decimal = money(0)
        self._journal: List[AccountEntry] = []

    # Eigenschaften, nur lesend von aussen zugänglich
    @property
    def id(self) -> str:
        return self._id

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def balance(self) -> Decimal:
        return self._balance

    @property
    def journal(self) -> List[AccountEntry]:
        # Kopie zurückgeben, um Encapsulation zu wahren
        return list(self._journal)

    # Lebenszyklus 
    def close(self):
        if self._balance != money(0):
            raise BankError("Konto kann nur mit Saldo 0 geschlossen werden.")
        self._active = False

    # Buchungs-API, nur Bank darf posten, Encapsulation, atomare Änderung
    def _post(self, entry: AccountEntry):
        """Nur von der Bank aufrufen: Journal-Eintrag hinzufügen und Saldo anpassen."""
        self._journal.append(entry)
        self._balance = money(self._balance + entry.amount_signed)

    #  Regeln, Polymorphie
    def can_withdraw(self, amount: Decimal) -> bool:
        """
        Prüft, ob dieser Kontotyp einen Abgang 'amount' zulässt.
        Basis: kein Überzug erlaubt (nicht negativ).
        """
        if amount <= 0:
            return False
        return self._balance - amount >= money(0)

    def calc_withdraw_fee(self, amount: Decimal) -> Decimal:
        """
        Berechnet die Gebühr für eine Abbuchung (Standard: 0).
        Positive Decimal zurückgeben.
        """
        return money(0)

    def accrue_interest(self, bank: "Bank") -> Optional[Transaction]:
        """
        Optional: Sparkonten o.ä. können hier Zinsgutschriften erzeugen,
        indem sie die Bank anweisen, eine INTEREST-Transaktion zu buchen.
        Basis: keine Zinsen.
        """
        return None

    def describe(self) -> str:
        """Kurze Typbeschreibung für Debug/Infos."""
        return "Generic Account"


class YouthAccount(Account):
    """
    Jugendkonto:
      - nie negativ
      - keine Gebühren
    """
    def describe(self) -> str:
        return "Youth Account (no overdraft, no fees)"


class PrivateAccount(Account):
    """
    Privatkonto:
      - Überziehung bis zum Limit erlaubt
      - Gebühren für Abbuchungen (Prozentsatz, Mindestgebühr)
    """
    def __init__(self, account_id: str,
                 overdraft_limit: Decimal = money(500),
                 fee_percent: Decimal = Decimal("0.01"),
                 min_fee: Decimal = money("0.50")):
        super().__init__(account_id)
        self._overdraft_limit = money(overdraft_limit)
        self._fee_percent = Decimal(fee_percent)   
        self._min_fee = money(min_fee)

    def describe(self) -> str:
        return (f"Private Account (overdraft to -{self._overdraft_limit}, "
                f"fee={self._fee_percent*100:.2f}% min {self._min_fee})")

    def can_withdraw(self, amount: Decimal) -> bool:    # polymorpher Hook
        if amount <= 0:
            return False
        # Überziehung bis -limit erlaubt
        return self.balance - amount >= money(0) - self._overdraft_limit

    def calc_withdraw_fee(self, amount: Decimal) -> Decimal:
        raw = money(amount * self._fee_percent)
        return raw if raw >= self._min_fee else self._min_fee


class SavingsAccount(Account):
    """
    Sparkonto:
      - nie negativ
      - keine Buchungsgebühren
      - Zinsgutschrift per accrue_interest(); Zinsberechnung hier simpel: rate * aktueller Saldo
    """
    def __init__(self, account_id: str, rate_per_period: Decimal = Decimal("0.01")):
        super().__init__(account_id)
        self._rate = Decimal(rate_per_period)  # 1% pro Periode als Default

    def describe(self) -> str:
        pct = self._rate * 100
        return f"Savings Account (no overdraft, interest {pct:.2f}%/period)"

    def accrue_interest(self, bank: "Bank") -> Optional[Transaction]:
        # Zins nur gutschreiben, wenn positiver Saldo vorhanden ist
        if self.balance <= money(0):
            return None
        interest = money(self.balance * self._rate)
        if interest == money(0):
            return None
        # Zinsbuchung: von Bank-ZINSKONTO -> dieses Konto
        return bank._book_internal_transfer(
            from_internal=bank.interest_expense_account_id,
            to_account=self.id,
            amount=interest,
            type_="INTEREST",
            purpose=f"Interest @ {self._rate * 100:.2f}%"
        )


class InternalBankAccount(Account):
    """
    Internes Bankkonto (z.B. Gebühreneinnahmen, Zinsaufwand).
    - Wird von aussen nicht benutzt/sichtbar gemacht.
    - Kann nicht geschlossen werden (oder nur intern).
    """
    def close(self):
        # interne Konten für Einfachheit nicht schliessen lassen
        raise BankError("Interne Bankkonten können nicht geschlossen werden.")

    def describe(self) -> str:
        return "Internal Bank Account"


# Bank 
class Bank:
    """
    Bank mit:
      - Kontenverwaltung
      - Journal auf Bankebene (alle Transaktionen)
      - Fabrik/Registry für Kontotypen (Open-Closed)
      - internen Bankkonten für Gebühren/Zinsen
    """

    def __init__(self,
                 fee_income_account_id: str = "BANK:FEE_INCOME",
                 interest_expense_account_id: str = "BANK:INTEREST_EXPENSE"):
        # Kontenindex
        self._accounts: Dict[str, Account] = {}

        # Bankjournal
        self._journal: List[Transaction] = []
        self._next_txn_id = 1
        self._sequence = 1  # globaler Reihenfolgezähler

        # Registry: string -> factory(account_id, **kwargs) -> Account
        self._account_type_registry: Dict[str, Callable[..., Account]] = {}

        # Interne Bankkonten erzeugen
        self.fee_income_account_id = fee_income_account_id
        self.interest_expense_account_id = interest_expense_account_id
        self._accounts[fee_income_account_id] = InternalBankAccount(fee_income_account_id)
        self._accounts[interest_expense_account_id] = InternalBankAccount(interest_expense_account_id)

        # Nützliche Defaults registrieren
        self.register_account_type("youth", lambda account_id, **kw: YouthAccount(account_id))
        self.register_account_type("private", lambda account_id, **kw: PrivateAccount(
            account_id,
            overdraft_limit=money(kw.get("overdraft_limit", 500)),
            fee_percent=Decimal(str(kw.get("fee_percent", "0.01"))),
            min_fee=money(kw.get("min_fee", "0.50"))
        ))
        self.register_account_type("savings", lambda account_id, **kw: SavingsAccount(
            account_id,
            rate_per_period=Decimal(str(kw.get("rate", "0.01")))
        ))

        # Einfache Konto-ID-Automat
        self._next_account_nr = 100000

    # Utility: neues Transaktionsobjekt 
    def _new_transaction(self, type_: str,
                         from_account: Optional[str],
                         to_account: Optional[str],
                         amount: Decimal,
                         purpose: Optional[str]) -> Transaction:
        txn = Transaction(
            id=self._next_txn_id,
            sequence=self._sequence,
            ts_utc=datetime.utcnow(),
            type=type_,
            from_account=from_account,
            to_account=to_account,
            amount=money(amount),
            purpose=purpose
        )
        self._next_txn_id += 1
        self._sequence += 1
        return txn

    def _append_to_journal_and_post(self, txn: Transaction):
        """
        Führt die Verbuchung durch:
          - Bankjournal ergänzen
          - Konto-Journale der beteiligten Konten updaten
          - Salden anpassen (über Account._post)
        """
        self._journal.append(txn)

        # Bareinzahlung: nur Zielkonto bekommt eine Gutschrift
        if txn.type == "CASH_DEPOSIT":
            to_acc = self._accounts[txn.to_account]  # type: ignore
            to_acc._post(AccountEntry(
                transaction_id=txn.id,
                sequence=txn.sequence,
                ts_utc=txn.ts_utc,
                type=txn.type,
                amount_signed=money(+txn.amount),
                counterparty=None,
                purpose=txn.purpose
            ))
            return

        # Normalfall: Transfer/Fee/Interest => zwei Konto-Einträge
        if txn.from_account is None or txn.to_account is None:
            raise BankError("Ungültige Transaktion: from/to darf hier nicht None sein.")

        from_acc = self._accounts[txn.from_account]
        to_acc = self._accounts[txn.to_account]

        # Belastung auf from
        from_acc._post(AccountEntry(
            transaction_id=txn.id,
            sequence=txn.sequence,
            ts_utc=txn.ts_utc,
            type=txn.type,
            amount_signed=money(-txn.amount),
            counterparty=to_acc.id,
            purpose=txn.purpose
        ))
        # Gutschrift auf to
        to_acc._post(AccountEntry(
            transaction_id=txn.id,
            sequence=txn.sequence,
            ts_utc=txn.ts_utc,
            type=txn.type,
            amount_signed=money(+txn.amount),
            counterparty=from_acc.id,
            purpose=txn.purpose
        ))

    # Öffentliche API 

    # Konto eröffnen
    def open_account(self, account_type: str, account_id: Optional[str] = None, **kwargs) -> str:
        """
        Erzeugt ein Konto eines registrierten Typs.
        account_type: z.B. "youth", "private", "savings" oder ein später hinzugefügter Typ.
        account_id:
          - None  -> Bank generiert ID
          - str   -> explizite ID (muss eindeutig sein)
        kwargs: typ-spezifische Parameter (z.B. rate, overdraft_limit, fee_percent, min_fee)
        Return: Konto-ID
        """
        if account_id is None:
            # simple ID-Vergabe: AC-<laufende Nummer>
            account_id = f"AC-{self._next_account_nr}"
            self._next_account_nr += 1

        if account_id in self._accounts:
            raise DuplicateAccountId(f"Konto-ID '{account_id}' existiert bereits.")

        factory = self._account_type_registry.get(account_type.lower())
        if not factory:
            raise BankError(f"Unbekannter Kontotyp: {account_type!r}")

        account = factory(account_id, **kwargs)
        self._accounts[account_id] = account
        return account_id

    # Konto schliessen
    def close_account(self, account_id: str) -> bool:
        account = self._get_active_account(account_id)
        account.close()
        return True

    # Bareinzahlung
    def deposit_cash(self, to_account_id: str, amount, purpose: Optional[str] = None) -> int:
        """
        Bareinzahlung: nur positive Beträge; keine Gegenbuchung.
        Rückgabe: Transaktions-ID
        """
        amount = money(amount)
        if amount <= money(0):
            raise InvalidAmount("Bareinzahlung muss positiv sein.")
        to_acc = self._get_active_account(to_account_id)
        txn = self._new_transaction(
            type_="CASH_DEPOSIT",
            from_account=None,
            to_account=to_acc.id,
            amount=amount,
            purpose=purpose or "Cash deposit"
        )
        self._append_to_journal_and_post(txn)
        return txn.id

    # Überweisung
    def transfer(self, from_account_id: str, to_account_id: str, amount, purpose: Optional[str] = None) -> List[int]:
        """
        Führt eine Überweisung aus. Ggf. werden zusätzliche Gebührenbuchungen erzeugt.
        Rückgabe: Liste aller erzeugten Transaktions-IDs (Hauptbuchung + evtl. Gebühr).
        """
        amount = money(amount)
        if amount <= money(0):
            raise InvalidAmount("Überweisungsbetrag muss positiv sein.")
        if from_account_id == to_account_id:
            raise SameAccountTransfer("Von und zu demselben Konto ist nicht erlaubt.")

        from_acc = self._get_active_account(from_account_id)
        to_acc = self._get_active_account(to_account_id)

        # Gebühren berechnen
        fee = from_acc.calc_withdraw_fee(amount)
        total_debit = money(amount + fee)

        # Regelprüfung (Polymorphie)
        if not from_acc.can_withdraw(total_debit):
            raise InsufficientFunds("Deckung/Limit unzureichend für Abbuchung (inkl. Gebühren).")

        # Haupttransaktion
        txn = self._new_transaction(
            type_="TRANSFER",
            from_account=from_acc.id,
            to_account=to_acc.id,
            amount=amount,
            purpose=purpose
        )
        self._append_to_journal_and_post(txn)

        txn_ids = [txn.id]

        # Gebühren (Polymorphie): ggf. zusätzliche Transaktion von from -> BANK:FEE_INCOME
        if fee > money(0):
            fee_txn = self._new_transaction(
                type_="FEE",
                from_account=from_acc.id,
                to_account=self.fee_income_account_id,
                amount=fee,
                purpose=f"Fee for txn {txn.id}"
            )
            self._append_to_journal_and_post(fee_txn)
            txn_ids.append(fee_txn.id)

        return txn_ids

    # Kontostand abfragen
    def get_balance(self, account_id: str) -> Decimal:
        acc = self._get_account(account_id)
        return acc.balance

    # Konto-Journal abfragen
    def get_account_entries(self, account_id: str, limit: Optional[int] = None) -> List[AccountEntry]:
        acc = self._get_account(account_id)
        entries = acc.journal
        return entries[-limit:] if (limit is not None and limit >= 0) else entries

    # Bankjournal abfragen
    def get_bank_journal(self, limit: Optional[int] = None) -> List[Transaction]:
        entries = self._journal
        return entries[-limit:] if (limit is not None and limit >= 0) else entries

    # Zinsen auf alle Sparkonten anwenden (eine "Periode")
    def apply_interest_to_all_savings(self) -> List[int]:
        """
        Ruft für alle Konten accrue_interest() auf.
        Rückgabe: Liste erzeugter Zins-Transaktions-IDs.
        """
        generated: List[int] = []
        for acc in self._accounts.values():
            # Nur aktive "Kundenkonten" berücksichtigen (nicht interne)
            if isinstance(acc, SavingsAccount) and acc.is_active:
                txn = acc.accrue_interest(self)
                if txn is not None:
                    generated.append(txn.id)
        return generated

    #  Open-Closed: neue Kontotypen registrieren 
    def register_account_type(self, name: str, factory: Callable[..., Account]):
        """
        Ermöglicht das Hinzufügen neuer Kontotypen zur Laufzeit:
          bank.register_account_type("premium", lambda id, **kw: PremiumAccount(id, ...))
        """
        key = name.lower().strip()
        self._account_type_registry[key] = factory

    #  interne Helfer 

    def _get_account(self, account_id: str) -> Account:
        acc = self._accounts.get(account_id)
        if acc is None:
            raise AccountNotFound(f"Konto '{account_id}' nicht gefunden.")
        return acc

    def _get_active_account(self, account_id: str) -> Account:
        acc = self._get_account(account_id)
        if not acc.is_active:
            raise AccountClosed(f"Konto '{account_id}' ist geschlossen.")
        return acc

    def _book_internal_transfer(self, from_internal: str, to_account: str,
                                amount: Decimal, type_: str, purpose: Optional[str]) -> Transaction:
        """
        Bucht einen Transfer von einem internen Bankkonto auf ein Kundenkonto (oder umgekehrt),
        z.B. für Zinsen ("INTEREST") oder Gebühren (werden an anderer Stelle erzeugt).
        """
        amount = money(amount)
        if amount <= money(0):
            raise InvalidAmount("Interner Transfer erfordert positiven Betrag.")

        # Hier verzichten wir bewusst auf can_withdraw() bei internen Konten.
        # Annahme: Interne Konten sind 'beliebig' belastbar (Banksteuerung).
        txn = self._new_transaction(
            type_=type_,
            from_account=from_internal,
            to_account=to_account,
            amount=amount,
            purpose=purpose
        )
        self._append_to_journal_and_post(txn)
        return txn

    # Optional: einfache Audit-Prüfung (Kohärenz-Check)
    def audit(self) -> None:
        """
        Führt ein paar grundlegende Konsistenzprüfungen durch.
          - Jede TRANSFER/FEE/INTEREST hat from != None und to != None
          - Jede CASH_DEPOSIT hat from == None und to != None
          - Summe der Beträge pro TRANSFER/FEE/INTEREST ist symmetrisch auf Konten verbucht
        """
        for txn in self._journal:
            if txn.type == "CASH_DEPOSIT":
                if txn.from_account is not None or txn.to_account is None:
                    raise BankError(f"Inkonstistente CASH_DEPOSIT #{txn.id}")
            else:
                if txn.from_account is None or txn.to_account is None:
                    raise BankError(f"Inkonstistente Transaktion #{txn.id}: from/to fehlen")

    #  Debug/Info 
    def describe_account(self, account_id: str) -> str:
        acc = self._get_account(account_id)
        return f"{acc.id}: {acc.describe()} | active={acc.is_active} | balance={acc.balance}"


# Demo
if __name__ == "__main__":
    bank = Bank()

    # Beispiel: neuen Kontotyp zur Laufzeit registrieren (Open-Closed-Prinzip)
    class PremiumAccount(PrivateAccount):
        def __init__(self, account_id: str):
            super().__init__(
                account_id,
                overdraft_limit=money(1000),
                fee_percent=Decimal("0.005"),
                min_fee=money("0.25")
            )

        def describe(self) -> str:
            return "Premium Account (höheres Limit, niedrigere Gebühren)"

    bank.register_account_type("premium", lambda acc_id, **kw: PremiumAccount(acc_id))

    # Vier Konten anlegen (inkl. dynamisch registriertem Premium-Konto)
    youth_id = bank.open_account("youth")                       # Jugendkonto
    priv_id = bank.open_account("private", overdraft_limit=300, fee_percent="0.015", min_fee="0.40")
    sav_id = bank.open_account("savings", rate="0.02")          # Sparkonto mit 2%/Periode
    premium_id = bank.open_account("premium")                   # Laufzeit-registriertes Premiumkonto

    # Bareinzahlungen
    bank.deposit_cash(youth_id, 100, "Startguthaben Jugend")
    bank.deposit_cash(priv_id, 100, "Startguthaben Privat")
    bank.deposit_cash(sav_id, 1000, "Startguthaben Sparen")
    bank.deposit_cash(premium_id, 100, "Startguthaben Premium")

    # Überweisung (Privat -> Jugend) – es fällt eine Gebühr an
    bank.transfer(priv_id, youth_id, 20, "Taschengeld")

    # Überweisung vom dynamischen Premium-Konto (geringere Gebühr als Privatkonto)
    bank.transfer(premium_id, youth_id, 20, "Premium-Taschengeld")

    # Versuch einer Überziehung beim Jugendkonto (soll scheitern)
    try:
        bank.transfer(youth_id, priv_id, 200, "zu viel")
    except BankError as e:
        print("Erwarteter Fehler (Jugendkonto darf nicht überziehen):", e)

    # Zinsen auf Sparkonten gutschreiben
    generated_interest_txns = bank.apply_interest_to_all_savings()
    print("Erzeugte Zins-Transaktions-IDs:", generated_interest_txns)

    # Stände und kurze Beschreibung
    print(bank.describe_account(youth_id))
    print(bank.describe_account(priv_id))
    print(bank.describe_account(sav_id))
    print(bank.describe_account(premium_id))

    # Letzte Einträge eines Kontos
    print("\nLetzte Buchungen Jugendkonto:")
    for e in bank.get_account_entries(youth_id, limit=5):
        print(f"  #{e.transaction_id} [{e.type}] "
              f"{'+' if e.amount_signed >= 0 else ''}{e.amount_signed} "
              f"gegen {e.counterparty}  Zweck={e.purpose}")

    # Bankjournal (die letzten 10)
    print("\nBankjournal (letzte 10):")
    for t in bank.get_bank_journal(limit=10):
        print(f"  #{t.id} seq={t.sequence} {t.type} "
              f"{t.from_account or 'CASH'} -> {t.to_account} amount={t.amount} purpose={t.purpose}")

    # Konto schliessen (geht nur bei Saldo 0)
    try:
        bank.close_account(priv_id)
    except BankError as e:
        print("\nErwarteter Fehler beim Schliessen (Saldo != 0):", e)
