import os
import random
import time
from flask import Flask, request, render_template, session, flash, redirect, \
    url_for, jsonify, Response
from flask_mail import Mail, Message
from celery import Celery
from models.Model import *
import hashlib
import json
import multiprocessing
from multiprocessing import Process

app = Flask(__name__)
app.config.from_object('config.BaseConfig')

db_session = Session()


# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = 'flask@example.com'

# Celery configuration
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/1'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/1'


# Initialize extensions
mail = Mail(app)

# Initialize Celery
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


@celery.task
def send_async_email(email_data):
    """Background task to send an email with Flask-Mail."""
    msg = Message(email_data['subject'],
                  sender=app.config['MAIL_DEFAULT_SENDER'],
                  recipients=[email_data['to']])
    msg.body = email_data['body']
    with app.app_context():
        mail.send(msg)


@celery.task(bind=True)
def long_task(self):
    """Background task that runs a long function with progress reports."""
    verb = ['Starting up', 'Booting', 'Repairing', 'Loading', 'Checking']
    adjective = ['master', 'radiant', 'silent', 'harmonic', 'fast']
    noun = ['solar array', 'particle reshaper', 'cosmic ray', 'orbiter', 'bit']
    message = ''
    total = random.randint(10, 50)
    for i in range(total):
        if not message or random.random() < 0.25:
            message = '{0} {1} {2}...'.format(random.choice(verb),
                                              random.choice(adjective),
                                              random.choice(noun))
        self.update_state(state='PROGRESS',
                          meta={'current': i, 'total': total,
                                'status': message})
        time.sleep(1)
    return {'current': 100, 'total': 100, 'status': 'Task completed!',
            'result': 42}


@celery.task
def add(a, b):
    return a + b


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template('index.html', email=session.get('email', ''))
    email = request.form['email']
    session['email'] = email

    # send the email
    email_data = {
        'subject': 'Hello from Flask',
        'to': email,
        'body': 'This is a test email sent from a background Celery task.'
    }
    if request.form['submit'] == 'Send':
        # send right away
        send_async_email.delay(email_data)
        flash('Sending email to {0}'.format(email))
    else:
        # send in one minute
        send_async_email.apply_async(args=[email_data], countdown=60)
        flash('An email will be sent to {0} in one minute'.format(email))

    return redirect(url_for('index'))


@app.route('/longtask', methods=['POST'])
def longtask():
    task = long_task.apply_async()
    return jsonify({}), 202, {'Location': url_for('taskstatus',
                                                  task_id=task.id)}


@app.route('/status/<task_id>')
def taskstatus(task_id):
    task = long_task.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'status': task.info.get('status', '')
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            'current': 1,
            'total': 1,
            'status': str(task.info),  # this is the exception raised
        }
    return jsonify(response)


@app.route("/demo/login", methods=['GET', 'POST'])
def login_index():
    if request.method == 'GET':
        return render_template("login.html")
    elif request.method == 'POST':
        app.logger.debug(request.form.get('account'))
        app.logger.debug(request.form.get('password'))
        account = request.form.get('account')
        password = request.form.get('password')
        select_data = db_session.query(User).all()
        for item in select_data:
            if item.account == account and item.password == hashlib.md5(password.encode("utf8")).hexdigest():
                session['username'] = account
                app.logger.info(session)
                return jsonify({'code': 0, 'url': url_for('user_index'), 'account': account})
            else:
                return jsonify({'code': -1, 'url': url_for('login_index'), 'account': account, 'msg': '账号或者密码错误'})
        app.logger.info(select_data)

        return "OK"


@app.route('/hwq/user', methods=['GET', 'POST'])
def user_info():

    if request.method == 'GET':
        return render_template('info_opera.html')
    elif request.method == 'POST':
        raw_data = request.form.get('data_send')
        app.logger.info(raw_data)
        app.logger.info(type(raw_data))
        src_data = json.loads(request.form.get('data_send'))
        app.logger.info(type(src_data))
        if isinstance(src_data, list):
            app.logger.info('insert')
            db_data = db_session.query(User).all()
            app.logger.info(db_data)
            ids = [_x.id for _x in db_data]

            app.logger.info(ids)
            for item in src_data:
                app.logger.info(item)
                if int(item['id']) in ids:
                    db_session.query(User).filter_by(id=item['id']).update(item)
                else:
                    insert_data = User(item)
                    app.logger.info(insert_data)
                    db_session.add(insert_data)
        else:
            if src_data['type'] == 'delete':
                app.logger.info('delete')
                db_session.query(User).filter_by(id=src_data['id']).delete()
            elif src_data['type'] == 'update':
                app.logger.info('update')
                update_data = {}
                for k, v in src_data.items():
                    if k != 'type':
                        update_data[k] = v
                app.logger.info(update_data)
                db_session.query(User).filter_by(id=src_data['id']).update(update_data)
        db_session.commit()
        return jsonify({'code': 0, 'msg': '操作成功'})


def procedure(tm, interval):
    print('process{} start'.format(os.getpid()))
    while interval > 0:
        # time.sleep(tm)
        interval -= 1
    print('process{} end'.format(os.getpid()))


@app.route('/hwq/alarm', methods=['POSt'])
def alarm():
    if request.method == 'POST':
        src_data = request.form.get('alarm_type')
        app.logger.info(src_data)
        if src_data == 'cpu':
            print('父进程 {}启动...'.format(os.getpid()))
            p1 = Process(target=procedure, args=(3, 3))
            p2 = Process(target=procedure, args=(3, 3))
            # p3 = Process(target=procedure, args=(3,))
            p1.start()
            p2.start()
            p1.join()
            p2.join()
            time.sleep(15)
            print('父进程 {}结束!!!'.format(os.getpid()))
        elif src_data == 'mem':
            app.logger.error('内存错误')
            raise MemoryError
    return jsonify({'code': 0, 'msg': '报警成功'})


@app.route('/hwq/init', methods=['GET'])
def init():
    select_data = db_session.query(User).all()
    back_data = []
    for item in select_data:
        temp = {}
        temp['id'] = item.id
        temp['account'] = item.account
        temp['password'] = item.password
        temp['phone'] = item.phone
        back_data.append(temp)
    return jsonify({'code': 0, 'data': back_data, 'msg': '初始化成功'})


@app.route('/demo/user', methods=['GET'])
def user_index():
    if request.method == 'GET':
        return render_template('user.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('cas_login.html')


@app.route("/add", methods=['GET', 'POST'])
def addtask():
    task = add.apply_async()
    app.logger.debug(task)
    return jsonify({}), 202, {'Location': url_for('taskstatus',
                                                  task_id=task.id)}


if __name__ == '__main__':
    app.run(debug=True, processes=True)
