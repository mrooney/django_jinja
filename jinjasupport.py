import jinja2
import os
import settings
from django.template.context import Context
from django.core.urlresolvers import get_callable, reverse, NoReverseMatch
from django.utils import translation
from django.utils.thread_support import currentThread
from django.http import HttpResponse
from jinja2 import PackageLoader, Environment, ChoiceLoader, FileSystemLoader
from exceptions import AttributeError

global env

### don't forget to install jinja2 and add it to your PYTHON_PATH
### http://jinja.pocoo.org/2/documentation/


##########################   HANDLER FOR GENERIC VIEWS   ##########################   

class DjangoTemplate(jinja2.Template):
  """
  a class for flatting generic views dictionary and 
  passing it to jinja template renderer
  """

  def render(self,*args,**kwargs):
    """a method for flattening passed generic view dictionary"""
    if args and isinstance(args[0],Context):
      for dictionary in reversed(args[0].dicts):
        kwargs.update(dictionary)
      args=[]
    return super(DjangoTemplate,self).render(*args,**kwargs)
    
class DjangoEnvironment(jinja2.Environment):
  """
  a class for proxying jinja2 support to django generic views,
  just add to specific urls.py file below line:
  
    from <MODULE_NAME>.jinjasupport import jenv
  
  and in your generic view dictionary:
    
    'template_loader':jenv,
  """
  template_class=DjangoTemplate
    
jenv=DjangoEnvironment(loader=FileSystemLoader(settings.TEMPLATE_DIRS))

####################   HANDLER FOR HAND MADE FILTERS AND TAGS   #######################

# template loaders setup

loader_array = []
for pth in getattr(settings, 'TEMPLATE_DIRS', ()):
    loader_array.append(FileSystemLoader(pth))

for app in settings.INSTALLED_APPS:
    loader_array.append(PackageLoader(app))

# environment setup

try:
  default_mimetype = getattr(settings, 'DEFAULT_CONTENT_TYPE')
except AttributeError:
  default_mimetype="text/html"

try:
  global_exts = getattr(settings, 'JINJA_EXTS', ())
except AttributeError:
  global_exts=""

env = Environment(extensions=global_exts, loader=ChoiceLoader(loader_array))

# adding i18n support
if 'jinja2.ext.i18n' in global_exts:
    env.install_gettext_translations(translation)

# add user Globals, Filters, Tests
# defined in JINJA_GLOBALS, JINJA_FILTERS, JINJA_FILTERS tuples in your settings.py

global_imports = getattr(settings, 'JINJA_GLOBALS', ())
for imp in global_imports:
    method = get_callable(imp)
    method_name = getattr(method,'jinja_name',None)
    if not method_name == None:
        env.globals[method_name] = method
    else:
        env.globals[method.__name__] = method

global_filters = getattr(settings, 'JINJA_FILTERS', ())
for imp in global_filters:
    method = get_callable(imp)
    method_name = getattr(method,'jinja_name',None)
    if not method_name == None:
        env.filters[method_name] = method
    else:
        env.filters[method.__name__] = method

global_tests = getattr(settings, 'JINJA_TESTS', ())
for imp in global_tests:
    method = get_callable(imp)
    method_name = getattr(method,'jinja_name',None)
    if not method_name == None:
        env.tests[method_name] = method
    else:
        env.tests[method.__name__] = method

##########################   HANDLER FOR HAND MADE VIEWS  #############################

def render_to_string(filename, context={}):
    """
    helper method for jinja2 powered render_to_response method
    """
    template = env.get_template(filename)
    rendered = template.render(**context)
    return rendered

def render_to_response(filename, context={},mimetype=default_mimetype, request = None):
    """
    use this function instead builtin django render_to_response
    """
    if request:
        context['request'] = request
    rendered = render_to_string(filename, context)
    return HttpResponse(rendered,mimetype=mimetype)
    
##########################   TEMPLATE HELPERS   ##########################

# reverse url pattern matching
def url_noencode(view_name, *args, **kwargs):
    try:
        return reverse(view_name, args=args, kwargs=kwargs)
    except NoReverseMatch:
        return "/"
    
def url(view_name, *args, **kwargs):
    """
    same as builtin django url tag, but used as function
    {{ url_for("view_name",args,kwargs) }}
    """
    import urllib
    escaped_args = tuple(urllib.quote(arg,"") if isinstance(arg,basestring) else arg for arg in args)
    escaped_kwargs = dict((k, urllib.quote(v,"") if isinstance(arg,basestring) else arg) for k,v in kwargs)
    return url_noencode(view_name, *escaped_args, **kwargs)
env.globals["url_for"] = url

def get_lang():
    """
    displays current language code 
    """
    return translation.get_language()
env.globals["get_language_code"] = get_lang

def timesince(date):
    """
    converted django timesince tag 
    """
    from django.utils.timesince import timesince
    return timesince(date)
env.globals["timesince"] = timesince

def timeuntil(date):
    """
    converted django timeuntil tag 
    """
    from django.utils.timesince import timesince
    from datetime import datetime
    return timesince(datetime.now(),datetime(date.year, date.month, date.day))
env.globals["timeuntil"] = timeuntil

def truncate(text,arg):
    """
    tag that truncates text call it with an str argument like '20c' or '5w',
    where the number provides the count 
    and c stands for characters and w stands for words 
    """
    import re
    from django.utils.encoding import force_unicode
    text = force_unicode(text)
    matches = re.match('(\d+)([cw]{1})',arg)
    if not matches:
        return text
    count = int(matches.group(1))
    type = matches.group(2)
    if type == 'c':
        if count > len(text):
            return text
        else:
            return text[:count] + '&hellip;'
    elif type == 'w':
        arr = text.strip().split()
        if count > len(arr):
            return ' '.join(arr)
        else:
            return ' '.join(arr[:count]) + '&hellip;'
env.filters["truncate"] = truncate



