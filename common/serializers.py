from rest_framework import serializers

class ErrorResponseSerializer(serializers.Serializer):
    """
    에러 응답을 위한 serializer
    - 단일 에러 메시지: {'error': '에러 메시지'}
    - 필드별 에러: {'errors': {'필드1': ['에러1', '에러2'], '필드2': ['에러1']}}
    """
    error = serializers.CharField(help_text='에러 메시지', required=False)
    errors = serializers.DictField(help_text='필드별 에러 메시지', required=False)
    
    def to_representation(self, instance):
        if isinstance(instance, dict) and ('error' in instance or 'errors' in instance):
            return super().to_representation(instance)
            
        if isinstance(instance, dict) and not ('error' in instance or 'errors' in instance):
            return {'errors': instance}
            
        if isinstance(instance, str):
            return {'error': instance}
            
        return {'error': str(instance)} 