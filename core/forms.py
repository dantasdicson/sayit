from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.utils import timezone


class CadastroForm(UserCreationForm):
    nome_completo = forms.CharField(label='Nome completo', max_length=150,
                                   widget=forms.TextInput(attrs={'autocomplete': 'name'}))
    data_nascimento = forms.DateField(label='Data de nascimento',
        input_formats=['%Y-%m-%d'], widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        error_messages={'invalid': 'Digite uma data de nascimento válida.'})
    email = forms.EmailField(label='E-mail', max_length=254,
        widget=forms.EmailInput(attrs={'autocomplete': 'email'}),
        error_messages={'invalid': 'Digite um endereço de e-mail válido.'})

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ('nome_completo', 'data_nascimento', 'username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Nome de usuário'
        self.fields['username'].help_text = 'Use letras, números e os símbolos @ . + - _'
        self.fields['username'].widget.attrs.update(autocomplete='username')
        self.fields['username'].widget.attrs.pop('autofocus', None)
        self.fields['nome_completo'].widget.attrs['autofocus'] = True
        self.fields['password1'].label = 'Senha'
        self.fields['password1'].help_text = 'Use pelo menos 8 caracteres. Evite senhas comuns, só números ou parecidas com seus dados.'
        self.fields['password2'].label = 'Confirmar senha'
        self.fields['password2'].help_text = ''
        self.fields['data_nascimento'].widget.attrs['max'] = timezone.localdate().isoformat()
        for field in self.fields.values():
            field.required = True
            field.error_messages.update(required='Preencha este campo.', max_length='Este texto ficou muito longo.')
        self.fields['username'].error_messages.update(
            unique='Este nome de usuário já está em uso.',
            invalid='Use letras, números e os símbolos @ . + - _ no nome de usuário.')

    def clean_username(self):
        value = self.cleaned_data['username']
        if (self._meta.model.objects.filter(username__iexact=value).exists()
                or self._meta.model.objects.filter(email__iexact=value).exists()):
            raise ValidationError('Este nome de usuário já está em uso.')
        return value

    def clean_email(self):
        value = self.cleaned_data['email'].lower()
        if self._meta.model.objects.filter(email__iexact=value).exists():
            raise ValidationError('Este e-mail já está cadastrado.')
        # Older users may have an email-shaped username.
        if self._meta.model.objects.filter(username__iexact=value).exists():
            raise ValidationError('Este e-mail já está cadastrado.')
        return value

    def clean_data_nascimento(self):
        value = self.cleaned_data['data_nascimento']
        if value > timezone.localdate():
            raise ValidationError('A data de nascimento não pode estar no futuro.')
        return value

    def _post_clean(self):
        # Populate inherited name fields before Django checks password similarity.
        parts = self.cleaned_data.get('nome_completo', '').split(maxsplit=1)
        self.instance.first_name = parts[0] if parts else ''
        self.instance.last_name = parts[1] if len(parts) > 1 else ''
        super()._post_clean()

    def add_error(self, field, error):
        if isinstance(error, ValidationError) and hasattr(error, 'error_list'):
            messages = {
                'password_mismatch': 'As senhas não coincidem.',
                'password_too_short': 'Use uma senha com pelo menos 8 caracteres.',
                'password_too_common': 'Esta senha é muito comum. Escolha outra.',
                'password_entirely_numeric': 'Misture letras e outros caracteres na senha.',
                'password_too_similar': 'Escolha uma senha diferente dos seus dados pessoais.',
            }
            error = ValidationError([
                ValidationError(messages[item.code], code=item.code)
                if item.code in messages else item for item in error.error_list
            ])
        super().add_error(field, error)


class EntrarForm(AuthenticationForm):
    error_messages = {
        'invalid_login': 'Usuário/e-mail ou senha incorretos.',
        'inactive': 'Usuário/e-mail ou senha incorretos.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'] = forms.CharField(label='Usuário ou e-mail', max_length=254,
            widget=forms.TextInput(attrs={'autofocus': True, 'autocomplete': 'username', 'autocapitalize': 'none'}))
        self.fields['password'].label = 'Senha'
        for field in self.fields.values():
            field.error_messages.update(required='Preencha este campo.', max_length='Este texto ficou muito longo.')
