Getting Started
===============

This page gives an introduction to **django-taxii-services** and how to use it.  Please note
that this page is being actively worked on and feedback is welcome (taxii@mitre.org).

Note that the GitHub repository is named :code:`django-taxii-services`, but
once installed, the library is imported using the :code:`import taxii_services`
statement.

Installation
------------
There are two options for installation:  

#. :code:`pip install taxii_services --upgrade`  
#. Download the latest zip from https://pypi.python.org/pypi/taxii-services

Local YETI Deployment
---------------------

These instructions tell you how to get YETI / django-taxii-services
up and running on your local machine.

1. Install django-taxii-services (Per the installation section)
2. Get YETI using one of two methods:

 a. Clone the YETI repostory (:code:`git clone https://github.com/TAXIIProject/yeti.git`) \
    (Requires git)
 b. Download and unpack the latest release (2.0a at the time of this writing): \
    https://github.com/TAXIIProject/yeti/releases

3. Open a command prompt and navigate to the folder you extracted YETI into
#. Set up the database: :code:`python manage.py syncdb` 

 a. This sets up the database, and only needs to be run once
 b. Say "yes" to "Create a superuser?" - Supply your own credentials

4. Run the server: :code:`python manage.py runserver --insecure 0.0.0.0:8080`

Now you have YETI running. You can play with it by:

* Pointing your browser at :code:`http://localhost:8080/`

 * Or go to :code:`http://localhost:8080/admin/` to log into the admin interface

* Run any of the scripts in yeti/scripts. e.g., 

 * :code:`scripts\yeti_collection_information_client.bat`
 * :code:`scripts\yeti_discovery_information_client.bat`
 * If you have a proxy, you'll have to specify it by appending \
   :code:`--proxy http://proxy.example.com:80` to the script \
   e.g., :code:`scripts\yeti_discovery_information_client.bat --proxy http://proxy.example.com:80`

* Run any libtaxii script from a command prompt:

 * :code:`discovery_client --host localhost --port 8080 [--proxy <proxy_address>]`
