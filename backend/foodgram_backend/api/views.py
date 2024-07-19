import base64

import pyshorteners
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    Favorite,
    Ingredient,
    Recipe,
    ShoppingCart,
    Subscription,
    Tag,
    User
)
from .permisions import IsAuthorOrAdmin
from .serializers import (
    CustomUserSerializer,
    IngredientSerializer,
    PasswordChangeSerializer,
    RecipeSerializer,
    ShortRecipeSerializer,
    SubscribedUserSerializer,
    TagSerializer,
    UsersSerializer
)
from .utils import FILENAME_OF_SHOPPING_LIST
from .filters import RecipeFilter


class CustomUserViewSet(UserViewSet):
    serializer_class = CustomUserSerializer
    queryset = User.objects.all()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UsersSerializer
    pagination_class = LimitOffsetPagination
    http_method_names = ('get', 'post', 'delete', 'patch', 'put')

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='subscriptions'
    )
    def subscriptions(self, request, pk=None):
        user = request.user
        subscriptions = Subscription.objects.filter(user=user)
        subscribed_users = [
            subscription.subscribed_to for subscription in subscriptions
        ]
        pages = self.paginate_queryset(subscribed_users)
        serializer = SubscribedUserSerializer(
            pages,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='subscribe'
    )
    def subscribe(self, request, pk=None):
        user = request.user
        subscribed_to = self.get_object()
        if request.method == 'POST':
            if Subscription.objects.filter(
                user=user,
                subscribed_to=subscribed_to
            ).exists():
                return Response(
                    {'detail': 'Вы уже подписаны на этого пользователя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if user == subscribed_to:
                return Response(
                    {'detail': 'Вы не можете подписаться на самого себя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            Subscription.objects.create(user=user, subscribed_to=subscribed_to)
            serializer = SubscribedUserSerializer(
                subscribed_to,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            subscription = Subscription.objects.filter(
                user=user,
                subscribed_to=subscribed_to
            ).first()
            if not subscription:
                return Response(
                    {'detail': 'Вы не подписаны на этого пользователя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            subscription.delete()
            return Response(
                {'detail': 'Подписка отменена.'},
                status=status.HTTP_204_NO_CONTENT
            )

    @action(
        detail=False,
        methods=['get', 'patch'],
        permission_classes=[IsAuthenticated],
    )
    def me(self, request):
        if request.method == 'GET':
            serializer = self.get_serializer(request.user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        serializer = self.get_serializer(
            request.user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['put', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='me/avatar'
    )
    def avatar(self, request):
        user = request.user
        data = request.data
        if request.method == 'DELETE':
            user.avatar.delete(save=True)
            return Response(
                {'detail': 'Аватар был удален.'},
                status=status.HTTP_204_NO_CONTENT
            )
        if 'avatar' in data:
            avatar_data = data.get('avatar')
            if avatar_data.startswith('data:image'):
                format, imgstr = avatar_data.split(';base64,')
                ext = format.split('/')[-1]
                user.avatar.save(
                    f'{user.username}.{ext}',
                    ContentFile(base64.b64decode(imgstr)),
                    save=False
                )
                user.save()
                return Response(
                    {'avatar': user.avatar.url},
                    status=status.HTTP_200_OK
                )
            return Response(
                {'detail': 'Неверный формат.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            {'detail': 'В запросе отсутсвует аватар.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(
        detail=False,
        methods=['post'],
        permission_classes=[IsAuthenticated],
        url_path='set_password'
    )
    def set_password(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response(
            {'detail': 'Пароль был изменен.'},
            status=status.HTTP_204_NO_CONTENT
        )


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    http_method_names = ['get']

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('name',)
    http_method_names = ['get']

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    pagination_class = LimitOffsetPagination
    permission_classes = (IsAuthorOrAdmin,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    @action(
        detail=True,
        methods=['get'],
        url_path='get-link'
    )
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        url = request.build_absolute_uri(f'/api/recipes/{recipe.id}/')
        s = pyshorteners.Shortener()
        try:
            short_url = s.tinyurl.short(url)
            return Response({"short-link": short_url})
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='shopping_cart'
    )
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        if request.method == 'POST':
            if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'detail': 'Рецепт уже в корзине.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            ShoppingCart.objects.create(user=user, recipe=recipe)
            serializer = ShortRecipeSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            cart_item = ShoppingCart.objects.filter(
                user=user,
                recipe=recipe
            ).first()
            if not cart_item:
                return Response(
                    {'detail': 'Рецепт не найден в корзине.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            cart_item.delete()
            return Response(
                {'detail': 'Рецепт удален из корзины.'},
                status=status.HTTP_204_NO_CONTENT
            )

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='download_shopping_cart'
    )
    def download_shopping_cart(self, request):
        user = request.user
        cart_items = ShoppingCart.objects.filter(user=user)
        if not cart_items.exists():
            return Response(
                {'detail': 'Корзина пуста.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        ingredients = {}
        for cart_item in cart_items:
            recipe = cart_item.recipe
            for ingredient in recipe.recipe_ingredients.all():
                id = ingredient.ingredient.id
                name = ingredient.ingredient.name
                measurement_unit = ingredient.ingredient.measurement_unit
                amount = ingredient.amount
                if name in ingredients:
                    ingredients[name] = amount
        shopping_list = '\n'.join(
            [
                f'{id}\n  {name}\n  {measurement_unit}\n  {amount}\n'
                for name, amount in ingredients.items()
            ]
        )
        response = HttpResponse(shopping_list, content_type='text/plain')
        response['Content-Disposition'] = FILENAME_OF_SHOPPING_LIST
        return response

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='favorite'
    )
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user
        if request.method == 'POST':
            if Favorite.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'detail': 'Рецепт уже в избранных.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Favorite.objects.create(user=user, recipe=recipe)
            serializer = ShortRecipeSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            favorite = Favorite.objects.filter(
                user=user,
                recipe=recipe
            ).first()
            if not favorite:
                return Response(
                    {'detail': 'Рецепт не найден в избранных.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            favorite.delete()
            return Response(
                {'detail': 'Рецепт удален из избранных.'},
                status=status.HTTP_204_NO_CONTENT
            )

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

    def create(self, request, *args, **kwargs):
        errors = self.validate_recipe_data(request.data)
        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        errors = self.validate_recipe_data(request.data)
        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        instance = self.get_object()
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

    def validate_recipe_data(self, data):
        errors = {}
        if 'ingredients' not in data or not data['ingredients']:
            errors["ingredients"] = ["Это поле не может быть пустым."]

        if 'tags' not in data or not data['tags']:
            errors["tags"] = ["Это поле не может быть пустым."]

        if 'ingredients' in data:
            for ingredient_data in data['ingredients']:
                amount = ingredient_data.get('amount', 0)
                if amount <= 0:
                    errors.setdefault(
                        "ingredients",
                        []
                    ).append("Количество должно быть больше нуля.")

        if 'tags' in data:
            tags_data = []
            for tag_data in data['tags']:
                if tag_data in tags_data:
                    errors.setdefault(
                        "tags",
                        []
                    ).append("Теги должны быть уникальными.")
                else:
                    tags_data.append(tag_data)

        if 'ingredients' in data:
            ingredient_ids = [
                ingredient['id'] for ingredient in data['ingredients']
            ]
            if len(ingredient_ids) != len(set(ingredient_ids)):
                errors.setdefault(
                    "ingredients",
                    []
                ).append("Ингредиенты должны быть уникальными.")

        return errors
