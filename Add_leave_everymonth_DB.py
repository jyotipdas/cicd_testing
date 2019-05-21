from main import Users, db, logging
from datetime import date


def addLeave():
    if date.today().day == 3:
        for user in Users.query.all():
            user.balance += 2

        db.session.commit()
        logging.info('2 leaved added to everyone automatically')


addLeave()