# Lesson: `prefetch_related` in Django

Reference: https://docs.djangoproject.com/en/6.1/ref/models/querysets/#prefetch-related

## 1. The problem: the N+1 query

Open `prefetch_related/models.py`. A `Pizza` has many `Topping`s, and `Pizza.__str__` reads them:

```python
class Pizza(models.Model):
    ...
    def __str__(self):
        return "%s (%s)" % (
            self.name,
            ", ".join(topping.name for topping in self.toppings.all()),
        )
```

Now run this:

```python
for pizza in Pizza.objects.all():
    print(str(pizza))
```

Django runs **one query** for the pizzas, then **one more query per pizza** for its toppings. With 4 pizzas that is 5 queries. This is the N+1 problem. It grows with the number of rows, so 1,000 pizzas means 1,001 queries.

## 2. The fix: `prefetch_related`

`prefetch_related` loads a related set with a separate query, then attaches the results to each object in Python.

```python
for pizza in Pizza.objects.prefetch_related("toppings"):
    print(str(pizza))
```

Now there are **2 queries** no matter how many pizzas there are:

1. `SELECT ... FROM pizza`
2. `SELECT ... FROM topping INNER JOIN pizza_toppings ... WHERE pizza_id IN (...)`

Each `pizza.toppings.all()` call reads from the prefetch cache and does not touch the database.

This is already in your code. In `prefetch_related/views.py`, `PizzaViewSet` has the optimized line commented out:

```python
# queryset = Pizza.objects.prefetch_related("toppings").all()
```

Uncomment it and compare the number of queries in the Django debug toolbar or with `CaptureQueriesContext`.

## 3. Following relationships across levels: `__`

Lookups can span relations with double underscores. This prefetches a chain:

```python
Restaurant.objects.prefetch_related("pizzas__toppings")
```

That is three queries in total: restaurants, then pizzas, then toppings. Without it, the `RestaurantSerializer` (which nests `pizzas` and each pizza's `toppings`) would run a query for every restaurant and then for every pizza.

`prefetch_related_objects` and multiple arguments also work:

```python
Restaurant.objects.prefetch_related("pizzas", "pizzas__toppings")
```

Each path is prefetched once. Django reuses the `pizzas` prefetch for the second argument.

## 4. `prefetch_related` vs `select_related`

| | `select_related` | `prefetch_related` |
|---|---|---|
| Works on | ForeignKey, OneToOne (forward) | ManyToMany, reverse ForeignKey, reverse OneToOne, and forward FK too |
| How | SQL `JOIN`, one query | Separate query, joined in Python |
| Good for | Following a single object | Following a set of objects |

Your `Restaurant` model has both kinds of relation:

- `pizzas` is a ManyToMany, so use `prefetch_related("pizzas")`.
- `best_pizza` is a ForeignKey, so `select_related("best_pizza")` is the tool for it.

## 5. Check what the serializer actually needs

`RestaurantSerializer` has `best_pizza` as a plain field:

```python
class RestaurantSerializer(serializers.ModelSerializer):
    pizzas = PizzaSerializer(many=True)

    class Meta:
        model = Restaurant
        fields = ["id", "pizzas", "best_pizza"]
```

`best_pizza` is rendered as a primary key, which Django reads from the `best_pizza_id` column. It needs no extra query. Measured on the fixture data (3 restaurants):

| Code | Queries |
|---|---|
| `[r.best_pizza_id for r in Restaurant.objects.all()]` | 1 |
| `[r.best_pizza.name for r in Restaurant.objects.all()]` | 4 |
| `[r.best_pizza.name for r in Restaurant.objects.select_related("best_pizza")]` | 1 |

Lesson: only optimize what your code reads. Prefetching or joining data you never touch is wasted work.

## 6. Measured results (your fixture data)

| Code | Queries |
|---|---|
| `[str(p) for p in Pizza.objects.all()]` | 5 |
| `[str(p) for p in Pizza.objects.prefetch_related("toppings")]` | 2 |
| Restaurants, pizzas, and toppings, no prefetch | 13 |
| `Restaurant.objects.prefetch_related("pizzas")` | 11 |
| `Restaurant.objects.prefetch_related("pizzas__toppings")` | 3 |

`prefetch_related("pizzas")` alone helps only a little, because the toppings are still fetched per pizza. You need the full path `pizzas__toppings` to get the full benefit.

## 7. Advanced: `Prefetch` objects

A plain string prefetches everything. A `Prefetch` object lets you control the query:

```python
from django.db.models import Prefetch

Restaurant.objects.prefetch_related(
    Prefetch("pizzas", queryset=Pizza.objects.order_by("name"), to_attr="sorted_pizzas")
)
```

- `queryset=` filters or orders the prefetched rows.
- `to_attr=` stores the result in a new list attribute instead of the manager. Here `restaurant.sorted_pizzas` is a plain list.

## 8. Common pitfalls

1. **Calling `.filter()` or `.order_by()` after prefetching throws the cache away.** `pizza.toppings.all()` uses the cache, but `pizza.toppings.filter(name="Basil")` runs a new query. Use a `Prefetch` object with a queryset instead.
2. **Prefetching a relation you never read** adds a query for no benefit.
3. **Prefetching inside a loop** does not help. The prefetch has to be on the queryset before it is evaluated.
4. **Forgetting `.all()` on the viewset.** In DRF, `queryset` is evaluated per request, so put the prefetch on the class attribute as your code does.

## Exercises

Work through these in your Django shell or a test file (`prefetch_related/tests.py` is empty and ready to use).

1. **Count it.** Use `django.test.utils.CaptureQueriesContext` to count queries for `Restaurant.objects.all()` serialized with `RestaurantSerializer`, first without any prefetch, then with `prefetch_related("pizzas__toppings")`.
2. **Sorted toppings.** Write a `Prefetch("toppings", queryset=Topping.objects.order_by("name"), to_attr="sorted_toppings")` on `Pizza`, and print each pizza's `sorted_toppings`.
3. **Find the trap.** Prefetch `toppings` on `Pizza`, then call `pizza.toppings.filter(name__startswith="M")`. Use `CaptureQueriesContext` to confirm a new query runs. Then rewrite it with a `Prefetch` object so it uses one query.
4. **Edge case.** Restaurant 3's `best_pizza` is not in its `pizzas` list. Write a query that gets each restaurant's `best_pizza` name with the fewest queries, and show that `best_pizza` does not need to be in `pizzas`.
5. **Wire it up.** Set `RestaurantViewSet.queryset` to the optimized query, hit `/restaurants/` in the browser, and count the queries with the Django debug toolbar or logging.

## Solutions

<details>
<summary>Show solutions</summary>

1. ```python
   from django.db import connection
   from django.test.utils import CaptureQueriesContext
   from prefetch_related.models import Restaurant
   from prefetch_related.serializers import RestaurantSerializer

   with CaptureQueriesContext(connection) as c:
       RestaurantSerializer(Restaurant.objects.all(), many=True).data
   print("plain:", len(c.captured_queries))

   with CaptureQueriesContext(connection) as c:
       RestaurantSerializer(Restaurant.objects.prefetch_related("pizzas__toppings"), many=True).data
   print("prefetched:", len(c.captured_queries))
   ```
   Expected: plain is well above 3, prefetched is 3.

2. ```python
   from django.db.models import Prefetch
   from prefetch_related.models import Pizza, Topping

   pizzas = Pizza.objects.prefetch_related(
       Prefetch("toppings", queryset=Topping.objects.order_by("name"), to_attr="sorted_toppings")
   )
   for pizza in pizzas:
       print(pizza.name, [t.name for t in pizza.sorted_toppings])
   ```

3. ```python
   from django.db import connection
   from django.test.utils import CaptureQueriesContext
   from prefetch_related.models import Pizza

   pizza = Pizza.objects.prefetch_related("toppings").first()

   with CaptureQueriesContext(connection) as c:
       list(pizza.toppings.filter(name__startswith="M"))
   print("filter queries:", len(c.captured_queries))  # 1, the cache is bypassed

   from django.db.models import Prefetch
   from prefetch_related.models import Topping

   pizza = Pizza.objects.prefetch_related(
       Prefetch("toppings", queryset=Topping.objects.filter(name__startswith="M"), to_attr="m_toppings")
   ).first()
   print([t.name for t in pizza.m_toppings])  # no extra query
   ```

4. ```python
   from prefetch_related.models import Restaurant

   for r in Restaurant.objects.select_related("best_pizza"):
       print(r.id, r.best_pizza.name, [p.name for p in r.pizzas.all()])
   ```
   `best_pizza` is a ForeignKey, so `select_related` joins it in one query. It does not need to appear in `pizzas`.

5. ```python
   # prefetch_related/views.py
   class RestaurantViewSet(viewsets.ModelViewSet):
       queryset = Restaurant.objects.prefetch_related("pizzas__toppings").all()
       serializer_class = RestaurantSerializer
   ```
   Add `select_related("best_pizza")` as well if you want to read `best_pizza` fields beyond its id, for example `Restaurant.objects.select_related("best_pizza").prefetch_related("pizzas__toppings")`.

</details>
