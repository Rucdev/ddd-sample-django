from django.test import TestCase
from django.urls import reverse


class HomeViewTests(TestCase):
    def test_home_page_loads_and_links_to_screens(self) -> None:
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("ordering:order_list"))
        self.assertContains(response, reverse("kitchen:ticket_list"))
        self.assertContains(response, reverse("inventory:kit_list"))


class DemoFixtureTests(TestCase):
    fixtures = ["demo"]

    def test_demo_fixture_loads_and_customer_can_order(self) -> None:
        response = self.client.post(
            reverse("ordering:place_order"),
            {
                "customer_id": "00000000-0000-0000-0000-000000000003",
                "qty_20000000-0000-0000-0000-000000000002": "2",
            },
            follow=True,
        )

        page_messages = [str(m) for m in response.context["messages"]]
        self.assertIn("注文を受け付けました。", page_messages)
        self.assertContains(response, "810円")  # ゴールド会員: 900 円 - 10%

    def test_demo_fixture_has_kits_and_ordering_beyond_stock_is_rejected(self) -> None:
        response = self.client.post(
            reverse("ordering:place_order"),
            {
                "customer_id": "00000000-0000-0000-0000-000000000003",
                "qty_20000000-0000-0000-0000-000000000005": "4",  # ホットサンドのキットは 3 個
            },
            follow=True,
        )

        page_messages = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("in stock" in m for m in page_messages))
