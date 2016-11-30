from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.forms.formsets import formset_factory
from blog.models import Article, Blog, ArticleList, CustomUser
from blog.forms import ArticleCreationForm, BlogSubscribeForm, \
    CustomUserCreateForm, CustomUserUpdateForm, ArticleUpdatingForm
from django.views.generic.edit import CreateView, UpdateView
from django.core.urlresolvers import reverse_lazy

HELLO = "Hello, guest. You're in the blog now, welcome."


def signout(request):
    form = AuthenticationForm()
    context = {'title': HELLO, 'form': form}
    logout(request)
    return render(request, 'login.html', context)


def hello(request):
    form = AuthenticationForm()
    title = HELLO
    if request.user.is_authenticated():
        title = "Hi, dude. You're in the blog, say hi."
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            get_articles(request)
    context = {'title': title, 'form': form}
    return render(request, 'base.html', context)


def get_articles(request):
    context = {'objects': Article.objects.filter(published=True),
               'title': "Latest published articles"}
    return render(request, 'articles.html', context)


def get_user_articles(request):
    user = request.user
    blog = Blog.objects.filter(author__pk=user.pk)
    context = {'objects': Article.objects.filter(blog=blog),
               'title': "My articles"}
    return render(request, 'articles_user.html', context)


def get_article(request, slug):
    obj = Article.objects.get(slug=slug)
    user = CustomUser.objects.get(user=request.user)
    if ArticleList.objects.filter(article=obj, user=user, read=False).exists():
        article = ArticleList.objects.filter(article=obj, user=user,
                                             read=False)[0]
        article.read = True
        article.save(update_fields=['read'])
    context = {'obj': obj}
    return render(request, 'article.html', context)


def add_article(request):
    user = request.user
    if user.is_authenticated and request.method == 'POST':
        form = ArticleCreationForm(request.POST)
        if form.is_valid():
            article = form.save(commit=False)
            custom_user = CustomUser.objects.get(user=user)
            blog = Blog.objects.get_or_create(author=custom_user)[0]
            article.blog = blog
            article.save()
            subscribers = blog.subscribers.all()
            articles2read = []
            for sub in subscribers:
                if not ArticleList.objects.filter(user=sub,
                                                  article=article).exists():
                    articles2read.append({'article': article, 'user': sub})
            ArticleList.objects.bulk_create([ArticleList(**kw) for kw
                                             in articles2read])
            return get_article(request, slug=article.slug)
    else:
        form = ArticleCreationForm()
    context = {'form': form, 'action': 'article-add',
               'title': 'Add a new article to your awesome blog'}
    return render(request, 'article_creation.html', context)


def update_article(request, pk):
    obj = Article.objects.get(pk=pk)
    if request.method == 'POST':
        form = ArticleUpdatingForm(request.POST, instance=obj)
        if form.is_valid():
            article = form.save()
            return get_article(request, slug=article.slug)
    else:
        form = ArticleUpdatingForm(instance=obj)
    context = {'form': form, 'title': 'Edit the article',
               'action': 'article-edit', 'obj': obj}
    return render(request, 'article_creation.html', context)


def get_subscribed_articles(request):
    user = CustomUser.objects.get(user=request.user)
    objects = ArticleList.objects.filter(user=user.pk)\
        .order_by('article__published_date')
    if objects.count() < 1:
        blogs = [blog.pk for blog in Blog.objects.filter(subscribers=user)]
        articles = Article.objects.filter(published=True, blog__in=blogs)\
            .order_by('published_date')
        new_objects = [{'article': article, 'user': user} for article
                       in articles]
        ArticleList.objects.bulk_create([ArticleList(**kw) for kw
                                         in new_objects])
        if ArticleList.objects.filter(user=user.pk).exists():
            objects = ArticleList.objects.filter(user=user.pk)\
                .order_by('article__published_date')
    context = {'objects': objects}
    return render(request, 'articles.html', context)


def control_subscription(request):
    context = {'title': "Subscription control"}
    user = CustomUser.objects.get(user=request.user)
    blogs = Blog.objects.filter(deleted=False)
    objects = []
    for blog in blogs:
        subscribers = blog.subscribers.all()
        subscribed = True if user in subscribers else False
        objects.append({'blog_name': blog.name, 'subscribe': subscribed,
                        'author_name': blog.author.user.get_username()})
    BlogFormset = formset_factory(BlogSubscribeForm, extra=0)
    if request.method == 'POST':
        articles2read = []
        formset = BlogFormset(request.POST, request.FILES)
        if formset.is_valid():
            for data in formset.cleaned_data:
                new_blog = blogs.filter(name=data.get('blog_name'))[0]
                if data.get('subscribe'):
                    new_blog.subscribers.add(user)
                    articles = new_blog.article_set.all()
                    for article in articles:
                        if not ArticleList.objects\
                                .filter(user=user, article=article).exists():
                            articles2read.append({'article': article,
                                                  'user': user})
                else:
                    old_subscribers = new_blog.subscribers.all()
                    if user in old_subscribers:
                        new_blog.subscribers.remove(user)
                        for article in new_blog.article_set.all():
                            ArticleList.objects\
                                .filter(user=user, article=article).delete()
            if articles2read:
                ArticleList.objects.bulk_create([ArticleList(**kw)
                                                 for kw in articles2read])
            context.update({'success': "You subscriptions were successfully "
                                       "changed"})
    else:
        formset = BlogFormset(initial=objects)
    context.update({'formset': formset})
    return render(request, 'blogs.html', context)


class CustomUserCreateView(CreateView):
    allowed_for_superuser = True
    model = CustomUser
    form_class = CustomUserCreateForm
    success_url = reverse_lazy('index')


class CustomUserUpdateView(UpdateView):
    allowed_for_superuser = True
    model = CustomUser
    form_class = CustomUserUpdateForm
    success_url = reverse_lazy('index')

