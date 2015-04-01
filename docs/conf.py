import taxii_services

project = u'django-taxii-services'
copyright = u'2014, The MITRE Corporation'
version = taxii_services.__version__
release = version

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode']

templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'

exclude_patterns = ['_build']

pygments_style = 'sphinx'

html_theme = 'default'

latex_elements = {}
latex_documents = [
  ('index', 'django-taxii-services.tex', u'django-taxii-services Documentation',
   u'Mark Davidson', 'manual'),
]
