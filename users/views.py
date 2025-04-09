from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate, login, logout
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import User
from .serializers import (
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
        200: openapi.Response(
            description="로그인 성공",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING, description='로그인 성공 메시지'),
                    'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='사용자 ID'),
                    'username': openapi.Schema(type=openapi.TYPE_STRING, description='사용자명'),
                    'is_superuser': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='관리자 여부')
                }
            )
        ),
        400: openapi.Response(
            description="로그인 실패",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING, description='에러 메시지')
                }
            )
        )
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
            return Response({
                'message': '로그인을 성공하였습니다.',
                'user_id': user.id,
                'username': user.username,
                'is_superuser': user.is_superuser
            })
        else:
            return Response(
                {'error': '잘못된 사용자명 또는 비밀번호입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    로그아웃 API
    
    현재 로그인된 사용자를 로그아웃합니다.
    """
    logout(request)
    return Response({
        'message': '로그아웃을 성공하였습니다.'
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def user_list(request):
    """
    사용자 목록 조회 API
    
    관리자만 모든 사용자 목록을 조회할 수 있습니다.
    """
    users = User.objects.all()
    serializer = UserSerializer(users, many=True)
    return Response({'users': serializer.data})

@api_view(['POST'])
def user_create(request):
    """
    사용자 생성 API
    
    새로운 사용자를 생성합니다.
    """
    serializer = UserCreateSerializer(data=request.data)
    if serializer.is_valid():
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        if User.objects.filter(username=username).exists():
            return Response(
                {'error': '이미 존재하는 사용자명입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = User.objects.create_user(
            username=username,
            password=password
        )
        
        return Response({
            'message': '사용자가 성공적으로 생성되었습니다.',
            'user_id': user.id,
            'username': user.username
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def user_detail(request, user_id):
    """
    사용자 상세 조회/수정/삭제 API
    
    GET: 사용자 정보 조회
    PUT: 사용자 정보 수정
    DELETE: 사용자 삭제 (관리자만 가능)
    """
    if not request.user.is_superuser and request.user.id != user_id:
        return Response(
            {'error': '권한이 없습니다.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {'error': '사용자를 찾을 수 없습니다.'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        serializer = UserSerializer(user)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = UserUpdateSerializer(data=request.data)
        if serializer.is_valid():
            if 'username' in serializer.validated_data:
                new_username = serializer.validated_data['username']
                if new_username != user.username and User.objects.filter(username=new_username).exists():
                    return Response(
                        {'error': '이미 존재하는 사용자명입니다.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                user.username = new_username
            
            if 'password' in serializer.validated_data:
                user.password = make_password(serializer.validated_data['password'])
            
            user.save()
            return Response({
                'message': '사용자 정보가 성공적으로 수정되었습니다.',
                'user_id': user.id,
                'username': user.username
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        if not request.user.is_superuser:
            return Response(
                {'error': '권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user.delete()
        return Response(
            {'message': '사용자가 성공적으로 삭제되었습니다.'},
            status=status.HTTP_204_NO_CONTENT
        )