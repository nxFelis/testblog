from django.conf.urls import url

from . import views, feed

urlpatterns = [
    url(r'^$', views.hello, name='index'),
    url(r'^article/(?P<slug>[0-9a-zA-Z-_.]*)/$', views.get_article,
        name='article-get'),
    url(r'^myarticles/$', views.get_user_articles, name='articles-get-user'),
    url(r'^articles/$', views.get_subscribed_articles, name='articles-get'),
    url(r'^add/$', views.add_article, name='article-add'),
    url(r'^edit/(?P<pk>\d+)/$', views.update_article, name='article-edit'),
    url(r'^feed/$', feed.LatestArticles(), name="feed"),
    url(r'^(?P<pk>\d+)/info/$', views.CustomUserUpdateView.as_view(),
        name="custom_info"),
    url(r'^out/$', views.signout, name="logout"),
    url(r'^subscribe/$', views.control_subscription, name='blog-subscribe'),


]
