# MOTOAPI

## Install requiremnts:
 ```sh
$ python setup.py develop
```

## Instalation
 ```sh
$ flask db init
$ flask db migrate
$ flask db upgrade
```
## Creating an user
```sh
$ python manage.py create_user
```

The default admin user will be:
> admin@admin.com | Admin | admin

If you want a custom email / name / password you should use the function parameters:

```sh
$ python manage.py create_user --name admin --email admin@admin.com --pasword admin
```

In order to connect to the application run the flask development server
```sh
$ FLASK_APP=motoapi flask run
```

## Translations

Generate the translation strings base file

```sh
$ pybabel extract -F babel.cfg -o messages.pot .
$ pybabel update -i messages.pot -d motoapi/translations
```

Init a new translation language

```sh
$ pybabel init -i messages.pot -d motoapi/translations -l es
```

Update the language with new strings in base file

```sh
$ pybabel update -i messages.pot -d motoapi/translations
```
Compile the translation files

```sh
$ pybabel compile -d motoapi/translations
```
