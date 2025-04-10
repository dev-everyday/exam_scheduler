from rest_framework import serializers

class ErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField(help_text='에러 메시지') 