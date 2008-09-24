from django.template import RequestContext
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.sites.models import Site
from django.contrib.auth.models import User

from omb.forms import RemoteSubscribeForm
from omb import oauthUtils, oauthConsumer, OAUTH_REQUEST, OAUTH_ACCESS, OMB_POST_NOTICE, OMB_UPDATE_PROFILE, OAUTH_AUTHORIZE
from omb.models import RemoteProfile

from oauth.oauth import OAuthRequest, OAuthServer, OAuthSignatureMethod_HMAC_SHA1
from oauth_provider.stores import DataStore

#from pydentica.utils import omb
#from pydentica.models import RemoteProfile, Subscription, Notice

def follow(request):
    if request.method == "GET":
        form = RemoteSubscribeForm(initial={'username': request.GET.get('username')})
    else:
        current_site = Site.objects.get_current()
        form = RemoteSubscribeForm(request.POST)
        if form.is_valid():
            user = User.objects.get(username=form.cleaned_data['username'])
            omb = oauthUtils.getServices(user, form.cleaned_data['profile_url'])
            token = oauthConsumer.requestToken(omb)
            print token
            oauthRequest = oauthConsumer.requestAuthorization(token, omb[OAUTH_AUTHORIZE].uris[0].uri, omb[OAUTH_REQUEST].localid.text, user)
            print(repr(token))
            # store a bunch of stuff in the session varioable oauth_authorization_request
            omb_session = {
                'listenee': user.username,
                'listener': omb[OAUTH_REQUEST].localid.text,
                'token': token.key,
                'secret': token.secret,
                'access_token_url': omb[OAUTH_ACCESS].uris[0].uri,
                'post_notice_url': omb[OMB_POST_NOTICE].uris[0].uri,
                'update_profile_url': omb[OMB_UPDATE_PROFILE].uris[0].uri,
            }
            request.session['oauth_authorization_request'] = omb_session
            print(oauthRequest.to_url())
            #return HttpResponseRedirect(oauthRequest.to_url())            
    return render_to_response('omb/remote_subscribe.html', {'form': form})

def finish_follow(request):
    omb_session = request.session['oauth_authorization_request']
    oauth_request = OAuthRequest.from_request(request.method, request.build_absolute_uri(), headers=request.META)
    accessToken = oauthConsumer.requestAccessToken(omb_session, oauth_request)
    try:
        remote_profile = RemoteProfile.objects.get(uri=omb_session["listener"])
    except:
        remote_profile = RemoteProfile()
        remote_profile.uri = omb_session["listener"]
        remote_profile.url = oauth_request['omb_listener_profile']
        remote_profile.postnoticeurl = omb_session["post_notice_url"]
        remote_profile.updateprofileurl = omb_session["update_profile_url"]
        remote_profile.save()
    

def postnotice(request):
    current_site = Site.objects.get_current()
    signature_methods = {
        OAuthSignatureMethod_HMAC_SHA1().get_name(): OAuthSignatureMethod_HMAC_SHA1
    }
    oauth_req = OAuthRequest.from_request(request.method, request.build_absolute_uri(), headers=request.META)
    if not oauth_req:
        return HttpResponse("Not a OAuthRequest")
    else:
        oauth_server = OAuthServer(data_store=DataStore(oauth_req), signature_methods=signature_methods)
        oauth_server.verify_request(oauth_request)
        # TOOD Refactor this into something like omb.post_notice
        version = oauth_req.get_parameter('omb_version')
        if version != omb.OMB_VERSION_01:
            return HttpResponse("Unsupported OMB version")
        listenee = oauth_req.get_parameter('omb_listenee')
        remote_profile = RemoteProfile.objects.get(uri=listenee)
        if not remote_profile:
            return HttpResposne("Profile unknown")
        subscription = Subscription.objects.get(token=oauth_req.get_parameter('token'))
        if not subscription:
            return HttpResponse("No such subscription")
        content = oauth_req.get_parameter('omb_notice_content')
        if not content or len(content) > 140:
            return HttpResponse("Invalid notice content")
        notice_uri = oauth_req.get_parameter('omb_notice')
        # TODO Validate this uri exists
            # Invalid notice uri
        notice_url = oauth_uri.get_parameter("omb_notice_url")
        # TODO Validate this url 
            # Invalid notice url
        try:
            Notice.objects.get(uri=notice_uri)
        except: # TODO catch the real exception
            notice = Notice.objects.create(profile=remote_profile, content=content, )
            # TODO this is bad, do this better
            # TODO add the notice.source = "omb"
            # TODO add notice.is_local=False
            notice.uri = "%s/notice/%s" % (current_site.domain, notice.id)
            notice.save()
            # Broadcast to remote subscribers ===================================
            subscriptions = Subscription.objects.filter(subscribed=notice.profile)
            for sub in subcriptions:
                rp = RemoteProfile.objects.get(id=sub.subscriber.id)
                omb.post_notice_keys(notice, rp.postnoticeurl, sub.token, sub.secret)
                
            
        return HttpResponse("omb_version=%s" % omb.OMB_VERSION_01)

def updateprofile(request):
    return HttpResponse("update profile")