import base64

from django.contrib.auth.hashers import make_password
from django.core.files.base import ContentFile
from djoser.serializers import UserSerializer
from rest_framework import serializers
from rest_framework.fields import CurrentUserDefault
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.validators import UniqueValidator

from .models import (Favorite, Ingredient, Recipe, RecipeIngredient, RecipeTag,
                     ShoppingCart, Subscription, Tag, User)
from .utils import (LITERALS, MAX_LENGTH_EMAIL, MAX_LENGTH_FIRST_NAME,
                    MAX_LENGTH_LAST_NAME, MAX_LENGTH_PASSWORD,
                    MAX_LENGTH_USERNAME, MIN_COOKING_TIME, validate_username)


class CustomImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            img_data = base64.b64decode(imgstr)
            file_name = f'temp.{ext}'
            data = ContentFile(img_data, name=file_name)
        return super().to_internal_value(data)


class CustomUserSerializer(UserSerializer):
    email = serializers.EmailField(
        max_length=MAX_LENGTH_EMAIL,
        required=True,
    )
    password = serializers.CharField(
        max_length=MAX_LENGTH_PASSWORD,
        required=True,
        write_only=True,
        style={'input_type': 'password', 'placeholder': 'Password'}
    )

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'password'
        )

    def create(self, validated_data):
        validated_data['password'] = make_password(
            validated_data.get('password')
        )
        return super(CustomUserSerializer, self).create(validated_data)


class UsersSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        max_length=MAX_LENGTH_EMAIL,
        required=True,
        validators=[
            UniqueValidator(queryset=User.objects.all())
        ],
    )
    username = serializers.CharField(
        max_length=MAX_LENGTH_USERNAME,
        required=True,
        validators=[
            LITERALS,
            UniqueValidator(queryset=User.objects.all()),
            validate_username
        ]
    )
    first_name = serializers.CharField(
        max_length=MAX_LENGTH_FIRST_NAME,
        required=True
    )
    last_name = serializers.CharField(
        max_length=MAX_LENGTH_LAST_NAME,
        required=True
    )
    password = serializers.CharField(
        max_length=MAX_LENGTH_PASSWORD,
        required=True,
        write_only=True,
        style={'input_type': 'password', 'placeholder': 'Password'}
    )
    is_subscribed = serializers.SerializerMethodField()
    avatar = CustomImageField(required=False)

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'password',
            'is_subscribed',
            'avatar'
        )

    def create(self, validated_data):
        validated_data['password'] = make_password(
            validated_data.get('password')
        )
        return super().create(validated_data)

    def to_representation(self, instance):
        if (
            self.context['request'].method == 'POST'
            and self.context['request'].path == '/api/users/'
        ):
            return {
                'email': instance.email,
                'id': instance.id,
                'username': instance.username,
                'first_name': instance.first_name,
                'last_name': instance.last_name,
            }
        else:
            return super().to_representation(instance)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                'Аккаунт с таким email уже существует.'
            )
        return value

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return Subscription.objects.filter(
            user=user,
            subscribed_to=obj
        ).exists()


class SubscriptionSerializer(serializers.ModelSerializer):
    subscribed_to = UsersSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = ('id', 'subscribed_to')


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Текущий пароль неверен.')
        return value


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False)
    measurement_unit = serializers.CharField(required=False)
    amount = serializers.IntegerField(required=False, write_only=True)

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    name = serializers.CharField(source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit',
        read_only=True
    )
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeTagSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='tag.name', read_only=True)
    slug = serializers.SlugField(source='tag.slug', read_only=True)

    class Meta:
        model = RecipeTag
        fields = ('id', 'name', 'slug')


class RecipeSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientSerializer(many=True)
    tags = PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )
    author = UsersSerializer(required=False, default=CurrentUserDefault())
    is_favorited = serializers.SerializerMethodField(required=False)
    is_in_shopping_cart = serializers.SerializerMethodField(required=False)
    image = CustomImageField(required=True)
    cooking_time = serializers.IntegerField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time'
        )

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return Favorite.objects.filter(user=user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(user=user, recipe=obj).exists()

    def validate_cooking_time(self, value):
        if value < MIN_COOKING_TIME:
            raise serializers.ValidationError(
                "Время готовки не может быть меньше 1 минуты."
            )
        return value

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        ingredients_representation = RecipeIngredientSerializer(
            instance.recipe_ingredients.all(),
            many=True
        ).data
        representation['ingredients'] = ingredients_representation
        tag_representation = RecipeTagSerializer(
            instance.recipe_tags.all(),
            many=True
        ).data
        representation['tags'] = tag_representation
        return representation

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients', [])
        tags_data = validated_data.pop('tags', [])
        recipe = Recipe.objects.create(**validated_data)
        self.create_or_update(recipe, ingredients_data, tags_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', [])
        tags_data = validated_data.pop('tags', [])
        RecipeIngredient.objects.filter(recipe=instance).delete()
        RecipeTag.objects.filter(recipe=instance).delete()
        instance.name = validated_data.get('name', instance.name)
        instance.image = validated_data.get('image', instance.image)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get(
            'cooking_time',
            instance.cooking_time
        )
        instance.save()
        self.create_or_update(instance, ingredients_data, tags_data)
        return instance

    def create_or_update(self, recipe, ingredients_data, tags_data):
        for ingredient_data in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient_data['id'],
                amount=ingredient_data['amount']
            )
        for tag_data in tags_data:
            RecipeTag.objects.create(
                recipe=recipe,
                tag=tag_data
            )


class ShortRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscribedUserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed'
        )

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        recipes = Recipe.objects.filter(author=instance)
        recipes_limit = self.context['request'].query_params.get(
            'recipes_limit'
        )
        if recipes_limit:
            recipes = recipes[:int(recipes_limit)]
        recipes_representation = ShortRecipeSerializer(
            recipes, many=True,
            context=self.context
        ).data
        representation['recipes'] = recipes_representation
        representation['recipes_count'] = recipes.count()
        if instance.avatar:
            representation['avatar'] = instance.avatar.url
        else:
            representation['avatar'] = None
        return representation

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return Subscription.objects.filter(
            user=user,
            subscribed_to=obj
        ).exists()
