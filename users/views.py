from django.http import JsonResponse
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from .models import User
import json

def login_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                return JsonResponse({
                    'message': '로그인을 성공하였습니다.',
                    'user_id': user.id,
                    'username': user.username,
                    'is_superuser': user.is_superuser
                })
            else:
                return JsonResponse({'error': '잘못된 사용자명 또는 비밀번호입니다.'}, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': '잘못된 JSON 형식입니다.'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': '지원하지 않는 메소드입니다.'}, status=405)

@login_required
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return JsonResponse({
            'message': '로그아웃을 성공하였습니다.'
        })
    
    return JsonResponse({'error': '지원하지 않는 메소드입니다.'}, status=405)

@login_required
def user_list(request):
    if request.method == 'GET':
        if not request.user.is_superuser:
            return JsonResponse({'error': '권한이 없습니다.'}, status=403)
        
        users = User.objects.all()
        user_list = [{
            'user_id': user.id,
            'username': user.username,
            'is_superuser': user.is_superuser,
            'created_at': user.created_at
        } for user in users]
        
        return JsonResponse({'users': user_list})
    
    return JsonResponse({'error': '지원하지 않는 메소드입니다.'}, status=405)

def user_create(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return JsonResponse({'error': '사용자명과 비밀번호는 필수입니다.'}, status=400)
            
            if User.objects.filter(username=username).exists():
                return JsonResponse({'error': '이미 존재하는 사용자명입니다.'}, status=400)
            
            user = User.objects.create_user(
                username=username,
                password=password
            )
            
            return JsonResponse({
                'message': '사용자가 성공적으로 생성되었습니다.',
                'user_id': user.id,
                'username': user.username
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': '잘못된 JSON 형식입니다.'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': '지원하지 않는 메소드입니다.'}, status=405)

@login_required
def user_detail(request, user_id):
    if not request.user.is_superuser and request.user.id != user_id:
        return JsonResponse({'error': '권한이 없습니다.'}, status=403)
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': '사용자를 찾을 수 없습니다.'}, status=404)
    
    if request.method == 'GET':
        return JsonResponse({
            'user_id': user.id,
            'username': user.username,
            'is_superuser': user.is_superuser,
            'created_at': user.created_at
        })
    
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            
            if 'username' in data and data['username'] != user.username:
                if User.objects.filter(username=data['username']).exists():
                    return JsonResponse({'error': '이미 존재하는 사용자명입니다.'}, status=400)
                user.username = data['username']
            
            if 'password' in data:
                user.password = make_password(data['password'])
            
            user.save()
            
            return JsonResponse({
                'message': '사용자 정보가 성공적으로 수정되었습니다.',
                'user_id': user.id,
                'username': user.username
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': '잘못된 JSON 형식입니다.'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    elif request.method == 'DELETE':
        if not request.user.is_superuser:
            return JsonResponse({'error': '권한이 없습니다.'}, status=403)
        
        user.delete()
        return JsonResponse({'message': '사용자가 성공적으로 삭제되었습니다.'}, status=204)
    
    return JsonResponse({'error': '지원하지 않는 메소드입니다.'}, status=405)