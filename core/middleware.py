class PrivateResponseMiddleware:
    """Páginas e APIs individuais nunca entram no cache compartilhado do CDN."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Cache-Control'] = 'private, no-store'
        response['CDN-Cache-Control'] = 'no-store'
        response['Vercel-CDN-Cache-Control'] = 'no-store'
        return response
