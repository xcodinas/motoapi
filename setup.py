import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="Motoapi",
    version="0.1.0",
    author="Xavier Codinas",
    author_email="xavier19966@gmail.com",
    description=("Soocial City"),
    license="BSD",
    packages=['motoapi'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'pyparsing==2.4.7',
        'flask==1.1.2',
        'SQLAlchemy<1.4',
        'Flask-sqlalchemy',
        'Flask-migrate',
        'Flask-script',
        'Flask-admin',
        'Flask-Babelex',
        'Flask-CORS',
        'Flask-mail',
        'Flask-restful',
        'Wtforms',
        'psycopg2',
        'setuptools',
        'python-magic',
        'lorem',
        'passlib',
        'itsdangerous==2.0',
        'jinja2==3.0.3',
        'Werkzeug==2.0.3',
        'Flask-jwt-extended==3.25.0',
        'jwt',
    ],
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
    ],
    test_suite='tests',
)
