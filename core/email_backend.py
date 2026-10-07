"""E-mail transacional por HTTPS, compatível com Render Free."""
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend


class ResendEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages:
            if not message.recipients():
                continue
            try:
                if not settings.RESEND_API_KEY:
                    raise ImproperlyConfigured('Configure RESEND_API_KEY no Render para enviar e-mails.')
                payload = {'from': message.from_email, 'to': message.to,
                           'subject': message.subject, 'text': message.body}
                if message.cc:
                    payload['cc'] = message.cc
                if message.bcc:
                    payload['bcc'] = message.bcc
                if message.reply_to:
                    payload['reply_to'] = message.reply_to
                request = Request('https://api.resend.com/emails',
                    data=json.dumps(payload).encode('utf-8'), method='POST',
                    headers={'Authorization': 'Bearer ' + settings.RESEND_API_KEY,
                             'Content-Type': 'application/json', 'User-Agent': 'SayIt/1.0'})
                with urlopen(request, timeout=settings.EMAIL_TIMEOUT) as response:
                    result = json.load(response)
                    if not result.get('id'):
                        raise RuntimeError('O provedor não confirmou o envio do e-mail.')
                sent += 1
            except HTTPError as error:
                if not self.fail_silently:
                    # Nunca incluir o corpo, token ou dados pessoais na exceção.
                    raise RuntimeError(f'O provedor recusou o e-mail (HTTP {error.code}).') from None
            except Exception:
                if not self.fail_silently:
                    raise
        return sent
