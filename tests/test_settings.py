# Copyright (C) 2015 - The MITRE Corporation
# For license information, see the LICENSE.txt file

import os

DEBUG = True
USE_TZ = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(os.path.dirname(__file__), 'test.db'),
    }
}

INSTALLED_APPS = [
    'taxii_services',
]

MIDDLEWARE_CLASSES = (
    'taxii_services.middleware.StatusMessageExceptionMiddleware',
)

ROOT_URLCONF = 'taxii_services.urls'


SECRET_KEY = "kjebl23k4b64.35mg.sd,mfnt.,3m4t1,m3nbr,1235"
