import re
from collections import OrderedDict
from django.forms import Form, ModelForm, BaseModelFormSet, BooleanField, CharField
from blog.models import Article, Blog, ArticleList, CustomUser
from django.db import transaction
from django.forms import BooleanField, CharField, ChoiceField, RegexField, \
    FileField, ModelForm
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User


class ArticleCreationForm(ModelForm):
    class Meta:
        model = Article
        fields = ['name', 'title', 'description', 'content', 'author_name',
                  'published']


class ArticleUpdatingForm(ModelForm):
    class Meta:
        model = Article
        fields = ['name', 'title', 'description', 'content']


class BlogSubscribeForm(Form):
    blog_name = CharField(max_length=512)
    author_name = CharField(max_length=128)
    subscribe = BooleanField(required=False)


class ArticleListForm(ModelForm):
    class Meta:
        model = ArticleList
        fields = ['read', 'article']


class BlogForm(ModelForm):
    class Meta:
        model = Blog
        fields = ['author']


class CustomUserFormBase(ModelForm):
    username = RegexField(re.compile('^[\w.@+-]{1,30}$'),
                          label=_('username').capitalize())
    last_name = RegexField(re.compile(r"^[\w '-]+$", re.U),
                           label=_('last name').capitalize(),
                           required=True, max_length=30)
    first_name = RegexField(re.compile(r"^[\w '-]+$", re.U),
                            label=_('first name').capitalize(),
                            required=True, max_length=30)

    def clean_username(self):
        username = self.cleaned_data['username']
        user_pk = self.instance.user.pk if self.instance.pk else None
        if User.objects.filter(username=username).exclude(pk=user_pk).exists():
            raise ValidationError(_('This username is already used.'))
        return username

    def clean(self):
        cleaned_data = super(CustomUserFormBase, self).clean()
        custom_user = self.instance or None
        striping_fields = ('first_name', 'last_name')
        for striping_field in striping_fields:
            cleaned_data[striping_field] = (cleaned_data.get(striping_field,
                                                             '').strip())
        kw_to_exists = {'user__first_name': cleaned_data.get('first_name'),
                        'user__last_name': cleaned_data.get('last_name')}
        if not isinstance(self, CustomUserUpdateForm):
            existed_user = CustomUser.objects.filter(**kw_to_exists).exists()
            if existed_user and CustomUser.objects.filter(**kw_to_exists)[0]\
                    .pk:
                raise ValidationError(_('Full name must be unique'))
        else:
            if custom_user:
                existed_user = CustomUser.objects.filter(**kw_to_exists)\
                                              .exclude(pk=custom_user.pk)
                if existed_user:
                    raise ValidationError(_('Full name must be unique'))
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super(CustomUserFormBase, self).__init__(*args, **kwargs)
        first_field_names = ['username', 'last_name', 'first_name']
        addition_fields = [field_name for field_name in self.fields
                           if field_name not in first_field_names]
        field_names = first_field_names + addition_fields
        fields = OrderedDict((field_name, self.fields[field_name])
                             for field_name in field_names)
        self.fields = fields
        # adding an username initial value
        if self.instance and self.instance.pk:
            custom_user = self.instance
            self.fields['username'].initial = custom_user.user.username
            self.fields['last_name'].initial = custom_user.user.last_name
            self.fields['first_name'].initial = custom_user.user.first_name

    def save(self, commit=True):
        with transaction.atomic():
            custom_user = ModelForm.save(self, commit)
            custom_user.user.username = self.cleaned_data['username']
            custom_user.user.last_name = self.cleaned_data['last_name']
            custom_user.user.first_name = self.cleaned_data['first_name']
            if commit:
                custom_user.user.save()
            return custom_user


class CustomUserCreateForm(CustomUserFormBase, UserCreationForm):

    def __init__(self, *args, **kwargs):
        super(CustomUserCreateForm, self).__init__(*args, **kwargs)

    def clean_first_name(self):
        first_name = self.cleaned_data['first_name'].strip()
        if not first_name:
            raise ValidationError(_('Invalid value'), code='invalid')
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data['last_name'].strip()
        if not last_name:
            raise ValidationError(_('Invalid value'), code='invalid')
        return last_name

    def save(self, commit=True):
        user_form = UserCreationForm(data=self.data)
        user_form.is_valid()
        user = user_form.save(commit)
        self.instance.user = user
        return CustomUserFormBase.save(self, commit)

    class Meta:
        model = CustomUser
        exclude = ('user',)


class CustomUserUpdateForm(CustomUserFormBase, UserChangeForm):

    avatar = FileField(label=_('avatar').capitalize(), required=False)

    class Meta:
        model = CustomUser
        exclude = ('user', 'avatar')

    def __init__(self, *args, **kwargs):
        super(CustomUserUpdateForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['readonly'] = True
        del self.fields['password']

    def clean_password(self):
        if 'password' in self.initial:
            return super(CustomUserUpdateForm, self).clean_password()
        return None

    def clean_first_name(self):
        first_name = self.cleaned_data['first_name'].strip()
        if not first_name:
            raise ValidationError(_('Invalid value'), code='invalid')
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data['last_name'].strip()
        if not last_name:
            raise ValidationError(_('Invalid value'), code='invalid')
        return last_name

    def save(self, commit=True):
        custom_user = super(CustomUserUpdateForm, self).save(commit)
        custom_user.avatar = self.cleaned_data['avatar']
        if commit:
            custom_user.user.save()
            custom_user.save()
        return custom_user
