import base64

import pyshorteners
from django.core.files.base import ContentFile
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .filters import RecipeFilter
from .mixins import ActionMixin
from .models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                     ShoppingCart, Subscription, Tag, User)
from .permisions import IsAuthorOrAdmin
from .serializers import (CustomUserSerializer, IngredientSerializer,
                          PasswordChangeSerializer, RecipeSerializer,
                          ShoppingCardSerializer, ShortRecipeSerializer,
                          SubscribedUserSerializer, TagSerializer,
                          UserCreateResponseSerializer, UsersSerializer)


class CustomUserViewSet(UserViewSet):
    serializer_class = CustomUserSerializer
    queryset = User.objects.all()


class UserViewSet(viewsets.ModelViewSet, ActionMixin):
    queryset = User.objects.all()
    serializer_class = UsersSerializer
    pagination_class = LimitOffsetPagination
    http_method_names = ('get', 'post', 'delete', 'patch', 'put')

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        if request.path == '/api/users/':
            serializer = UserCreateResponseSerializer(response.data)
            return Response(serializer.data, status=response.status_code)
        return response

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='subscriptions'
    )
    def subscriptions(self, request, pk=None):
        user = request.user
        subscribed_user_ids = Subscription.objects.filter(
            user=user
        ).values_list('subscribed_to_id', flat=True)
        subscribed_users = User.objects.filter(id__in=subscribed_user_ids)
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
        return self.handle_action(
            model=Subscription,
            serializer_class=SubscribedUserSerializer,
            request=request,
            subscribed_to=self.get_object()
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
    http_method_names = ['get', 'post']

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


class RecipeViewSet(viewsets.ModelViewSet, ActionMixin):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (IsAuthorOrAdmin,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    @action(
        detail=True,
        methods=['get'],
        url_path='get-link'
    )
    def get_link(self, request, pk=None):
        shortener = pyshorteners.Shortener()
        short_url = shortener.tinyurl.short(
            request.build_absolute_uri()
            .replace('/api', '')
            .replace('/get-link', '')
        )
        return Response({'short-link': short_url})

    @staticmethod
    def destroy_shopping_cart_favorite(id_to_delete, user, model):
        recipe_to_delete = get_object_or_404(Recipe, id=id_to_delete)
        deleted, _ = model.objects.filter(
            author=user, recipe=recipe_to_delete
        ).delete()
        if not deleted:
            return Response(
                {'detail': 'recipe is missing'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def add_to_shopping_cart_favorite(serializer, pk, request):
        get_object_or_404(Recipe, id=pk)
        serializer = serializer(
            data={
                'recipe': pk,
                'author': request.user.id,
            },
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,),
        url_path='shopping_cart',
    )
    def add_to_shopping_cart(self, request, pk):
        return self.add_to_shopping_cart_favorite(
            ShoppingCardSerializer, pk, request
        )

    @add_to_shopping_cart.mapping.delete
    def delete_from_shopping_cart(self, request, pk):
        return self.destroy_shopping_cart_favorite(
            pk, request.user, ShoppingCart
        )

    @action(
        detail=False,
        permission_classes=[IsAuthenticated],
        methods=['get'],
        url_path='download_shopping_cart'
    )
    def download_shopping_cart(self, request):
        user = request.user
        ingredients = RecipeIngredient.objects.filter(
            recipe__shopping_cart__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(amount=Sum('amount'))
        shopping_list = (
            f'Список покупок для: {user.get_full_name()}\n\n'
        )
        shopping_list += '\n'.join([
            f'- {ingredient["ingredient__name"]} '
            f'({ingredient["ingredient__measurement_unit"]})'
            f' - {ingredient["amount"]}'
            for ingredient in ingredients
        ])
        filename = f'{user.username}_shopping_list.txt'
        response = HttpResponse(
            shopping_list, content_type='text.txt; charset=utf-8'
        )
        response['Content-Disposition'] = f'attachment; filename={filename}'
        return response

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='favorite'
    )
    def favorite(self, request, pk=None):
        return self.handle_action(
            model=Favorite,
            serializer_class=ShortRecipeSerializer,
            request=request,
            recipe=self.get_object()
        )
