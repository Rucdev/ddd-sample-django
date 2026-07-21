from django.test import TestCase
from django.urls import reverse


class HomeViewTests(TestCase):
    def test_home_page_loads_and_links_to_screens(self) -> None:
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("lending:loan_list"))
        self.assertContains(response, reverse("reservation:reservation_list"))
