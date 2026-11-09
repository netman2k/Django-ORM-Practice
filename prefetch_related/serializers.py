from rest_framework import serializers

from prefetch_related.models import Pizza, Restaurant, Topping


class ToppingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topping
        fields = ["id", "name"]


class PizzaSerializer(serializers.ModelSerializer):
    toppings = ToppingSerializer(many=True)

    class Meta:
        model = Pizza
        fields = ["id", "name", "toppings"]


class RestaurantSerializer(serializers.ModelSerializer):
    pizzas = PizzaSerializer(many=True)

    class Meta:
        model = Restaurant
        fields = ["id", "pizzas", "best_pizza"]
