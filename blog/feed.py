from django.contrib.syndication.views import Feed
from blog.models import Article


class LatestArticles(Feed):
    title = "Blog, my little pur-pur blog"
    link = "/feed/"
    description = 'Testov Test Testovich is written here.' \
                  ' Invisible fonts? No, have never heard.'

    def items(self):
        return Article.objects.filter(published=True)[:8]

