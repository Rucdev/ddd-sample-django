from django.conf import settings
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse

from config.views import serve_media


class HomeViewTests(TestCase):
    def test_home_page_loads_and_links_to_screens(self) -> None:
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("ordering:order_list"))
        self.assertContains(response, reverse("kitchen:ticket_list"))
        self.assertContains(response, reverse("seating:seat_board"))


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
        self.assertContains(response, "¥810")  # ゴールド会員: 900 円 - 10%


class ServeMediaTests(SimpleTestCase):
    def test_media_is_served_with_headers_that_block_scripts(self) -> None:
        # スクリプト入りのファイルが MEDIA にあっても、URL を直接開いたときに動かないようにする
        request = RequestFactory().get("/media/menu_items/demo/scone.svg")

        response = serve_media(request, "menu_items/demo/scone.svg", document_root=settings.MEDIA_ROOT)

        self.assertEqual(response.status_code, 200)
        self.assertIn("sandbox", response["Content-Security-Policy"])
        self.assertIn("default-src 'none'", response["Content-Security-Policy"])
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
