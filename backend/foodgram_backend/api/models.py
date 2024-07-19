from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models

from .utils import (
    LITERALS,
    MIN_COOKING_TIME,
    MAX_LENGTH,
    MAX_LENGTH_EMAIL,
    MAX_LENGTH_SLUG,
    MAX_LENGTH_USERNAME,
    MAX_LENGTH_FIRST_NAME,
    MAX_LENGTH_LAST_NAME,
    validate_username
)


class User(AbstractUser):
    email = models.EmailField(
        unique=True,
        max_length=MAX_LENGTH_EMAIL,
        verbose_name='email'
    )
    username = models.CharField(
        max_length=MAX_LENGTH_USERNAME,
        unique=True,
        validators=[
            LITERALS,
            validate_username
        ],
        null=True,
        verbose_name='username'
    )
    first_name = models.CharField(
        max_length=MAX_LENGTH_FIRST_NAME,
        verbose_name='first_name'
    )
    last_name = models.CharField(
        max_length=MAX_LENGTH_LAST_NAME,
        verbose_name='last_name'
    )
    avatar = models.ImageField(null=True, blank=True, verbose_name='avatar')

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.username


class Subscription(models.Model):
    user = models.ForeignKey(
        User,
        related_name='subscribing',
        on_delete=models.CASCADE,
        verbose_name='user'
    )
    subscribed_to = models.ForeignKey(
        User,
        related_name='subscribers',
        on_delete=models.CASCADE,
        verbose_name='subscribed_to'
    )

    class Meta:
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'
        unique_together = ('user', 'subscribed_to')

    def __str__(self):
        return f"{self.user} подписан на {self.subscribed_to}"


class Tag(models.Model):
    name = models.CharField(
        max_length=MAX_LENGTH,
        unique=True,
        verbose_name='name'
    )
    slug = models.SlugField(
        max_length=MAX_LENGTH_SLUG,
        unique=True,
        verbose_name='slug'
    )

    class Meta:
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(max_length=MAX_LENGTH, verbose_name='name')
    measurement_unit = models.CharField(
        max_length=MAX_LENGTH,
        verbose_name='measurement_unit'
    )
    amount = models.IntegerField(null=True, blank=True, verbose_name='amount')

    class Meta:
        verbose_name = 'Ingredient'
        verbose_name_plural = 'Ingredients'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='author'
    )
    name = models.CharField(max_length=MAX_LENGTH, verbose_name='name')
    image = models.ImageField(verbose_name='image')
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        verbose_name='ingredients'
    )
    text = models.TextField(verbose_name='text')
    tags = models.ManyToManyField(Tag, verbose_name='tags')
    cooking_time = models.PositiveIntegerField(
        validators=[
            MinValueValidator(
                MIN_COOKING_TIME,
                message="Время готовки должно быть не менее одной минуты."
            )
        ],
        verbose_name='cooking_time'
    )

    class Meta:
        verbose_name = 'Recipe'
        verbose_name_plural = 'Recipes'

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
        verbose_name='recipe'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='ingredient'
    )
    amount = models.IntegerField(verbose_name='amount')

    class Meta:
        verbose_name = 'RecipeIngredient'
        verbose_name_plural = 'RecipeIngredients'

    def __str__(self):
        return self.recipe


class RecipeTag(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_tags',
        verbose_name='recipe'
    )
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, verbose_name='tag')

    class Meta:
        verbose_name = 'RecipeTag'
        verbose_name_plural = 'RecipeTags'

    def __str__(self):
        return self.recipe


class Favorite(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name='user')
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='recipe'
    )

    class Meta:
        verbose_name = 'Favorite'
        verbose_name_plural = 'Favorites'
        unique_together = ('user', 'recipe')

    def __str__(self):
        return self.user


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='user'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='recipe'
    )

    class Meta:
        verbose_name = 'ShoppingCart'
        verbose_name_plural = 'ShoppingCarts'
        unique_together = ('user', 'recipe')

    def __str__(self):
        return self.user
