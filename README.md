# Django DB

## Lessons

All lessons live in the `lessons/` folder.

| Lesson | Topic |
|--------|-------|
| [prefetch_related](lessons/prefetch_related.md) | Fixing N+1 queries with `prefetch_related`, `Prefetch` objects, and comparing with `select_related` |

## prefetch_related fixture

The `prefetch_related` app includes sample data in `prefetch_related/fixtures/prefetch_related_data.json`, for testing `prefetch_related` and `select_related` behaviour.

### Models

| Model        | Records | Notes                                                         |
|--------------|---------|---------------------------------------------------------------|
| `Topping`    | 5       | Mozzarella, Tomato, Basil, Pepperoni, Mushroom                |
| `Pizza`      | 4       | Many-to-many with `Topping`; toppings vary from 1 to 3 per pizza |
| `Restaurant` | 3       | Many-to-many with `Pizza` (`pizzas`) and a foreign key to `Pizza` (`best_pizza`) |

Restaurant 3's `best_pizza` is not in its `pizzas` list, which is useful for edge-case tests.

### Loading the fixture

```
python manage.py loaddata prefetch_related_data
```

Make sure all migrations are applied before loading the fixture:

```
python manage.py migrate
```




