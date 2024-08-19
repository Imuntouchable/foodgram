from django_filters.rest_framework import FilterSet, filters

from .models import Recipe, Tag


class RecipeFilter(FilterSet):
    tags = filters.ModelMultipleChoiceFilter(
        field_name='recipe_tags__tag__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
    )
    is_in_shopping_cart = filters.NumberFilter(
        method='filter_is_in_shopping_cart'
    )
    is_favorited = filters.NumberFilter(method='filter_is_favorited')

    class Meta:
        model = Recipe
        fields = (
            'author',
            'tags',
        )

    def filter_is_in_shopping_cart(self, queryset, name, value):
        user = self.request.user
        print(type(value))
        if value == 1 and not user.is_anonymous:
            return queryset.filter(shoppingcart__user=user)
        elif value == 0:
            return queryset.exclude(shoppingcart__user=user)
        return queryset

    def filter_is_favorited(self, queryset, name, value):
        user = self.request.user
        if value == 1 and not user.is_anonymous:
            return queryset.filter(favorite__user=user)
        elif value == 0:
            return queryset.exclude(favorite__user=user)
        return queryset
