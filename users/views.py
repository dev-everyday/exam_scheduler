from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate, login, logout
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from .models import User
from .serializers import (
    ErrorResponseSerializer,
    UserListResponseSerializer,
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    LoginSerializer
)

@swagger_auto_schema(
    method='post',
    operation_summary="로그인 API",
    operation_description="사용자명과 비밀번호로 로그인합니다.",
    request_body=LoginSerializer,
    responses={
        200: UserSerializer,
        400: ErrorResponseSerializer
    }
)
@api_view(['POST'])
def login_view(request):
    """
    로그인 API
    
    사용자명과 비밀번호로 로그인합니다.
    """
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        user = authenticate(username=username, password=password)
        
        if user is not None:
            login(request, user)
            serializer = UserSerializer({
                'user_id': user.id,
                'username': user.username,
                'is_superuser': user.is_superuser,
                'created_at': user.created_at
            })
            return Response(serializer.data, status=200)
        else:
            serializer = ErrorResponseSerializer({'error': '잘못된 사용자명 또는 비밀번호입니다.'})
            return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='post',
    operation_summary="로그아웃 API",
    operation_description="현재 로그인된 사용자를 로그아웃합니다.",
    responses={
        200: None
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    로그아웃 API
    
    현재 로그인된 사용자를 로그아웃합니다.
    """
    logout(request)
    return Response(status=status.HTTP_200_OK)

@swagger_auto_schema(
    method='get',
    operation_summary="사용자 목록 조회 API",
    operation_description="관리자만 모든 사용자 목록을 조회할 수 있습니다.",
    responses={
        200: UserListResponseSerializer,
        403: ErrorResponseSerializer
    }
)
@swagger_auto_schema(
    method='post',
    operation_summary="사용자 생성 API",
    operation_description="새로운 사용자를 생성합니다.",
    request_body=UserCreateSerializer,
    responses={
        201: UserSerializer,
        400: ErrorResponseSerializer
    }
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def user_view(request):
    """
    사용자 API
    
    GET: 사용자 목록 조회
    - 관리자만 모든 사용자 목록을 조회할 수 있습니다.
    
    POST: 사용자 생성
    - 새로운 사용자를 생성합니다.
    """
    if request.method == 'GET':
        users = User.objects.all()
        user_data = UserListResponseSerializer({'users': UserSerializer(users, many=True).data})
        return Response(user_data.data)
    
    elif request.method == 'POST':
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            
            if User.objects.filter(username=username).exists():
                return Response(ErrorResponseSerializer({'error': '이미 존재하는 사용자명입니다.'}).data,
                                 status=status.HTTP_400_BAD_REQUEST)
            
            user = User.objects.create_user(
                username=username,
                password=password
            )
            
            return Response(UserSerializer({'user_id': user.id, 'username': user.username}).data,
                             status=status.HTTP_201_CREATED)
        return Response(ErrorResponseSerializer(serializer.errors).data, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='get',
    operation_summary="사용자 상세 조회 API",
    operation_description="특정 사용자의 상세 정보를 조회합니다.",
    responses={
        200: UserSerializer,
        401: ErrorResponseSerializer,
        403: ErrorResponseSerializer,
        404: ErrorResponseSerializer
    }
)
@swagger_auto_schema(
    method='put',
    operation_summary="사용자 정보 수정 API",
    operation_description="특정 사용자의 정보를 수정합니다.",
    request_body=UserUpdateSerializer,
    responses={
        200: UserSerializer,
        400: ErrorResponseSerializer,
        403: ErrorResponseSerializer,
        404: ErrorResponseSerializer
    }
)
@swagger_auto_schema(
    method='delete',
    operation_summary="사용자 삭제 API",
    operation_description="특정 사용자를 삭제합니다.",
    responses={
        204: None,
        403: ErrorResponseSerializer,
        404: ErrorResponseSerializer
    }
)
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def user_detail_view(request, user_id):
    """
    사용자 상세 조회/수정/삭제 API
    
    GET: 사용자 정보 조회
    PUT: 사용자 정보 수정
    DELETE: 사용자 삭제 (관리자만 가능)
    """
    if not request.user.is_superuser and request.user.id != user_id:
        return Response(ErrorResponseSerializer({'error': '권한이 없습니다.'}).data,
                         status=status.HTTP_403_FORBIDDEN)
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(ErrorResponseSerializer({'error': '사용자를 찾을 수 없습니다.'}).data,
                         status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = UserSerializer(user)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = UserUpdateSerializer(data=request.data)
        if serializer.is_valid():
            if 'username' in serializer.validated_data:
                new_username = serializer.validated_data['username']
                if new_username != user.username and User.objects.filter(username=new_username).exists():
                    return Response(ErrorResponseSerializer({'error': '이미 존재하는 사용자명입니다.'}).data,
                                     status=status.HTTP_400_BAD_REQUEST)
                user.username = new_username
            
            if 'password' in serializer.validated_data:
                user.password = make_password(serializer.validated_data['password'])
            
            user.save()
            
            return Response(UserSerializer({'user_id': user.id, 'username': user.username}).data,
                             status=status.HTTP_200_OK)
        return Response(ErrorResponseSerializer(serializer.errors).data, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        if not request.user.is_superuser:
            return Response(ErrorResponseSerializer({'error': '권한이 없습니다.'}).data,
                             status=status.HTTP_403_FORBIDDEN)
        user.delete()
        return Response(
            status=status.HTTP_204_NO_CONTENT
        )