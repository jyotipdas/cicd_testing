#!/usr/bin/python2.7
from flask import Flask, render_template,request, url_for, redirect, session,g
from flask_wtf import FlaskForm, RecaptchaField
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired, Length
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import  check_password_hash
from flask_login import LoginManager, login_required, login_user,UserMixin, logout_user,current_user
import atexit
from apscheduler.scheduler import Scheduler
import datetime,logging


app = Flask(__name__)
cron = Scheduler(daemon=True)
cron.start()


app.config['SECRET_KEY'] = ';Y8m4e#PUP\qQR]+"`ZAM(&td{8utWN?CtHXg6X(-z!$XP4?(t)~g4Kk9xgr8}ZaH]eGx(:uvNE}GVp;'
app.config['RECAPTCHA_PUBLIC_KEY'] = '6LePzS8UAAAAADoA_QPfGVUArvWnA0oF9eZi7-L7'
app.config['RECAPTCHA_PRIVATE_KEY'] = '6Lf3yS8UAAAAAExePlZihuoFhiZIcZOKWskui3sd'
app.config['TESTING'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///leave.db"
log_date= datetime.datetime.today().strftime('%m%d%Y')
filename = 'leavetracker.log'
logging.basicConfig(filename=filename,level=logging.DEBUG,format='%(asctime)s-%(levelname)s-%(funcName)s-%(message)s',
                    datefmt='%Y/%m/%d %H:%M:%S')
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
user_name={'jdas':'Jyoti','bdas':'Byomkesh','cjog':'Chinmay','skupwadde':'Swaapnesh','kahire':'Kapil',
           'ashinde':'Abhijit','dpatil':'Dinesh'}


class Users(UserMixin,db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(15), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    balance = db.Column(db.Integer,nullable=False,default=0)
    compoff = db.Column(db.Integer,nullable=False,default=0)
    leaves = db.relationship('Leavedetail', backref='user', lazy='dynamic')
    compoffs = db.relationship('Compoff', backref='user', lazy='dynamic')


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

class Leavedetail(db.Model):
    __tablename__='leavedetail'

    id = db.Column(db.Integer, primary_key=True)
    sdate = db.Column(db.DateTime, nullable=False)
    edate = db.Column(db.DateTime, nullable=False)
    days = db.Column(db.Integer, nullable=False)
    a_time = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.String(200))
    active = db.Column(db.Boolean, nullable=False,default=True)
    compoff = db.Column(db.Boolean,nullable=False,default=False)
    usr_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

class Compoff(db.Model):
    __tablename__ = 'compoff'

    id = db.Column(db.Integer, primary_key=True)
    worked_date = db.Column(db.DateTime,nullable=False)
    logged_date = db.Column(db.DateTime,nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=15)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8, max=80)])
    recaptcha = RecaptchaField()


@app.before_request
def before_request():
    session.permanent = True
    app.permanent_session_lifetime = datetime.timedelta(minutes=15)
    session.modified = True
    g.user = current_user

@app.route('/')
@app.route('/login/', methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_usr = Users.query.filter_by(username=form.username.data).first()
        if db_usr:
            if check_password_hash(db_usr.password, form.password.data):
                login_user(db_usr, remember=False)
                session['username'] = form.username.data
                session['login_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                session['user_id'] = current_user.get_id()
                logging.info('User {} logged in'.format(form.username.data))
                return render_template('welcome.html', name=user_name[session['username']])
            else:
                logging.error('User {} provided wrong password'.format(form.username.data))
                return render_template('login.html', form=form, error='Password is not matching...')
        else:
            return render_template('login.html',form=form, error='Check your username.')

    return render_template('login.html', form=form)

@app.route('/welcome/',methods=['GET','POST'])
@login_required
def welcome():
    return  render_template('welcome.html',name=user_name[session['username']])


@app.route('/plan/', methods=['GET','POST'])
@login_required
def plan():
    usr = Users.query.filter_by(id=session['user_id']).first()
    el = usr.balance
    comp = usr.compoff
    if request.method == 'POST':
        sdate = datetime.datetime.strptime(str(request.form['sdate']), '%Y-%m-%d')
        edate = datetime.datetime.strptime(str(request.form['edate']), '%Y-%m-%d')
        days = int(request.form['days'])
        ctime = datetime.datetime.now()
        reason = request.form['reason']
        leave_type = request.form.get('type')
        if sdate > edate:
            logging.error('User {} provided a wrong date range'.format(session['username']))
            return render_template('plan.html',error='Start date is bigger than End date..')

        if leave_type == 'leave':
            if usr.balance > 0 and days <= usr.balance:
                leave_apply = Leavedetail(sdate=sdate,edate=edate,a_time=ctime,days=days,reason=reason,active=True,compoff=False,usr_id=session['user_id'])
                if leave_apply:
                    usr.balance = usr.balance - days
                    db.session.add(leave_apply)
                    db.session.commit()
                    request.form = {}
                    logging.info('User {} successfully applied for a leave'.format(session['username']))
                    return render_template('plan.html',message='You have applied for leave from {} to {}'.format(sdate,edate))
            else:
                 return render_template('plan.html',error='You do not have much to apply for')

        else:
            if sdate == edate:
                if usr.compoff > 0:
                    comp_apply = Leavedetail(sdate=sdate,edate=edate,a_time=ctime,days=days,reason=reason,active=True,compoff=True,usr_id=session['user_id'])
                    if comp_apply:
                        usr.compoff = comp - 1
                        db.session.add(comp_apply)
                        db.session.commit()
                        request.form = {}
                        logging.info('User {} applied for a compoff redeemtion'.format(session['username']))
                        return render_template('plan.html',message='You have redeemed a compoff')
                    else:
                        return render_template('plan.html',error='Facing some issue,Try after some time!')
                else:
                    return  render_template('plan.html',error='You dont have balance to apply for compoff...')
            else:
                logging.warning('User {} trying to apply compoff for more than 1 day'.format(session['username']))
                return render_template('plan.html',error='Compoff can apply for a single day only!!!')

    return render_template('plan.html',message='You have {} nos of leave and {} nos of compoff.'.format(usr.balance,usr.compoff))

@app.route('/compoff/',methods=['GET','POST'])
@login_required
def compoff():
    if request.method == 'POST':
        if request.form['compoff']:
            worked_date = datetime.datetime.strptime(str(request.form['compoff']),'%Y-%m-%d')
            log_time = datetime.datetime.now()
            user_id = int(current_user.get_id())
            add_compoff = Compoff(worked_date=worked_date,logged_date=log_time,user_id=user_id)
            user_compoff = Users.query.filter_by(id=user_id).first()
            if add_compoff and user_compoff:
                db.session.add(add_compoff)
                user_compoff.compoff = user_compoff.compoff + 1
                db.session.commit()
                request.form = {}
                logging.info('User {} added a new compoff'.format(session['username']))
                return render_template('compoff.html',message='Added {} as compoff :)'.format(str(worked_date).split()[
                    0]))

    return render_template('compoff.html')

@app.route('/logout/')
@login_required
def logout():
    logout_user()
    logging.info('User {} logged out'.format(session['username']))
    return redirect(url_for('login'))

@app.route('/cancel/',methods=['GET','POST'])
@login_required
def cancel():
    leaves = Leavedetail.query.filter_by(usr_id=session['user_id'],active=True).all()
    today = datetime.datetime.today().strftime('%Y-%m-%d')
    for d in xrange(len(leaves)):
        if leaves[d].sdate.strftime('%Y-%m-%d') >= today:
            return render_template('cancel.html',list=leaves[d])
    else:
        return render_template('cancel.html',message='You dont have leaves to cancel...')

@app.route('/cancel/<string:input>')
@login_required
def cancelling(input):
    sdate,edate,id,days = input.split('=')
    sdate = datetime.datetime.strptime(sdate,'%Y-%m-%d %H:%S:%M')
    edate = datetime.datetime.strptime(edate,'%Y-%m-%d %H:%S:%M')
    leaves = Leavedetail.query.filter_by(usr_id=int(id),sdate=sdate ,edate=edate).first()
    users = Users.query.filter_by(id=id).first()
    if leaves.compoff:
            leaves.active = False
            leaves.compoff = False
            users.compoff = users.compoff + 1
            db.session.commit()
    else:
            days = int(days)
            new_balance = users.balance + days
            leaves.active = False
            users.balance = new_balance
            db.session.commit()
    logging.info('User {} cancelled a leave from the planed leaves'.format(session['username']))
    return redirect('cancel')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html',error=e)

def add_leave():
    for user in Users.query.all():
        user.balance += 2

    db.session.commit()
    logging.info('2 leaved added to everyone automatically')

cron.add_cron_job(add_leave,hour='*/4',minute='00', day='*',month='*')

atexit.register(lambda: cron.shutdown(wait=False))



if __name__ == '__main__':
    app.run()
