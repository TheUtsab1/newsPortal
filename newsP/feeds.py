from django.contrib.syndication.views import Feed
from .models import Post

class LatestPostsFeed(Feed):
    title = "Latest Posts"
    link = "/feed/"
    description = "Latest posts from XBDC"

    def items(self):
        return Post.objects.all().order_by('-date_created')[:10]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.content[:200]