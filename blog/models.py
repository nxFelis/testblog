from __future__ import unicode_literals

import re
import os
from datetime import datetime
from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.base import ContentFile
from tryit.celery import send_mail, add_log

HTMLField = models.TextField
if 'ckeditor' in settings.INSTALLED_APPS:
    try:
        from ckeditor.fields import RichTextField as HTMLField
    except ImportError:
        pass
elif 'tinymce' in settings.INSTALLED_APPS:
    try:
        from tinymce.models import HTMLField
    except ImportError:
        pass


def clean_slug(pk, slug):
    return '{0}-{1}'.format(pk, re.sub(r'[^0-9a-zA-Z._-]', '', slug))


def get_avatar_path(instance, filename):
    return os.path.join(settings.MEDIA_ROOT, settings.AVATAR_DIR)


def get_default_img():
    return CustomImage.objects.all()[0]


class CustomImage(models.Model):
    img = models.ImageField(verbose_name=_("Custom Image"),
                            upload_to=get_avatar_path)

    def __str__(self):
        return self.img.name


class CustomUser(models.Model):
    phone = models.CharField(verbose_name=_("Phone number"), max_length=32)
    skype = models.CharField(verbose_name=_("Skype nick"), max_length=128,
                             null=True, blank=True)
    avatar = models.ForeignKey(CustomImage, verbose_name=_("User avatar"),
                               null=True, blank=True)
    user = models.OneToOneField(User)

    def __str__(self):
        return self.user.get_username()


class BaseDateTimeModel(models.Model):
    name = models.CharField('Name', max_length=512, unique=True)
    created = models.DateTimeField('Created', auto_now_add=True)
    updated = models.DateTimeField('Updated', auto_now=True)

    class Meta:
        abstract = True


class Blog(BaseDateTimeModel):
    subscribers = models.ManyToManyField(CustomUser, blank=True, null=True,
                                         verbose_name=_('Subscribed users'))
    author = models.ForeignKey(CustomUser, verbose_name=_('Author'),
                               related_name='author')
    deleted = models.BooleanField('Is deleted', default=False)

    def save(self, *args, **kwarg):
        self.name = self.name if self.name else "%s's blog" % self.author.user\
            .get_username()
        super(Blog, self).save(*args, **kwarg)


class Category(models.Model):
    name = models.CharField(_("Category name"), max_length=512, unique=True)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class Article(BaseDateTimeModel):
    slug = models.CharField('Slug', max_length=256, blank=True, db_index=True)
    title = models.CharField('Title', max_length=256, blank=True)
    description = models.TextField('Description', max_length=1024, blank=True)
    content = models.TextField('Content', blank=True)
    published_date = models.DateTimeField('Published', blank=True, null=True)
    published = models.NullBooleanField('Is published')
    deleted = models.NullBooleanField('Is deleted')
    author_name = models.CharField('Author name', max_length=256, blank=True)
    blog = models.ForeignKey(Blog, null=True, blank=True)
    # tag = models.ManyToManyField(Tag)
    category = models.ManyToManyField(Category, null=True, blank=True)

    class Meta:
        verbose_name = 'Article'
        verbose_name_plural = 'Articles'
        ordering = ['-created']

    def __str__(self):
        return self.name

    def is_published(self):
        return self.published

    def is_read(self):
        return self.read

    def save(self, *args, **kwarg):
        pk = self.blog.pk if self.blog else 1
        self.slug = clean_slug(pk, self.slug) if self.slug \
            else clean_slug(pk, self.name)
        if not self.author_name:
            self.author_name = ' '.join([self.blog.author.user.first_name,
                                         self.blog.author.user.last_name])
        if not self.description:
            self.description = self.content[1024:]
        if self.is_published():
            self.published_date = datetime.now()
        super(Article, self).save(*args, **kwarg)
        if self.is_published():
            template = MailTemplate.objects.get(default=True)
            message = '%s: and you can find the article ' \
                      'here http://127.0.0.1%s' % (template.message,
                                                   self.get_absolute_url())
            send_mail(template.subject, message, template.from_addr,
                      self.blog.subscribers.all())

    def get_absolute_url(self):
        return '/article/%s' % self.slug


class ArticleComment(BaseDateTimeModel):
    article = models.ForeignKey(Article)
    content = models.TextField('Content', blank=True)
    author = models.ForeignKey(CustomUser)
    ranking = models.IntegerField(verbose_name=_("Comment's likes counting"))

    def __str__(self):
        return "%s's comment for %s" % (self.author.user.get_username(),
                                        self.article.title)


class ArticleList(models.Model):
    read = models.BooleanField('Is read', default=False)
    notified = models.NullBooleanField('Is notified', blank=True, null=True)
    article = models.ForeignKey(Article, verbose_name='Article')
    user = models.ForeignKey(CustomUser, verbose_name='Subscriber')


class MailTemplate(BaseDateTimeModel):
    subject = models.CharField('Subject', max_length=128)
    from_addr = models.EmailField('Sender email address', blank=True)
    message = HTMLField('Body', blank=True)
    slug = models.SlugField('Slug', unique=True,
                            help_text='Unique slug for internal usages.')
    num_of_retries = models.PositiveIntegerField('Number of retries',
                                                 default=0)
    interval = models.PositiveIntegerField('Send interval', null=True,
                                           blank=True,
                                           help_text='Specify sending interval'
                                                     ' in the seconds.')
    default = models.BooleanField('Is default template', default=False)

    class Meta:
        verbose_name = 'Mail template'
        verbose_name_plural = 'Mail templates'
        ordering = ['-created']

    def __str__(self):
        return self.name

    def get_template(self, slug=None):
        if self.objects.filter(slug=slug).exists():
            template = self.objects.filter(slug=slug)
        else:
            template = self.objects.filter(default=True)[0]
        return template

    def is_default(self):
        return self.default


class Mail(BaseDateTimeModel):
    sended = models.NullBooleanField('Is sent')
    status = models.SmallIntegerField('Sending status', default=1)
    to_addr = models.EmailField('Subscriber email address')
    sending_date = models.DateTimeField('Date of sending', null=True,
                                        blank=True)
