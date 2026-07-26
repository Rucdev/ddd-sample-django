from dataclasses import dataclass
from datetime import date, timedelta

from shared.domain.value_object import ValueObject

STANDARD_LOAN_DAYS = 14
EXTENDED_LOAN_DAYS = 21


@dataclass(frozen=True)
class LoanPeriod(ValueObject):
    """貸出期間。値オブジェクト。値(日数)が同じなら同じものとして扱う。"""

    days: int = STANDARD_LOAN_DAYS

    def due_date_from(self, start: date) -> date:
        return start + timedelta(days=self.days)


# 標準の貸出期間(14日)。一般会員の貸出開始・延長で使う。
STANDARD_LOAN_PERIOD = LoanPeriod()
# 延長貸出期間(21日)。シルバー・ゴールド会員の貸出開始・延長で使う。
EXTENDED_LOAN_PERIOD = LoanPeriod(days=EXTENDED_LOAN_DAYS)


@dataclass(frozen=True)
class LoanTerms(ValueObject):
    """会員ランクに応じた貸出条件(貸出上限冊数・貸出期間)。値オブジェクト。"""

    loan_limit: int
    loan_period: LoanPeriod


# 会員ランクごとの貸出条件。キーは members モジュールの公開 API が返す
# `MemberDTO.rank` の値("REGULAR" / "SILVER" / "GOLD")。lending は members の
# 内部(`Member.Rank`)を import せず、公開 API が返す文字列値だけで引き当てる。
LOAN_TERMS_BY_MEMBER_RANK: dict[str, LoanTerms] = {
    "REGULAR": LoanTerms(loan_limit=5, loan_period=STANDARD_LOAN_PERIOD),
    "SILVER": LoanTerms(loan_limit=5, loan_period=EXTENDED_LOAN_PERIOD),
    "GOLD": LoanTerms(loan_limit=10, loan_period=EXTENDED_LOAN_PERIOD),
}


def loan_terms_for_rank(rank: str | None) -> LoanTerms:
    """未知のランク・会員不明(None)は一般会員の条件にフォールバックする。"""
    return LOAN_TERMS_BY_MEMBER_RANK.get(rank, LOAN_TERMS_BY_MEMBER_RANK["REGULAR"])
