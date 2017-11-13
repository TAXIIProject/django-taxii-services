# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from django.conf.urls import include, patterns, url
from django.contrib import admin
from django.views.generic import TemplateView

admin.autodiscover()

urlpatterns = patterns('',
                       url(r'([\w-]+)/$', 'taxii_services.views.service_router'),
                       )
