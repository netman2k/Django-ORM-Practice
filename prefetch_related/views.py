from rest_framework import viewsets

from prefetch_related.models import Pizza, Restaurant, Topping
from prefetch_related.serializers import (
    PizzaSerializer,
    RestaurantSerializer,
    ToppingSerializer,
)

# Create your views here.


class PizzaViewSet(viewsets.ModelViewSet):
    # NOTE: The problem with this is that every time `Pizza.__str__()` asks
    # for `self.toppings.all()` it has to query the database, so `Pizza.objects.all()`
    # will run a query on the Toppings table for `every` item in the Pizza `QuerySet`
    queryset = Pizza.objects.all()

    # NOTE: This can reduece to just two queries using `prefetch_related`:
    # This implies a `self.toppings.all()` for each `Pizza`; now each time `self.toppings.all()`
    # is called, instead of having to go to the database for the items, it will find them in
    # prefetched `QuerySet` cache that was populated in a single query.
    # queryset = Pizza.objects.prefetch_related("toppings").all()

    serializer_class = PizzaSerializer


class ToppingViewSet(viewsets.ModelViewSet):
    queryset = Topping.objects.all()
    serializer_class = ToppingSerializer


class RestaurantViewSet(viewsets.ModelViewSet):
    queryset = Restaurant.objects.all()

    # NOTE: Optimization 1 - prefetching pizzas
    # queryset = Restaurant.objects.prefetch_related("pizzas").all()

    # NOTE: Optimization 2 - prefetching pizzas and its toppings
    # queryset = Restaurant.objects.prefetch_related("pizzas__toppings").all()
    serializer_class = RestaurantSerializer
