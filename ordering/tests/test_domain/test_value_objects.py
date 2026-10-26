import uuid
from unittest import TestCase

from ordering.domain.exceptions import InvalidQuantity
from ordering.domain.value_objects import (
    MAX_QUANTITY_PER_LINE,
    DiscountRate,
    Money,
    OrderLine,
    discount_rate_for_rank,
)


class MoneyTests(TestCase):
    def test_arithmetic(self) -> None:
        self.assertEqual(Money(300) + Money(200), Money(500))
        self.assertEqual(Money(300) - Money(200), Money(100))
        self.assertEqual(Money(300) * 3, Money(900))

    def test_negative_amount_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Money(-1)


class DiscountRateTests(TestCase):
    def test_discount_is_floored_to_whole_yen(self) -> None:
        # 1,234 円の 5% = 61.7 円 → 61 円
        self.assertEqual(DiscountRate(5).discount_for(Money(1234)), Money(61))

    def test_zero_percent_gives_no_discount(self) -> None:
        self.assertEqual(DiscountRate(0).discount_for(Money(1000)), Money(0))

    def test_percent_out_of_range_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            DiscountRate(101)

    def test_rate_by_rank(self) -> None:
        self.assertEqual(discount_rate_for_rank("REGULAR"), DiscountRate(0))
        self.assertEqual(discount_rate_for_rank("SILVER"), DiscountRate(5))
        self.assertEqual(discount_rate_for_rank("GOLD"), DiscountRate(10))

    def test_unknown_rank_falls_back_to_no_discount(self) -> None:
        self.assertEqual(discount_rate_for_rank("PLATINUM"), DiscountRate(0))
        self.assertEqual(discount_rate_for_rank(None), DiscountRate(0))


class OrderLineTests(TestCase):
    def _line(self, quantity: int) -> OrderLine:
        return OrderLine(
            menu_item_id=uuid.uuid4(), name="カフェラテ", unit_price=Money(450), quantity=quantity
        )

    def test_subtotal_is_unit_price_times_quantity(self) -> None:
        self.assertEqual(self._line(3).subtotal, Money(1350))

    def test_quantity_must_be_at_least_one(self) -> None:
        with self.assertRaises(InvalidQuantity):
            self._line(0)

    def test_quantity_upper_limit(self) -> None:
        self._line(MAX_QUANTITY_PER_LINE)  # 上限ちょうどは OK

        with self.assertRaises(InvalidQuantity):
            self._line(MAX_QUANTITY_PER_LINE + 1)
