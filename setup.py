from distutils.core import setup

setup(name='pyZOCP',
      version='0.1',
      description='Python ZOCP implementation',
      author='Arnaud Loonstra',
      author_email='arnaud@sphaero.org',
      url='http://www.github.com/z25/pyZOCP/',
      packages=['ZOCP'],
      package_dir = {'ZOCP': 'src'},
      include_package_data=True,
      requires=['pyre']
     )
