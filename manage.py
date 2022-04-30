import psycopg2
import random
import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy import exists, select, func, desc

from flask_script import Manager
import lorem

from motoapi import db, motoapi
from motoapi.models import Brand, Variation

manager = Manager(motoapi)


@manager.command
def init_db():
    db.create_all()


@manager.command
def import_data():
    con = psycopg2.connect("dbname=motos user=motos password=motos")
    cur = con.cursor()
    cur.execute("""
                select name from brands
                """)
    for brand in cur.fetchall():
        if not Brand.query.filter_by(name=brand[0]).first():
            db.session.add(Brand(name=brand[0]))
    db.session.commit()
    cur.execute("""
                select v.*, b.name
                from versions v
                inner join brands b on (b.id = v.brand_id);""")

    for moto in cur.fetchall():
        brand = Brand.query.filter_by(name=moto[6]).first()
        if not brand or Variation.query.filter_by(
                name=moto[1].split(' (')[0]).count():
            continue
        try:
            db.session.add(Variation(
                name=moto[1].split(' (')[0].strip(),
                brand=brand,
                model_year=moto[1].split(' (')[1][0:4],
                year=moto[3],
                fuel=moto[4],
                price=moto[5],
            ))
        except Exception as e:
            continue
    db.session.commit()


@manager.command
def update_data(validated=False):
    for moto in Variation.query.filter_by(fetch_date=None).all():
        moto.update_data()
        db.session.commit()
    if validated:
        for moto in Variation.query.filter(Variation.fetch_date != None).all():
            moto.update_data()


if __name__ == '__main__':
    manager.run()
