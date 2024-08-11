from rest_framework import status
from rest_framework.response import Response


class ActionMixin:
    def handle_action(
            self,
            model,
            serializer_class,
            request, user_field='user',
            **kwargs
    ):
        instance = self.get_object()
        user = request.user

        if request.method == 'POST':
            if model.objects.filter(**{user_field: user}, **kwargs).exists():
                return Response(
                    {'detail': f'{instance} уже добавлен.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            model.objects.create(**{user_field: user}, **kwargs)
            serializer = serializer_class(instance, context={
                'request': request
            }
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        obj = model.objects.filter(**{user_field: user}, **kwargs).first()
        if not obj:
            return Response(
                {'detail': f'{instance} не найден.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        obj.delete()
        return Response(
            {'detail': f'{instance} удален.'},
            status=status.HTTP_204_NO_CONTENT
        )
