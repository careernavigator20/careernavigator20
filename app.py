from flask import *
from flask_cors import CORS
from sqlalchemy import func
from model import db,Student,Interest,Notification,Counselor,CounselorSchedule,Feedback,Resource,Payment,Admin,Appointment
from datetime import datetime,timezone,timedelta
from apscheduler.schedulers.background import BackgroundScheduler 
from flask_mail import Mail,Message
from flask_migrate import Migrate
import random
import razorpay
import json
from config import Config
import stripe



app = Flask(__name__)
app.config.from_object('config.Config')
CORS(app)

db.init_app(app)
migrate = Migrate(app, db)

mail = Mail(app)

# Set up Stripe with your key
stripe.api_key = "sk_test_51R2sFf4DuQBaqDtl71gUnux6EbAe6Sg8Mo7m0QEshvpAPI5RB7LDodbVDN1Oj01pJBtPd3koeFa9Xa28J6rN1AJT00WwzlcMNx"

scheduler = BackgroundScheduler()

# Initialize Razorpay client
razorpay_client = razorpay.Client(
    auth=(Config.RAZORPAY_KEY_ID, Config.RAZORPAY_KEY_SECRET)
)
# ------------------------------ Apscheduler--------------------------------

@app.route('/send_scheduled_notifications')
def send_scheduled_notifications():
    try:
        now = datetime.now()
        formatted_now = now.strftime('%Y-%m-%d %H:%M:%S')

        with app.app_context():
            notifications_to_update = Notification.query.filter(
                Notification.status == 'scheduled',
                db.func.strftime('%Y-%m-%d %H:%M:%S', Notification.schedule_time) <= formatted_now
            ).all()

            if notifications_to_update:
                print(f"Current UTC time: {now}")
                print(f"Notifications to update: {len(notifications_to_update)}")
                for notification in notifications_to_update:
                    print(f"Notification: ID={notification.id}, Schedule Time={notification.schedule_time}")

                rows_updated = Notification.query.filter(
                    Notification.status == 'scheduled',
                    db.func.strftime('%Y-%m-%d %H:%M:%S', Notification.schedule_time) <= formatted_now
                ).update({"status": "sent"})
                db.session.commit()
                print(f"{rows_updated} rows updated")
                return jsonify({'status': 'Updated', 'count': rows_updated}), 200
            else:

                print("No notifications to update.")
                return jsonify({'status': 'No Updates', 'count': 0})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'status': 'Error', 'message': str(e)})

def update_appointments():
    try:
        with app.app_context():
            now = datetime.now()  # Get the current time
            formatted_now = now.strftime('%Y-%m-%d %H:%M:%S')  # Format as string
            # print(f"Current Time (formatted): {formatted_now}")

            appointments = Appointment.query.filter(
                Appointment.counselor_status == 'approved',
                Appointment.student_status == 'upcoming'
            ).all()

            if not appointments:
                print("No appointments to process.")
                return

            for appointment in appointments:
                try:
                    session_time = datetime.combine(
                        appointment.date,
                        datetime.strptime(appointment.time_slot.split(' - ')[0], '%H:%M').time()
                    )

                    formatted_session_time = session_time.strftime('%Y-%m-%d %H:%M:%S')
                    # print(f"Appointment ID={appointment.id}, Session Time (formatted)={formatted_session_time}, Current Time={formatted_now}")

                    # Compare as datetime objects
                    if now >= session_time:
                        appointment.student_status = 'live'
                        print(f"Updating Appointment ID={appointment.id} to live.")

                        # Sending notification emails
                        try:
                            send_email(
                                appointment.student.email,
                                "Session is now live",
                                f"Your session scheduled for {appointment.purpose} on {appointment.date} at {appointment.time_slot.split(' - ')[0]} is now live."
                            )
                            print(f"Email sent to student: {appointment.student.email}")
                        except Exception as e:
                            print(f"Error sending email to student: {e}")

                        try:
                            send_email(
                                appointment.counselor.email,
                                "Session is now live",
                                f"Your session scheduled for {appointment.purpose} on {appointment.date} at {appointment.time_slot.split(' - ')[0]} is now live."
                            )
                            print(f"Email sent to counselor: {appointment.counselor.email}")
                        except Exception as e:
                            print(f"Error sending email to counselor: {e}")

                except Exception as e:
                    print(f"Error processing Appointment ID={appointment.id}: {e}")

            # Commit all changes after processing all appointments
            db.session.commit()
    except Exception as e:
        print(f"Error in update_appointments: {e}")


with app.app_context():
    scheduler.add_job(send_scheduled_notifications, 'interval', minutes=1, replace_existing=True)
    scheduler.add_job(update_appointments, 'interval', minutes=1,replace_existing=True)
    scheduler.start()


def send_email(to, subject, body):
    msg = Message(subject, sender=app.config['MAIL_USERNAME'], recipients=[to])
    msg.body = body
    try:
        mail.send(msg)
        print(f"Email sent to {to}")
    except Exception as e:
        print(f"Error sending email to {to}: {e}")



# =========================================================================================== #
# ------------------------------------Admin Panel-------------------------------------------- #
# =========================================================================================== #


@app.route('/admin_regi', methods=['GET', 'POST'])
def admin_regi():
    if request.method == 'POST':
        try:
            full_name = request.form.get('fullName')
            email = request.form.get('email')
            username = request.form.get('username')
            password = request.form.get('password')
            contact_number = request.form.get('contactNumber')
            security_question = request.form.get('securityQuestion')
            security_answer = request.form.get('securityAnswer')

            profile_picture = request.files.get('profilePicture')

            if profile_picture:
                filename = profile_picture.filename
                file_path = f"static/img/admin_uploads/{filename}"
                profile_picture.save(file_path)

            if not all([full_name, email, username, password, contact_number, security_question, security_answer]):
                return jsonify({'success': False, 'message': 'All fields are required.'})

            if Admin.query.filter((Admin.email == email) | (Admin.username == username)).first():
                return jsonify({'success': False, 'message': 'Email or username already exists.'})


            new_admin = Admin(
                full_name = full_name,
                email = email,
                username = username,
                password = password,
                contact_number = contact_number,
                security_question = security_question,
                security_answer = security_answer,
                profile_picture = file_path
            )

            db.session.add(new_admin)
            db.session.commit()

            return jsonify({'success': True, 'message': 'Admin registered successfully!'})

        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)})

    return render_template('admin/admin_regi.html')

# @app.route('/test_email')
# def test_email():
#     try:
#         send_email(
#             "mihirsudani128@gmail.com",
#             "Test Email",
#             "This is a test email to verify email sending functionality."
#         )
#         return "Test email sent successfully!"
#     except Exception as e:
#         return f"Failed to send test email: {e}"


@app.route('/admin_login',methods=['GET','POST'])
def admin_login():
    if request.method == 'GET':
        return render_template('admin/admin_login.html')
    
    if request.method == 'POST':
        data = request.get_json()
        username =  data.get('username')
        password =  data.get('password')

        admin_user = Admin.query.filter((Admin.username == username) | (Admin.email == username)).first()

        if admin_user:
            if admin_user.password == password:
                return jsonify({"success": True, "message": "Login successful!"}), 200
            else:
                return jsonify({"success": False, "message": "Invalid password."}), 401
        else:
            return jsonify({"success": False, "message": "User not found."}), 404
        

@app.route('/admin_dash')
def dashboard():
    return render_template('admin/dashboard.html', active_page='dashboard')

@app.route('/students',methods=['GET'])
def students():
    if request.method == 'GET':
        students = Student.query.all()
        return render_template('admin/manage_stud.html', active_page='students',students=students)


@app.route('/edit_stud/<int:student_id>',methods=['GET','PUT'])
def edit_stud(student_id):
    # student = Student.query.get(student_id)
    student = db.session.get(Student,student_id)
    if request.method == 'GET':
        interests = Interest.query.all()
        return render_template('admin/edit_stud.html',active_page='students',student=student,interests=interests)

    if request.method == 'PUT':
        data = request.get_json()
        print(data)
        name = data.get('name','').strip()
        email = data.get('email','').strip()
        selected_interests = data.get('interests',[])

        if not name or not email or len(selected_interests) < 2:
            return jsonify({'msg':'Invalid Input!'}), 400
        
        student.name = name
        student.email = email
        student.interests = ','.join(selected_interests)

        db.session.commit()
        return jsonify({'msg':'Student Updated Successfully!'}), 200

@app.route('/delete_stud/<int:student_id>',methods=['DELETE'])
def delete_stud(student_id):
    student = db.session.get(Student,student_id)

    if not student:
        return jsonify({'msg' : 'Interest Not Found!'}), 404
    
    db.session.delete(student)
    db.session.commit()
    return jsonify({'msg':'Student Deleted Successfully!'}), 200
    


@app.route('/counselors')
def counselors():
    counselors = Counselor.query.all()
    return render_template('admin/manage_counselor.html', active_page='counselors',counselors=counselors)

@app.route('/approve_counselor', methods=['POST'])
def approve_counselor():
    data = request.get_json()
    counselor_id = data.get('counselor_id')
    action = data.get('action')

    counselor = Counselor.query.get_or_404(counselor_id)

    if action == 'approve':
        if counselor.approval_status == 'approved':
            return jsonify({'success': False, 'error': 'Counselor is already approved.'}), 400

        counselor.approval_status = 'approved'

        verification_code = random.randint(100000,999999)
        counselor.verification_code = verification_code
        db.session.commit()

        msg = Message(
            'Approval Notification',
            sender=app.config['MAIL_USERNAME'],
            recipients=[counselor.email]
        )
        msg.body = (
            f"Dear {counselor.full_name},\n\n"
            f"Congratulations! Your profile has been approved. "
            f"You can now log in and access your account.\n\n"
            f"Here is your verification code: {verification_code}\n\n"
            f"Best regards,\nCareerNavigator Team"
        )
        try:
            mail.send(msg)
            return jsonify({'success': True, 'message': 'Counselor approved and notification email sent.'})
        except Exception as e:
            return jsonify({'success': False, 'error': 'Email failed to send.'}), 500

    elif action == 'reject':
        if counselor.approval_status == 'rejected':
            return jsonify({'success': False, 'error': 'Counselor is already rejected.'}), 400

        counselor.approval_status = 'rejected'
        db.session.commit()
        return jsonify({'success': True, 'message': 'Counselor rejected.'}), 200

    return jsonify({'success': False, 'error': 'Invalid action.'})

# ---------------------------------- Interests -----------------------------------


@app.route('/interests')
def interests():
    all_interest = Interest.query.all()
    return render_template('admin/interests.html',interests=all_interest, active_page='interests')

#-------------- Add Interests

@app.route('/add_interest', methods=['GET', 'POST'])
def add_interest():
    if request.method == 'GET':
        return render_template('admin/add_interest.html',active_page='interests')
    
    if request.method == 'POST':
            data = request.get_json()
            interest_name = data.get('interest_name', '').strip()
            category = data.get('category', '').strip().title()

            if not interest_name or not category:
                return jsonify({'msg': 'Fields Are Required!'}), 400

            existing_interest = Interest.query.filter(
                db.func.lower(Interest.interest_name) == interest_name.lower()
            ).first()

            if existing_interest:
                return jsonify({'msg': 'Interest Already Exists!'}), 400

            new_interest = Interest(
                interest_name=interest_name,
                category=category
            )
            db.session.add(new_interest)
            db.session.commit()

            return jsonify({'msg': 'Interest Added Successfully!'}), 200
    

#-------------- Delete Interests ----------------------------------------------------

@app.route('/delete_interest/<int:interest_id>', methods=['DELETE'])
def delete_interest(interest_id):
    interest = Interest.query.get(interest_id)

    if not interest:
        return jsonify({'msg' : 'Interest Not Found!'}), 404
    
    db.session.delete(interest)
    db.session.commit()
    return jsonify({'msg' : 'Interest Deleted Successfully!'}), 200

# ------------------------------------------------------------------------------------

@app.route('/appointments')
def appointments():
    return render_template('admin/appointments.html', active_page='appointments')

@app.route('/monitor_resources')
def monitor_resources():

    resources = Resource.query.all()    
    counselor_names = {
        counselor.id: counselor.full_name
        for counselor in Counselor.query.all()
    }

    resource_types = list(set(resource.file_type for resource in resources))
    managed_by = list(set(counselor_names.get(resource.counselor_id, 'Unknown') for resource in resources))

    resources_with_counselor = [
        {
            'id': resource.id,
            'title': resource.title,
            'category': resource.category,
            'file_type': resource.file_type,
            'date_uploaded': resource.date_uploaded,
            'counselor_name': counselor_names.get(resource.counselor_id, 'Unknown')
        }
        for resource in resources
    ]

    return render_template(
        'admin/monitor_resource.html',
        resources=resources_with_counselor,
        resource_types=resource_types,
        managed_by=managed_by,
        active_page='monitor_resources'
    )


@app.route('/monitor_feedbacks', methods=['GET'])
def monitor_feedbacks():
    rating = request.args.get('rating')
    if rating and rating.isdigit():
        feedbacks = Feedback.query.filter(Feedback.rating == int(rating)).all()
    else:
        feedbacks = Feedback.query.all()
    if request.args.get('ajax'):  
        return jsonify([{
            'counselor_name': feedback.counselor.full_name,
            'student_name': feedback.student.name,
            'description': feedback.feedback_text,
            'rating': feedback.rating
        } for feedback in feedbacks])
    return render_template('admin/monitor_feedbacks.html', feedbacks=feedbacks, active_page='monitor_feedbacks')


# --------------------------- Reports ------------------------------------
@app.route('/reports')
def reports():
    return render_template('admin/reports.html', active_page='reports')

from collections import Counter

@app.route('/popular_interests', methods=['GET'])
def popular_interests():
    try:
        students = Student.query.all()
        interests_list = []
        for student in students:
            if student.interests:
                interests_list.extend(student.interests.split(','))

        interest_counts = Counter(interests_list)

        data = [{'interest': interest, 'count': count} for interest, count in interest_counts.items()]

        return jsonify({'status': 'success', 'data': data}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# --------------------------- notifications ------------------------------------

@app.route('/notifications',methods=['GET','POST'])
def notifications():
    if request.method == 'GET':
        notifications = Notification.query.order_by(Notification.created_at.desc()).all()
        return render_template('admin/notifications.html', active_page='notifications',notifications=notifications)

    if request.method == 'POST':
        data = request.get_json()
        title = data.get('title')
        message = data.get('message')
        recipients = data.get('recipients')
        schedule = data.get('schedule')
        schedule_time = data.get('schedule_time',None)

        if schedule == 'later' and schedule_time:
            schedule_time = datetime.fromisoformat(schedule_time).replace(tzinfo=timezone.utc)
        else:
            schedule_time = datetime.now(timezone.utc)
        
        new_notification = Notification(
            title=title,
            message=message,
            recipients=recipients,
            schedule_time=schedule_time,
            status = 'scheduled' if schedule == 'later' else 'sent'
        )
        db.session.add(new_notification)
        db.session.commit()
        return jsonify({'msg':'Notiication Added Successfully!'}), 201
    
    
@app.route('/get_notifications')
def get_notifications():
    with app.app_context():
        notifications = Notification.query.all()
        notifications_data = [
            {'id':n.id,'message':n.message,'timestamp':n.schedule_time.strftime('%Y-%m-%d %H:%M:%S')}
            for n in notifications
        ]
        return jsonify({'count': len(notifications_data),'notifications':notifications_data})



@app.route('/admins')
def admins():
    return render_template('admin/admins.html', active_page='admins')

@app.route('/logout')
def logout():
    return render_template('admin/logout.html', active_page='logout')


# =========================================================================================== #
# ------------------------------------Student Panel------------------------------------------ #
# =========================================================================================== #



@app.route('/register',methods=['GET','POST'])
def register():

    if request.method == 'GET':
        all_interests = Interest.query.all()
        return render_template('student/register.html',interests=all_interests)
    
    if request.method == 'POST':
        data = request.get_json()
        name = data.get('fullName')
        email = data.get('email')
        contact_number = data.get('contactNumber')
        password = data.get('password')
        con_password = data.get('confirmPassword')
        interests = data.get('interests',[])

        if not (name and email and contact_number and password and con_password and interests):
            return jsonify({'msg': 'All fields are required!'}), 400

        if password != con_password:
            return jsonify({'msg': 'Passwords do not match!'}), 400
        
        if len(interests) < 2:
            return jsonify({'msg': 'Please select at least two interests!'}), 400
        
        new_student = Student(
                name=name,
                email=email,
                contact_number=contact_number,
                password=password,
                con_password=con_password,
                interests=",".join(interests)
            )
        db.session.add(new_student)
        db.session.commit()
        return jsonify({'msg': 'Student Registered Successfully!'}), 200
    
@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'GET':
        # Get redirect parameters
        redirect_to = request.args.get('redirect', '')
        package = request.args.get('package', '')
        
        return render_template('student/login.html', redirect_to=redirect_to, package=package)
    
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        redirect_to = data.get('redirect_to', '')
        package = data.get('package', '')

        student = Student.query.filter_by(name=username, con_password=password).first()

        if student:
            print(student.name+" ",student.id)
            
            session['student_id'] = student.id
            session['student_name'] = student.name
            
            # Handle redirect after login
            if redirect_to == 'payment':
                return jsonify({
                    'success': True,
                    'message': 'Login Successful!',
                    'redirect': f"/payment?package={package}"
                }), 200
            else:
                return jsonify({'success': True, 'message': 'Login Successful!'}), 200
        else:
            return jsonify({'success': False, 'message': 'Invalid username or password'}), 401


@app.route('/stud_dash')
def stud_dash():
    if 'student_name' not in session:
        return redirect(url_for('student_login'))
    recent_resources = Resource.query.order_by(Resource.date_uploaded.desc()).limit(3).all()
    return render_template('student/stud-dash.html',active_page='stud_dash',recent_resources=recent_resources)

@app.route('/find_counselors')
def find_counselors():
    if 'student_name' not in session:
        return redirect(url_for('student_login'))
    counselors = Counselor.query.filter_by(approval_status='approved')
    return render_template('student/find_counselors.html',active_page='find_counselors',counselors=counselors)

@app.route('/schedule', methods=['GET','POST'])
def schedule():
    if 'student_name' and 'student_id' not in session:
        return redirect(url_for('student_login'))
    if request.method == 'GET':
        counselors = Counselor.query.all()
        
        return render_template(
            'student/schedule.html',
            active_page='schedule',
            counselors=counselors
        )
    
    if request.method == 'POST':
        data = request.get_json()
        print(data)
        counselor_id = data.get('counselor_id')
        appointment_date = data.get('date')
        time_slot = data.get('time_slot')
        purpose = data.get('purpose', '')

        if not counselor_id or not appointment_date or not time_slot:
            return jsonify({'message': 'All required fields must be filled out'}), 400
        
        appointment_date_obj = datetime.strptime(appointment_date, '%Y-%m-%d').date()
        
        new_appointment = Appointment(
            student_id = session.get('student_id'),
            counselor_id = int(counselor_id),
            date = appointment_date_obj,
            time_slot = time_slot,
            purpose = purpose
        )

        db.session.add(new_appointment)    
        db.session.commit()
        return jsonify({'message': 'Appointment booked successfully!'}), 200

@app.route('/get-time-slots-for-date/<int:counselor_id>/<string:selected_date>', methods=['GET'])
def get_time_slots_for_date(counselor_id, selected_date):
    print(f"Route called with counselor_id={counselor_id}, selected_date={selected_date}")
    counselor = Counselor.query.get(counselor_id)
    if not counselor:
        return jsonify({'success': False, 'message': 'Counselor not found'})

    day_of_week = datetime.strptime(selected_date, "%Y-%m-%d").strftime('%A')
    print(f"Day of Week: {day_of_week}")

    schedules = CounselorSchedule.query.filter_by(
        counselor_id=counselor_id,
        day_of_week=day_of_week
    ).all()
    print(f"Schedules: {schedules}")

    time_slots = []
    for schedule in schedules:
        print(f"Schedule: {schedule}")
        time_slot = schedule.time_slots
        time_slots.append(f"{time_slot['startTime']} - {time_slot['endTime']}")

    print(f"Time Slots: {time_slots}")
    return jsonify({'success': True, 'time_slots': time_slots})



@app.route('/get_availability/<int:counselor_id>', methods=['GET'])
def get_availability(counselor_id):
    schedules = db.session.query(CounselorSchedule).filter_by(counselor_id=counselor_id).all()

    availability = {}
    for schedule in schedules:
        if schedule.day_of_week not in availability:
            availability[schedule.day_of_week] = []
        availability[schedule.day_of_week].append(schedule.time_slots)

    available_days = list(availability.keys())
    time_slots = availability

    print(f"Available days: {available_days}", flush=True)
    print(f"Time slots: {time_slots}", flush=True)

    return jsonify({
        'available_days': available_days,
        'time_slots': time_slots
    })


@app.route('/stud_appointments', methods=['GET', 'POST'])
def stud_appointments():
    if 'student_name' not in session:
        return redirect(url_for('student_login'))
    
    student_id = session.get('student_id')
    
    if request.method == 'GET':
        upcoming_appointments = Appointment.query.filter_by(student_id=student_id, student_status='upcoming').all()
        completed_appointments = Appointment.query.filter_by(student_id=student_id, student_status='completed').all()
        canceled_appointments = Appointment.query.filter_by(student_id=student_id, student_status='canceled').all()

        return render_template(
            'student/appointments.html',
            active_page='appointments',
            upcoming_appointments=upcoming_appointments,
            completed_appointments=completed_appointments,
            canceled_appointments=canceled_appointments
        )
    
@app.route('/stud_room')
def stud_room():
    return render_template('student/stud_room.html')

    
@app.route('/resources')
def resources():
    if 'student_name' not in session:
        return redirect(url_for('student_login'))

    resources_data = Resource.query.all()

    resources = [
        {
            "id": resource.id,
            "title": resource.title,
            "category": resource.category,
            "description": resource.description, 
            "file_type": resource.file_type,
            "file_size": resource.file_size,
            "downloads": resource.downloads,
            "file_link": f"/static/resources/{resource.title.lower().replace(' ', '_')}.{resource.file_type}"
        }
        for resource in resources_data
    ]


    categories = ["all"] + list(set([resource.category for resource in resources_data]))

    return render_template('student/resources.html', categories=categories, resources=resources, active_page='resources')


@app.route('/download_resource/<int:resource_id>',methods=['GET'])
def download_resource(resource_id):
    resource = Resource.query.get_or_404(resource_id)

    resource.downloads += 1
    db.session.commit()

    file_path = resource.file_link

    try:
        return send_file(file_path,as_attachment=True)
    except FileNotFoundError:
        return f"File Not Found : {file_path}!", 404
    

@app.route('/feedback',methods=['GET','POST'])
def feedback():
    if 'student_name' not in session:
        return redirect(url_for('student_login'))
    
    if request.method == 'GET':
        counselors = Counselor.query.filter_by(approval_status='approved')
        return render_template('student/feedback.html',active_page='feedback',counselors=counselors)
    
    if request.method == 'POST':
        data = request.get_json()
        counselor_id = data.get('couselor_id')
        rating = data.get('rating')
        feedback_text = data.get('feedback_text')

        if not counselor_id or not rating or not feedback_text:
            return jsonify({'error':'All Fields Are Required!'}), 400
        
        student = Student.query.filter_by(name=session['student_name']).first()
        if not student:
            return jsonify({'error':'Student Not Found!'}), 404
        
        feedback = Feedback(
            counselor_id = counselor_id,
            student_id = student.id,
            rating = rating,
            feedback_text = feedback_text
        )
        
        db.session.add(feedback)
        db.session.commit()

        return jsonify({'message':'Feedback Submitted Successfully!'}), 201
        


@app.route('/settings')
def settings():
    if 'student_name' not in session:
        return redirect(url_for('student_login'))
    return render_template('student/settings.html',active_page='settings')

@app.route('/stud_logout')
def stud_logout():
    session.pop('student_name',None)
    return redirect(url_for('student_login'))


# ============================================================================================ #
# ------------------------------------Counselor Panel----------------------------------------- #
# ============================================================================================ #

@app.route('/coun_regi', methods=['GET', 'POST'])
def coun_regi():
    if request.method == 'GET':
        all_interests = Interest.query.all()
        interests = [{'id': interest.id, 'interest_name': interest.interest_name} for interest in all_interests]
        return render_template('counselor/coun_regi.html', interests=interests)

    if request.method == 'POST':
            full_name = request.form.get('fullName')
            print(full_name)
            email = request.form.get('email')
            password = request.form.get('password')
            contact_number = request.form.get('contactNumber')
            specialization = request.form.get('specialization')
            bio = request.form.get('bio')

            profile_picture = request.files.get('profilePicture')
            profile_picture_path = None

            if profile_picture and profile_picture.filename != '':
                filename = profile_picture.filename
                profile_picture_path = f"static/img/coun_uploads/{filename}"
                profile_picture.save(profile_picture_path)

            new_counselor = Counselor(
                full_name=full_name,
                email=email,
                password=password,
                contact_number=contact_number,
                specialization=specialization,
                bio=bio,
                profile_picture=profile_picture_path
            )
            db.session.add(new_counselor)
            db.session.flush() 

            availability_days = json.loads(request.form.get('availabilityDays', '[]'))
            availability_slots = json.loads(request.form.get('availabilitySlots', '{}'))

            for day in availability_days:
                if day in availability_slots:
                    for slot in availability_slots[day]:
                        new_schedule = CounselorSchedule(
                            counselor_id=new_counselor.id,
                            day_of_week=day,
                            time_slots=slot
                        )
                        db.session.add(new_schedule)

            db.session.commit()

            return jsonify({'msg': 'Registration is done successfully!'}), 201

@app.route('/coun_login',methods=['GET','POST'])
def coun_login():
    if request.method == 'GET':
        return render_template('counselor/coun_login.html')
    
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
                return jsonify({"status": "error", "message": "All fields are required!"}), 400

        counselor = Counselor.query.filter_by(
                email=email,
                password=password,
            ).first()

        if counselor:
            session['counselor_id'] = counselor.id 
            session['counselor_name'] = counselor.full_name
            return jsonify({"status": "success", "message": "Login successful!"}), 200
        else:
            return jsonify({"status": "error", "message": "Invalid login credentials!"}), 401
    
@app.route('/verify_login', methods=['POST'])
def verify_login():
    if 'counselor_id' not in session:
        return jsonify({"status": "error", "message": "Session expired. Please log in again."}), 401
    
    counselor_id = session.get('counselor_id')

    data = request.get_json()
    verification_code = data.get('verification_code')

    if not verification_code:
        return jsonify({"status": "error", "message": "Verification code is required."}), 400
    
    counselor = Counselor.query.filter_by(id=counselor_id,verification_code=verification_code).first()

    if counselor:
        session['counselor_id'] = counselor.id
        session['counselor_name'] = counselor.full_name
        return jsonify({"status": "success", "message": "Verification successful!"}), 200
    else:
        return jsonify({"status": "error", "message": "Invalid verification code."}), 401


@app.route('/counselor_dash')
def counselor_dash():
    if 'counselor_id' and 'counselor_name' not in session:
        return redirect(url_for('coun_login'))
    return render_template('counselor/counselor_dash.html',active_page='counselor_dash')

@app.route('/coun_appointment')
def coun_appointment():
    if 'counselor_id' and 'counselor_name' not in session:
        return redirect(url_for('coun_login'))
    
    counselor_id = session['counselor_id']

    appointments = db.session.query(Appointment).join(Student).filter(Appointment.counselor_id == counselor_id).all()
    print(appointments)

    print(appointments)
    appointment_list = [
        {
            'date_time': f"{appt.date.strftime('%b %d, %Y')} - {appt.time_slot}",
            'student_name': appt.student.name,
            'topic': appt.purpose,
            'student_status': appt.student_status.capitalize(),
            'counselor_status': appt.counselor_status.capitalize(),
            'id': appt.id  
        }
        for appt in appointments
    ]

    return render_template('counselor/coun_appointment.html',active_page='coun_appointment',appointments=appointment_list)

@app.route('/approve_appointment/<int:appointment_id>',methods=['POST'])
def approve_appointment(appointment_id):
    if 'counselor_id' and 'counselor_name' not in session:
        return redirect(url_for('coun_login'))
    
    appointment = Appointment.query.filter_by(id=appointment_id).first()

    if not appointment:
        return jsonify({'success': False, 'message': 'Appointment not found.'}), 404
    
    appointment.counselor_status = 'approved'
    appointment.student_status = 'upcoming'

    print(appointment.student_status)
    db.session.commit()
    update_appointments()

    return jsonify({'success': True, 'message': 'Appointment approved successfully.'}), 200

@app.route('/reject_appointment/<int:appointment_id>', methods=['POST'])
def reject_appointment(appointment_id):
    if 'counselor_id' not in session or 'counselor_name' not in session:
        return redirect(url_for('coun_login'))
    
    appointment = Appointment.query.filter_by(id=appointment_id).first()

    if not appointment:
        return jsonify({'success': False, 'message': 'Appointment not found.'}), 404

        
    appointment.counselor_status = 'rejected'
    appointment.student_status = 'canceled'

    db.session.commit()

    return jsonify({'success': True, 'message': 'Appointment rejected successfully.'}), 200

@app.route('/cancel_appointment/<int:appointment_id>', methods=['POST'])
def cancel_appointment(appointment_id):
    if 'counselor_id' not in session or 'counselor_name' not in session:
        return redirect(url_for('coun_login'))

    appointment = Appointment.query.filter_by(id=appointment_id).first()

    if not appointment:
        return jsonify({'success': False, 'message': 'Appointment not found.'}), 404

    # if appointment.counselor_status != 'Approved':
    #     print(f"Invalid status for cancellation: {appointment.counselor_status}")
    #     return jsonify({'success': False, 'message': 'Only approved appointments can be canceled.'}), 400

    appointment.counselor_status = 'canceled'
    appointment.student_status = 'none'
    db.session.commit()

    return jsonify({'success': True, 'message': 'Appointment canceled successfully.'}), 200


@app.route('/coun_view_stud')
def coun_view_stud():
    if 'counselor_id' not in session or 'counselor_name' not in session:
        return redirect(url_for('coun_login'))

    approved_appointments = (
        db.session.query(Appointment)
        .filter(Appointment.counselor_status == 'approved')
        .all()
    )

    students = [appointment.student for appointment in approved_appointments]

    for student in students:
        print(f"Student Name: {student.name}, Email: {student.email}")

    return render_template(
        'counselor/view_stud.html',
        active_page='coun_view_stud',
        students=students
    )

# @app.route('/get_messages',methods=['GET'])
# def get_messages(student_id):
#     if 'counselor_id' not in session:
#         return redirect(url_for('coun_login'))
    
#     counselor_id = session['counselor_id']
#     student= Student.query.get_or_404(student_id)

#     messages = Message.query.filter(
#         (Message.sender_id == counselor_id) & (Message.recipient_id == student_id) |
#         (Message.sender_id == student_id) & (Message.recipient_id == counselor_id)
#     ).order_by(Message.timestamp).all()

#     return render_template('counselor/coun_msg.html',active_page='coun_view_stud',student=student,messages=messages)

@app.route('/coun_room', methods=['GET'])
def coun_room():
    if request.method == 'GET':
        if 'counselor_id' not in session:
            return redirect(url_for('coun_login'))
    
    counselor_id = session['counselor_id'] 

    live_appointments = Appointment.query.filter_by(
    counselor_id=counselor_id,
    counselor_status='approved',
    student_status='live'
    ).all()

    return render_template('counselor/coun_room.html', appointments=live_appointments)


# @app.route('/start_meeting/<int:appointment_id>', methods=['GET'])
# def start_meeting(appointment_id):
#     # Validate the appointment
#     appointment = Appointment.query.filter_by(
#         id=appointment_id,
#         counselor_id=session['counselor_id'],
#         counselor_status='approved',
#         student_status='live'
#     ).first()

#     if not appointment:
#         return redirect(url_for('coun_room'))

#     # Generate a unique room name
#     room_name = f"room_{appointment.student_id}_{appointment.counselor_id}_{appointment.id}"


#     # Pass the room name and student details to the template
#     return render_template(
#         'counselor/start_meeting.html',
#         room_name=room_name,
#         student=appointment.student,
#         counselor_name=session.get('counselor_name', 'Counselor')
#     )

@app.route('/start_meeting/<int:appointment_id>', methods=['GET'])
def start_meeting(appointment_id):
    # Fetch the appointment using its ID
    appointment = Appointment.query.get_or_404(appointment_id)
    
    # Generate a full session link if it doesn't exist
    if not appointment.session_link:
        base_url = "https://meet.jit.si/"
        appointment.session_link = f"{base_url}appointment_{appointment.id}"
        db.session.commit()  # Save the updated session link in the database
    
    # Render the meeting page with the session link
    return render_template(
        'counselor/start_meeting.html',
        session_link=appointment.session_link
    )



@app.route('/manage_resources',methods=['GET','POST'])
def manage_resources():
    if request.method == 'GET':
        if 'counselor_id' not in session:
            return redirect(url_for('coun_login'))
        
        resources = Resource.query.filter_by(counselor_id=session['counselor_id']).all()
        return render_template('counselor/coun_resources.html',resources=resources)
    
    if request.method == 'POST':
        if 'file' not in request.files or 'title' not in request.form:
            return jsonify({'error':'Invalid Request!'}), 400
        
        title = request.form['title']
        file = request.files['file']
        category = request.form['category']
        description = request.form.get('description','No Description Provided')
        file_type = file.filename.split('.')[-1].upper()
        file_size = f"{round(len(file.read()) / 1024, 2)} KB"
        file.seek(0) 
        counselor_id = session.get('counselor_id')

        if not counselor_id:
            return jsonify({'error':'Unauthorized!'}), 403
        
        file_name = f"{title.replace(' ', '_').lower()}.{file_type}"
        file_path = f"static/resources/{file_name}"
        file.save(file_path)

        downloads = 0
        
        new_resource = Resource(
            title = title,
            category = category,
            description = description,
            file_type = file_type,
            file_size = file_size,
            file_link = file_path,
            downloads = downloads,
            counselor_id = counselor_id
        )

        db.session.add(new_resource)
        db.session.commit()
        return jsonify({
            'title': new_resource.title,
            'type': new_resource.file_type
        }), 200


@app.route('/get_resource/<int:resource_id>',methods=['GET'])
def get_resource(resource_id):
     resource = Resource.query.get(resource_id)
     if resource:
         return jsonify({
            'title': resource.title,
            'category': resource.category,
            'file_type': resource.file_type,
            'file_size': resource.file_size,
            'description': resource.description,
            'downloads': resource.downloads,
            'date_uploaded': resource.date_uploaded.strftime('%Y-%m-%d'),
        }), 200
     else:
         return jsonify({'error': 'Resource not found'}), 404
     
@app.route('/delete_resource/<int:resource_id>',methods=['DELETE'])
def delete_resource(resource_id):
    resource = Resource.query.get(resource_id)

    if not resource:
        return jsonify({'error':"Resource Not Found!"}), 404
    
    db.session.delete(resource)
    db.session.commit()
    return jsonify({'message':'Resource Deleted Successfully!'}), 200

@app.route('/coun_feedback')
def coun_feedback():
    if 'counselor_id' and 'counselor_name' not in session:
        return redirect(url_for('coun_login'))
    
    counselor_id = session['counselor_id']
    feedbacks = Feedback.query.filter_by(counselor_id=counselor_id).all()

    ratings = db.session.query(
        Feedback.rating,
        func.count(Feedback.rating).label('count')
    ).filter_by(counselor_id=counselor_id).group_by(Feedback.rating).all()

    total_ratings = sum(r[1] for r in ratings)
    overall_rating = (
        sum(r[0] * r[1] for r in ratings) / total_ratings if total_ratings > 0 else 0
    )

    rating_distribution = {star: 0 for star in range(1,6)}
    for r in ratings:
        rating_distribution[r[0]] = r[1]
    
    return render_template('counselor/coun_feedback.html',active_page='coun_feedback',feedbacks=feedbacks,total_ratings=total_ratings,rating_distribution=rating_distribution,overall_rating=overall_rating)

@app.route('/coun_profile')
def coun_profile():
    if 'counselor_id' and 'counselor_name' not in session:
        return redirect(url_for('coun_login'))
    return render_template('counselor/coun_profile.html',active_page='coun_profile')


# =============================================================================================== #
# ------------------------------------Landing Page Panel----------------------------------------- #
# =============================================================================================== #

@app.route('/')
def home():
    return render_template('landing_page/landing_page.html')

@app.route('/about')
def about():
    return render_template('landing_page/about.html')

@app.route('/counselor')
def counselor():
    return render_template('landing_page/counselor.html')

@app.route('/student')
def student():
    return render_template('landing_page/student.html')

@app.route('/services')
def services():
    return render_template('landing_page/services.html')

@app.route('/faq')
def faq():
    return render_template('landing_page/faq.html')

@app.route('/contact')
def contact():
    return render_template('landing_page/contact.html')

@app.route('/meeting')
def meeting():
    return render_template('landing_page/meeting-card.html')

@app.route('/meeting-room')
def meeting_room():
    return render_template('landing_page/meeting.html')

@app.route('/meeting-join')
def meeting_join():
    return render_template('landing_page/meeting-join.html')

@app.route('/payment')
def payment_page():
    # Remove strict login check, but store login status
    is_logged_in = 'student_name' in session
    student_name = session.get('student_name', None)
    
    package = request.args.get('package', 'premium')
    cancelled = request.args.get('cancelled', 'false')
    error = request.args.get('error', 'false')
    
    # Package details for display
    package_details = {
        'basic': {
            'name': 'Basic Plan',
            'price': '$49/month',
            'features': [
                '1 Career Counseling Session',
                'Resume Review',
                'Access to Webinar Library',
                'Basic Resource Access'
            ]
        },
        'premium': {
            'name': 'Premium Plan',
            'price': '$99/month',
            'features': [
                '3 Career Counseling Sessions',
                'Resume & Cover Letter Review',
                'Access to All Webinars',
                'Full Resource Access',
                '1 Mock Interview',
                'Mentorship Matching'
            ]
        },
        'ultimate': {
            'name': 'Ultimate Plan',
            'price': '$149/month',
            'features': [
                'Unlimited Career Counseling',
                'Priority Resume & Cover Letter Review',
                'VIP Access to All Events',
                'Premium Resource Access',
                'Unlimited Mock Interviews',
                'Priority Mentorship Matching',
                'Mental Health Support Sessions'
            ]
        }
    }
    
    return render_template('student/payment.html', 
                          active_page='payment',
                          package=package,
                          package_details=package_details[package],
                          is_logged_in=is_logged_in,
                          student_name=student_name,
                          cancelled=cancelled,
                          error=error)

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        # Get the package from the form data
        package = request.form.get('package', 'premium')
        
        # Define package prices and details
        package_details = {
            'basic': {
                'name': 'Basic Plan',
                'price': 4900,  # $49.00
                'description': 'Basic career counseling services'
            },
            'premium': {
                'name': 'Premium Plan',
                'price': 9900,  # $99.00
                'description': 'Enhanced career counseling services'
            },
            'ultimate': {
                'name': 'Ultimate Plan',
                'price': 14900,  # $149.00
                'description': 'Comprehensive career counseling services'
            }
        }
        
        if package not in package_details:
            return "Invalid package selected", 400
        
        # Create Checkout Session - direct to payment without login check
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": package_details[package]['name'],
                            "description": package_details[package]['description']
                        },
                        "unit_amount": package_details[package]['price'],
                    },
                    "quantity": 1,
                },
            ],
            mode="payment",
            success_url=url_for('payment_success', _external=True) + "?session_id={CHECKOUT_SESSION_ID}&package=" + package,
            cancel_url=url_for('payment_failed', _external=True) + "?package=" + package + "&status=cancelled",
            metadata={
                'package': package
            }
        )
        
        # Record in database if user is logged in
        if 'student_name' in session:
            student = Student.query.filter_by(name=session.get('student_name')).first()
            if student:
                payment = Payment(
                    payment_intent_id=checkout_session.id,
                    amount=package_details[package]['price'],
                    currency='usd',
                    status='pending',
                    student_id=student.id,
                    payment_metadata={"package": package}
                )
                db.session.add(payment)
                db.session.commit()
        
        # Redirect to Stripe Checkout
        return redirect(checkout_session.url)
    
    except Exception as e:
        print(f"Error creating checkout session: {str(e)}")
        return redirect(url_for('payment_failed') + "?package=" + package + "&status=error")

@app.route('/payment_success')
def payment_success():
    session_id = request.args.get('session_id')
    package = request.args.get('package', 'premium')
    
    if not session_id:
        return redirect(url_for('services'))
    
    try:
        # Retrieve the session
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        
        # Update payment status in database if user is logged in
        if 'student_name' in session:
            payment = Payment.query.filter_by(payment_intent_id=session_id).first()
            if payment:
                payment.status = 'completed'
                db.session.commit()
        
        return render_template('student/payment_success.html', 
                              package=package,
                              session_id=session_id)
    
    except Exception as e:
        print(f"Error retrieving checkout session: {str(e)}")
        return redirect(url_for('payment_failed') + f"?package={package}&status=error")

@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, "whsec_6CsI5M3qA9g5bK9YM1Eq9ctXvKLwnVQz"
        )
    except ValueError as e:
        # Invalid payload
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return jsonify({'error': 'Invalid signature'}), 400

    # Handle the events
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        print(f"PaymentIntent {payment_intent['id']} succeeded")
        
        # Find the payment record in our database
        payment = Payment.query.filter_by(payment_intent_id=payment_intent['id']).first()
        if payment:
            payment.status = 'completed'
            db.session.commit()

            # Send confirmation email to customer
            try:
                student = Student.query.get(payment.student_id)
                if student and student.email:
                    msg = Message(
                        'Payment Confirmation - Career Navigator',
                        sender=app.config['MAIL_USERNAME'],
                        recipients=[student.email]
                    )
                    
                    # Get package information from metadata
                    package = "premium"
                    if payment.payment_metadata and isinstance(payment.payment_metadata, dict):
                        package = payment.payment_metadata.get('package', 'premium')
                    
                    msg.body = f"""
                    Dear {student.name},

                    Thank you for subscribing to our {package.title()} plan!

                    Your payment of ${payment.amount/100:.2f} has been successfully processed.
                    
                    Transaction ID: {payment_intent['id']}

                    Best regards,
                    Career Navigator Team
                    """
                    mail.send(msg)
            except Exception as e:
                print(f"Error sending confirmation email: {str(e)}")

    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        error_message = payment_intent['last_payment_error']['message'] if payment_intent.get('last_payment_error') else None
        print(f"Payment failed: {payment_intent['id']}, {error_message}")
        
        # Update payment status in database
        payment = Payment.query.filter_by(payment_intent_id=payment_intent['id']).first()
        if payment:
            payment.status = 'failed'
            db.session.commit()

    return jsonify({'status': 'success'})

# @app.route('/test_razorpay')
# def test_razorpay():
#     try:
#         # Test API call
#         razorpay_client.payment.all()
#         return jsonify({'status': 'success', 'message': 'Razorpay connection successful'})
#     except Exception as e:
#         return jsonify({'status': 'error', 'message': str(e)})

@app.route('/payment_failed')
def payment_failed():
    # Remove login check to prevent redirection
    # if 'student_name' not in session:
    #     return redirect(url_for('student_login'))
    
    package = request.args.get('package', 'premium')
    status = request.args.get('status', 'failed')
    error = request.args.get('error', 'false')
    
    return render_template('student/payment_failed.html', 
                          package=package,
                          status=status,
                          error=error)




if __name__ == '__main__':
    app.run(debug=True)
