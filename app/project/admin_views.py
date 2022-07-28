import os
from datetime import datetime
from flask import redirect, render_template, Blueprint, request, session, url_for
from flask_login import current_user
from flask import current_app as app
from flask_admin import Admin, BaseView, expose
from .models import db, User
from .routes import read_json, write_json

class SecuredBaseView(BaseView):
    def is_accessible(self):
        admin_json_path = os.path.join(app.root_path,"admin_users.json")
        admin_users = read_json(admin_json_path,False,False)
        return current_user.name in admin_users

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('auth_bp.login_page', next=request.url))

class SupportList(SecuredBaseView):
    @expose('/')
    def support_list(self):
        all_messages=read_json(os.path.join(app.root_path,"all_messages.json"))
        return self.render('support_list.html',messages=all_messages)

class SupportView(SecuredBaseView):
    @expose('/', methods=['GET','POST'])
    def support(self):
        messages_path = os.path.join(app.root_path,"users",self.endpoint,"messages.json")
        alerts_path = os.path.join(app.root_path,"users",self.endpoint,"alerts.json")
        session['target_messages'] = read_json(messages_path,False,False)
        if request.method == "POST":
            new_message = request.form['send_msg']
            if new_message != "":
                ts = datetime.now()
                session['target_messages'].insert(0,{"sender":current_user.name,"date":ts.strftime("%B %d, %Y at %H:%M:%S"), "message":new_message})
                write_json(session['target_messages'],messages_path,False)
                target_alerts = read_json(alerts_path,False,False)
                target_alerts.insert(0,"New response from "+current_user.name+" to your support query.")
                write_json(target_alerts,alerts_path,False)
        return self.render('support_messaging_admin.html', current_user = current_user.name, messages=session['target_messages'], customer = self.name, endpoint = self.endpoint)
