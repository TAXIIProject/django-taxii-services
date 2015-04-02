import os

import taxii_services

project = u'django-taxii-services'
copyright = u'2014, The MITRE Corporation'
version = taxii_services.__version__
release = version

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode']

templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'

rst_prolog = """
**Version**: {}
""".format(release)

exclude_patterns = ['_build']

pygments_style = 'sphinx'

on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
if not on_rtd:  # only import and set the theme if we're building docs locally
    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
else:
    html_theme = 'default'

latex_elements = {}
latex_documents = [
  ('index', 'django-taxii-services.tex', u'django-taxii-services Documentation',
   u'Mark Davidson', 'manual'),
]
