# Copyright (c) 2014, The MITRE Corporation. All rights reserved.
# For license information, see the LICENSE.txt file

from __future__ import absolute_import

from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic import TemplateView

from taxii_services.views import service_router

admin.autodiscover()

urlpatterns = [
    url(r'([\w-]+)/$', service_router, name='service_router'),
]
