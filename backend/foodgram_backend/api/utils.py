from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

MAX_LENGTH = 256
MAX_LENGTH_EMAIL = 254
MAX_LENGTH_SLUG = 50
MAX_LENGTH_USERNAME = 150
MAX_LENGTH_PASSWORD = 150
LITERALS = RegexValidator(regex=r'^[\w.@+-]+\Z',)
FILENAME_OF_SHOPPING_LIST = 'attachment; filename="shopping_list.txt"'
MIN_COOKING_TIME = 1
MAX_LENGTH_FIRST_NAME = 150
MAX_LENGTH_LAST_NAME = 150


def validate_username(value):
    if "me" == value:
        raise ValidationError("Имя пользователя не может быть 'me'.")
