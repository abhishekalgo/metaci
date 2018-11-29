from django.conf.urls import url

from metaci.hirefire import views


urlpatterns = [
    url(r"^test$", views.test, name="test"),
    url(r"^(?P<token>.*)/info$", views.info, name="info"),
]
