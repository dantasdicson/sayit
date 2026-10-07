from django.conf import settings
from django.db import connection, DatabaseError
from django.http import Http404, JsonResponse
from django.views.static import serve


def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse({'status': 'unavailable'}, status=503)
    return JsonResponse({'status': 'ok'})


def pedagogical_media(request, path):
    # Apenas arquivos pedagógicos públicos; nunca gravações de estudantes.
    if not path.startswith(('palavras/imagens/', 'palavras/audios/', 'modulos/')) or not path.lower().endswith(('.webp', '.mp3')):
        raise Http404
    return serve(request, path, document_root=settings.MEDIA_ROOT)
