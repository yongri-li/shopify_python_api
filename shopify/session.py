import pyactiveresource.formats
import time
import urllib
try:
    from hashlib import md5
except ImportError:
    from md5 import md5
import re


class Session(object):
    api_key = None
    secret = None
    protocol = 'https'

    @classmethod
    def setup(cls, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(cls, k, v)

    @classmethod
    def temp(cls, domain, token, block):
        session = Session(domain, token)
        import shopify
        original_domain = shopify.ShopifyResource.get_site()
        original_token = shopify.ShopifyResource.headers['X-Shopify-Access-Token']
        original_session = shopify.Session(original_domain, original_token)

        try:
            shopify.ShopifyResource.activate_session(session)
            return eval(block)
        except Exception, e:
            raise e
        finally:
            shopify.ShopifyResource.activate_session(original_session) 

    def __init__(self, shop_url, token=None, params=None):
        self.url = self.__prepare_url(shop_url)
        self.token = token
        self.legacy = False

        if params is None:
            return

        if not self.validate_params(params):
            raise 'Invalid Signature: Possibly malicious login'

        self.legacy = True
        self.token = self.__computed_password(params['t'])

        return

    def __computed_password(self, t):
        return md5(self.secret + t).hexdigest()

    @classmethod
    def create_permission_url(cls, shop_url, scope, redirect_uri=None):
        shop_url = cls.__prepare_url(shop_url)
        query_params = dict(client_id=cls.api_key, scope=",".join(scope))
        if redirect_uri: query_params['redirect_uri'] = redirect_uri
        return "%s://%s/admin/oauth/authorize?%s" % (cls.protocol, shop_url, urllib.urlencode(query_params))

    @classmethod
    def create_auth_url(cls, shop_url, code):
        shop_url = cls.__prepare_url(shop_url)
        query_params = dict(client_id=cls.api_key, client_secret=cls.secret, code=code)
        return "%s://%s/admin/oauth/access_token?%s" % (cls.protocol, shop_url, urllib.urlencode(query_params))

    @property
    def site(self):
        return "%s://%s/admin" % (self.protocol, self.url)

    @property
    def valid(self):
        return self.url is not None and self.token is not None 

    @staticmethod
    def __prepare_url(url):
        if url.strip() == "":
            return None
        url = re.sub("https?://", "", url)
        url = re.sub("/.*", "", url)
        if url.find(".") == -1:
            url += ".myshopify.com"
        return url

    @classmethod
    def validate_params(cls, params):
        # Avoid replay attacks by making sure the request
        # isn't more than a day old.
        one_day = 24 * 60 * 60
        if int(params['timestamp']) < time.time() - one_day:
            return False

        return cls.validate_signature(params)

    @classmethod
    def validate_signature(cls, params):
        if "signature" not in params:
            return False

        sorted_params = ""
        signature = params['signature']

        for k in sorted(params.keys()):
            if k != "signature":
                sorted_params += k + "=" + params[k]

        return md5(cls.secret + sorted_params).hexdigest() == signature
