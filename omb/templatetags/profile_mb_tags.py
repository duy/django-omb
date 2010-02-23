from django import template
register = template.Library()
from django.contrib.auth.models import User
from omb.models import RemoteProfile

# this templatetag for microblogging/followers.html template, to get the profile url of OMB external user, but as you can not list different type of objects at template, this have not sense.
def profile_url(user):
    if not isinstance(user, User):
        try:
            user = User.objects.get(username=user)
            alt = unicode(user)
            url = user.get_absolute_url()
        except User.DoesNotExist:
            print "no existe el usuario"
            if isinstance(user, RemoteProfile):
                url = user.url
                alt = unicode(user.username)
    else:
        alt = unicode(user)
        url = user.get_absolute_url()
    return """<a href="%s">%s</a>""" % (url, alt)
register.simple_tag(profile_url)
