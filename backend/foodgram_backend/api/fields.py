import base64

from django.core.files.base import ContentFile
from rest_framework import serializers


class CustomImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            img_data = base64.b64decode(imgstr)
            file_name = f'temp.{ext}'
            data = ContentFile(img_data, name=file_name)
        return super().to_internal_value(data)
