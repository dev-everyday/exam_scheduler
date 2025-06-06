from rest_framework import serializers
from .models import User
from rest_framework.authtoken.models import Token

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'is_superuser', 'created_at']
        read_only_fields = ['id', 'created_at']

class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'password']
        extra_kwargs = {
            'username': {'help_text': '사용자명 (필수)'},
            'password': {'help_text': '비밀번호 (필수)', 'write_only': True}
        }

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'password']
        extra_kwargs = {
            'username': {'required': False, 'help_text': '새로운 사용자명 (선택)'},
            'password': {'required': False, 'help_text': '새로운 비밀번호 (선택)', 'write_only': True}
        }

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(help_text='사용자명 (필수)')
    password = serializers.CharField(help_text='비밀번호 (필수)', write_only=True)

class UserListResponseSerializer(serializers.Serializer):
    users = UserSerializer(many=True)

class AuthTokenSerializer(serializers.Serializer):
    token = serializers.CharField(help_text='인증 토큰')
    user = UserSerializer(help_text='사용자 정보')

    @classmethod
    def get_token_response(cls, user):
        token, _ = Token.objects.get_or_create(user=user)
        return {
            'token': token.key,
            'user': UserSerializer(user).data
        }