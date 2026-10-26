from django.urls import path

from kitchen.presentation import api, views

# app_name で名前空間化し、config/urls.py から include() で束ねる。
app_name = "kitchen"

urlpatterns = [
    path("", views.ticket_list_view, name="ticket_list"),
    path("<uuid:ticket_id>/start/", views.start_cooking_view, name="start_cooking"),
    path("<uuid:ticket_id>/complete/", views.complete_cooking_view, name="complete_cooking"),
    path("api/tickets/", api.TicketListAPIView.as_view(), name="api_ticket_list"),
    path(
        "api/tickets/<uuid:ticket_id>/start/",
        api.StartCookingAPIView.as_view(),
        name="api_start_cooking",
    ),
    path(
        "api/tickets/<uuid:ticket_id>/complete/",
        api.CompleteCookingAPIView.as_view(),
        name="api_complete_cooking",
    ),
]
