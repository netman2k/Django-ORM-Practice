from rest_framework.routers import DefaultRouter

from prefetch_related import views

router = DefaultRouter()
router.register(r"pizzas", views.PizzaViewSet)
router.register(r"toppings", views.ToppingViewSet)
router.register(r"restaurants", views.RestaurantViewSet)

urlpatterns = router.urls
