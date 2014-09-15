Release Notes
=============

0.1.1
-----

There was a critical bug in 0.1 that was somehow missed. (#13). 
This bug fix release is simply to fix that bug.

0.1
---

0.1 is the first version of django-taxii-services. Please note that since the
version number is below 1.0, the API is unstable and may change in a future minor 
release.

The intent of this release is to gauge interest for django-taxii-services
and determine whether it makes sense to keep working on future versions.

The major items accomplished in this release are: 
 
* Established core concepts, paradigms, and structures of the library
* Set the technical direction of MessageHandler extension points
* Baseline API documentation: http://taxii-services.readthedocs.org/en/latest/index.html
* YETI 2.0a (An experimental release of YETI) now uses django-taxii-services.

There are some notable/major TBDs in this release of django-taxii-services:

* Non-API documentation (We tried to get API documentation at least usable)
* Logging (https://github.com/TAXIIProject/django-taxii-services/issues/5)
* Testing (https://github.com/TAXIIProject/django-taxii-services/issues/3)
* QueryHandlers need to be fleshed out more (https://github.com/TAXIIProject/django-taxii-services/issues/6)
* Many portions of the library are experimental and untested