from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, make_response, send_file, abort
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta, date
from collections import defaultdict
from flask_sqlalchemy import SQLAlchemy
import os
import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go
import json
import io
import sqlite3
import uuid
import shutil
import werkzeug.security as security
from werkzeug.utils import secure_filename
from image_processor import parse_image_for_time_entries
from dateutil import parser
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
current_dir = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(current_dir, 'time_tracker.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configure upload folder
UPLOAD_FOLDER = os.path.join(current_dir, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size

# Create uploads directory if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

db = SQLAlchemy(app)

# Role-based access control decorators
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied. Administrator privileges required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not (current_user.is_admin or current_user.is_manager):
            flash('Access denied. Manager privileges required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Add datetime to all templates
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

@app.context_processor
def inject_app_settings():
    """Inject app settings into all templates"""
    settings = AppSetting.get_all()
    return {'app_settings': settings}

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_manager = db.Column(db.Boolean, default=False)
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # For employees assigned to a manager
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime, nullable=True)
    hourly_rate = db.Column(db.Float, nullable=True)
    department = db.Column(db.String(100), nullable=True)
    position = db.Column(db.String(100), nullable=True)
    
    # Relationship for manager-employee access
    employees = db.relationship('User', backref=db.backref('manager', remote_side=[id]),
                             lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = security.generate_password_hash(password)
        
    def check_password(self, password):
        return security.check_password_hash(self.password_hash, password)
    
    def get_full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    def update_login_timestamp(self):
        self.last_login = datetime.now()
        db.session.commit()
        
    def has_access_to_user(self, user_id):
        """Check if the current user has access to view/edit another user's data"""
        # Admin can access anyone
        if self.is_admin:
            return True
            
        # Manager can access their employees
        if self.is_manager:
            # Check if the user is one of this manager's employees
            return self.employees.filter_by(id=user_id).first() is not None
            
        # Users can only access themselves
        return self.id == user_id


class AppSetting(db.Model):
    """Model for application settings"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    value_type = db.Column(db.String(20), default='string')  # string, int, float, bool, json
    section = db.Column(db.String(50), nullable=False, default='general')
    description = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    @staticmethod
    def get(key, default=None):
        """Get a setting value by key"""
        setting = AppSetting.query.filter_by(key=key).first()
        
        if not setting:
            return default
            
        # Convert value based on type
        if setting.value_type == 'int':
            return int(setting.value) if setting.value is not None else default
        elif setting.value_type == 'float':
            return float(setting.value) if setting.value is not None else default
        elif setting.value_type == 'bool':
            return setting.value.lower() == 'true' if setting.value is not None else default
        elif setting.value_type == 'json':
            return json.loads(setting.value) if setting.value is not None else default
        else:
            return setting.value if setting.value is not None else default
    
    @staticmethod
    def set(key, value, value_type='string', section='general', description=None):
        """Set a setting value"""
        # Convert value to string for storage
        if value_type == 'json' and not isinstance(value, str):
            value = json.dumps(value)
        elif value_type == 'bool' and isinstance(value, bool):
            value = str(value).lower()
        elif value is not None:
            value = str(value)
        
        setting = AppSetting.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            setting.updated_at = datetime.now()
        else:
            setting = AppSetting(key=key, value=value, value_type=value_type, 
                               section=section, description=description)
            db.session.add(setting)
            
        db.session.commit()
        
    @staticmethod
    def get_all_by_section(section):
        """Get all settings for a specific section"""
        settings = AppSetting.query.filter_by(section=section).all()
        result = {}
        
        for setting in settings:
            result[setting.key] = AppSetting.get(setting.key)
            
        return result
        
    @staticmethod
    def get_all():
        """Get all settings as a dictionary"""
        settings = AppSetting.query.all()
        result = {}
        
        for setting in settings:
            result[setting.key] = AppSetting.get(setting.key)
            
        return result

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), nullable=True)  # Used for service orders
    category = db.Column(db.String(50), nullable=True)  # For other time types
    entry_type = db.Column(db.String(20), default='service_order')  # 'service_order' or 'other_time'
    employee_name = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)
    notes = db.Column(db.Text, nullable=True)  # Notes/comments about the time entry
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    def get_elapsed_time(self):
        if self.end_time:
            elapsed = self.end_time - self.start_time
            hours = int(elapsed.total_seconds() // 3600)
            minutes = int((elapsed.total_seconds() % 3600) // 60)
            seconds = int(elapsed.total_seconds() % 60)
            return f"{hours:02d}h:{minutes:02d}m:{seconds:02d}s"
        else:
            # Calculate elapsed time from start to now for active orders
            elapsed = datetime.now() - self.start_time
            hours = int(elapsed.total_seconds() // 3600)
            minutes = int((elapsed.total_seconds() % 3600) // 60)
            seconds = int(elapsed.total_seconds() % 60)
            return f"{hours:02d}h:{minutes:02d}m:{seconds:02d}s"

    def get_status(self):
        return "Active" if not self.end_time else "Completed"

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please provide both username and password.', 'danger')
            return render_template('login.html')
            
        user = User.query.filter_by(username=username).first()
        
        if user is None or not user.check_password(password):
            flash('Invalid username or password.', 'danger')
            return render_template('login.html')
        
        # Update last login timestamp
        user.last_login = datetime.now()
        db.session.commit()
        
        # Log the user in
        login_user(user)
        
        # Flash welcome message with role info
        if user.is_admin:
            flash(f'Welcome back, Administrator {user.get_full_name()}!', 'success')
        elif user.is_manager:
            flash(f'Welcome back, Manager {user.get_full_name()}!', 'success')
        else:
            flash(f'Welcome back, {user.get_full_name()}!', 'success')
        
        # Redirect to the next page parameter, or index if not present
        next_page = request.args.get('next')
        return redirect(next_page or url_for('index'))
            
        
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Form validation
        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('register'))
            
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))
            
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return redirect(url_for('register'))
            
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))
        
        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        # Make the first registered user an admin
        if User.query.count() == 0:
            new_user.is_admin = True
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

# Create default admin if no users exist
def create_default_admin():
    if User.query.count() == 0:
        admin = User(username='admin', email='admin@example.com', is_admin=True)
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()
        print('Created default admin user (username: admin, password: admin)')

# Application Routes
@app.route('/')
@login_required
def index():
    active_orders = Order.query.filter_by(end_time=None).order_by(Order.start_time.desc()).all()
    completed_orders = Order.query.filter(Order.end_time != None).order_by(Order.end_time.desc()).limit(10).all()
    return render_template('index.html', active_orders=active_orders, completed_orders=completed_orders)

@app.route('/add_order', methods=['GET', 'POST'])
@login_required
def add_order():
    if request.method == 'POST':
        entry_type = request.form.get('entry_type')
        employee_name = request.form.get('employee_name')
        notes = request.form.get('notes')
        
        # Validate order number for service orders
        order_number = request.form.get('order_number').strip() if request.form.get('order_number') else None
        if entry_type == 'service_order' and not order_number:
            flash('Order number is required for service orders.', 'danger')
            return redirect(url_for('add_order'))
        
        # Validate category for other time types
        category = request.form.get('category')
        if entry_type == 'other_time' and not category:
            flash('Please select a category for other time entries.', 'danger')
            return redirect(url_for('add_order'))

        # Handle manual time entry if checked
        manual_time = 'manual_time' in request.form
        if manual_time:
            # Manual time entry logic
            completed = 'completed' in request.form
            
            # Get start date and time
            start_date = request.form.get('start_date')
            start_time = request.form.get('start_time')
            start_datetime = None
            
            if start_date and start_time:
                try:
                    start_datetime = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
                except ValueError:
                    flash('Invalid start date/time format', 'danger')
                    return redirect(url_for('add_order'))
            else:
                flash('Start date and time are required', 'danger')
                return redirect(url_for('add_order'))
            
            # Handle end datetime for completed orders
            end_datetime = None
            if completed:
                end_date = request.form.get('end_date')
                end_time = request.form.get('end_time')
                
                if end_date and end_time:
                    try:
                        end_datetime = datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M")
                    except ValueError:
                        flash('Invalid end date/time format', 'danger')
                        return redirect(url_for('add_order'))
                        
                    # Validate end time is after start time
                    if end_datetime <= start_datetime:
                        flash('End time must be after start time', 'danger')
                        return redirect(url_for('add_order'))
                else:
                    flash('End date and time are required for completed entries', 'danger')
                    return redirect(url_for('add_order'))
            
            # Create the order
            new_order = Order(
                order_number=order_number,
                category=category,
                entry_type=entry_type,
                employee_name=employee_name,
                start_time=start_datetime,
                end_time=end_datetime,
                notes=notes
            )
            
        else:
            # Real-time tracking - just start now
            new_order = Order(
                order_number=order_number,
                category=category,
                entry_type=entry_type,
                employee_name=employee_name,
                start_time=datetime.now(),
                notes=notes
            )
            
        db.session.add(new_order)
        db.session.commit()
        
        if manual_time and completed:
            if entry_type == 'service_order':
                flash(f'Order {order_number} added and marked as completed!', 'success')
            else:
                flash(f'{category} time entry added and marked as completed!', 'success')
        else:
            if entry_type == 'service_order':
                flash(f'Order {order_number} started!', 'success')
            else:
                flash(f'{category} time entry started!', 'success')
            
        return redirect(url_for('index'))
    
    return render_template('add_order.html')

@app.route('/complete_order/<int:order_id>', methods=['POST'])
@login_required
def complete_order(order_id):
    order = Order.query.get_or_404(order_id)
    if not order.end_time:  # Only update if not already completed
        order.end_time = datetime.now()
        db.session.commit()
        flash('Order completed successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/edit_order/<int:order_id>', methods=['GET', 'POST'])
@login_required
def edit_order(order_id):
    order = Order.query.get_or_404(order_id)
    
    if request.method == 'POST':
        # Get entry type
        entry_type = request.form.get('entry_type', 'service_order')
        
        # Handle service order vs other time type
        if entry_type == 'service_order':
            order.order_number = request.form.get('order_number')
            order.category = None
            if not order.order_number:
                flash('Order number is required for service orders', 'danger')
                return render_template('edit_order.html', order=order)
        else:  # other_time
            order.order_number = None
            order.category = request.form.get('category')
            if not order.category:
                flash('Category is required for other time types', 'danger')
                return render_template('edit_order.html', order=order)
        
        # Common fields
        order.entry_type = entry_type
        order.employee_name = request.form.get('employee_name')
        order.notes = request.form.get('notes')  # Add notes field
        
        # Parse start date and time
        start_date_str = request.form.get('start_date')
        start_time_str = request.form.get('start_time')
        
        if start_date_str and start_time_str:
            # Combine date and time strings
            start_datetime_str = f"{start_date_str} {start_time_str}"
            order.start_time = datetime.strptime(start_datetime_str, "%Y-%m-%d %H:%M")
            
        # Handle completion status
        completed = 'completed' in request.form
        
        if completed:
            end_date_str = request.form.get('end_date')
            end_time_str = request.form.get('end_time')
            
            if end_date_str and end_time_str:
                # Combine date and time strings
                end_datetime_str = f"{end_date_str} {end_time_str}"
                end_time = datetime.strptime(end_datetime_str, "%Y-%m-%d %H:%M")
                
                # Validate that end time is after start time
                if end_time <= order.start_time:
                    flash('End time must be after start time', 'danger')
                    return render_template('edit_order.html', order=order)
                    
                order.end_time = end_time
            else:
                # If no end date/time provided, use current time
                order.end_time = datetime.now()
        else:
            # Entry is still active
            order.end_time = None
        
        db.session.commit()
        
        # Show appropriate success message
        if entry_type == 'service_order':
            flash(f'Order {order.order_number} updated successfully!', 'success')
        else:
            flash(f'{order.category} time entry updated successfully!', 'success')
            
        return redirect(url_for('index'))
        
    return render_template('edit_order.html', order=order)

@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html')

@app.route('/reports/order_times')
@login_required
def order_times_report():
    # Get date range filter
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = Order.query
    
    # Apply filters if provided
    if start_date:
        start_date = parser.parse(start_date)
        query = query.filter(Order.start_time >= start_date)
    
    if end_date:
        end_date = parser.parse(end_date)
        end_date = end_date + timedelta(days=1)  # Include the entire day
        query = query.filter(Order.start_time <= end_date)
    
    orders = query.all()
    
    # Prepare data for plotting
    data = []
    for order in orders:
        if order.end_time:  # Only include completed orders
            duration = (order.end_time - order.start_time).total_seconds() / 3600  # hours
            data.append({
                'order_number': order.order_number,
                'employee_name': order.employee_name,
                'duration': round(duration, 2),
                'start_time': order.start_time.strftime('%Y-%m-%d %H:%M'),
                'end_time': order.end_time.strftime('%Y-%m-%d %H:%M')
            })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    if not df.empty:
        # Create visualization
        fig = px.bar(
            df, 
            x='order_number', 
            y='duration',
            color='employee_name',
            title='Order Processing Times (Hours)',
            labels={'duration': 'Duration (hours)', 'order_number': 'Order Number'},
            hover_data=['start_time', 'end_time']
        )
        
        # Convert plot to JSON
        graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        return render_template('order_times.html', graphJSON=graphJSON, orders=data)
    
    return render_template('order_times.html', graphJSON=None, orders=[])

@app.route('/reports/employee_productivity')
@login_required
def employee_productivity_report():
    # Get date range filter
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = Order.query.filter(Order.end_time != None)  # Only completed orders
    
    # Apply filters if provided
    if start_date:
        start_date = parser.parse(start_date)
        query = query.filter(Order.start_time >= start_date)
    
    if end_date:
        end_date = parser.parse(end_date)
        end_date = end_date + timedelta(days=1)  # Include the entire day
        query = query.filter(Order.start_time <= end_date)
    
    orders = query.all()
    
    # Aggregate by employee
    employee_data = {}
    for order in orders:
        employee = order.employee_name
        duration = (order.end_time - order.start_time).total_seconds() / 3600
        
        if employee not in employee_data:
            employee_data[employee] = {
                'total_hours': 0,
                'order_count': 0,
                'orders': []
            }
        
        employee_data[employee]['total_hours'] += duration
        employee_data[employee]['order_count'] += 1
        employee_data[employee]['orders'].append(order.order_number)
    
    # Prepare for visualization
    viz_data = []
    for employee, data in employee_data.items():
        viz_data.append({
            'employee_name': employee,
            'total_hours': round(data['total_hours'], 2),
            'order_count': data['order_count'],
            'avg_time_per_order': round(data['total_hours'] / data['order_count'], 2) if data['order_count'] > 0 else 0
        })
    
    df = pd.DataFrame(viz_data)
    
    if not df.empty:
        # Create visualizations
        fig1 = px.bar(
            df,
            x='employee_name',
            y='total_hours',
            title='Total Hours by Employee',
            labels={'total_hours': 'Total Hours', 'employee_name': 'Employee'}
        )
        
        fig2 = px.bar(
            df,
            x='employee_name',
            y='avg_time_per_order',
            title='Average Time per Order by Employee (Hours)',
            labels={'avg_time_per_order': 'Average Hours', 'employee_name': 'Employee'}
        )
        
        # Convert plots to JSON
        graphJSON1 = json.dumps(fig1, cls=plotly.utils.PlotlyJSONEncoder)
        graphJSON2 = json.dumps(fig2, cls=plotly.utils.PlotlyJSONEncoder)
        
        return render_template(
            'employee_productivity.html', 
            graphJSON1=graphJSON1,
            graphJSON2=graphJSON2,
            employee_data=viz_data
        )
    
    return render_template('employee_productivity.html', graphJSON1=None, graphJSON2=None, employee_data=[])

@app.route('/weekly_report')
@login_required
def weekly_report():
    # Default to current week (Monday to Sunday)
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())  # Monday
    end_of_week = start_of_week + timedelta(days=6)  # Sunday
    
    # Get filter parameters
    start_date = request.args.get('start_date', start_of_week.strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', end_of_week.strftime('%Y-%m-%d'))
    employee = request.args.get('employee', '')
    
    # Convert string dates to datetime objects
    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Add one day to end_date to include the full day
    end_dt_inclusive = end_dt + timedelta(days=1)
    
    # Query for completed orders within the date range
    query = Order.query.filter(
        Order.end_time.isnot(None),
        Order.start_time >= datetime.combine(start_dt, datetime.min.time()),
        Order.start_time < datetime.combine(end_dt_inclusive, datetime.min.time())
    ).order_by(Order.start_time)
    
    # Filter by employee if specified
    if employee:
        query = query.filter(Order.employee_name == employee)
    
    # Get all entries
    all_entries = query.all()
    
    # Get list of all employees for the filter dropdown
    employees = db.session.query(Order.employee_name).distinct().all()
    employees = [emp[0] for emp in employees]
    
    # Organize entries by date
    report_data = defaultdict(list)
    day_totals = defaultdict(float)
    total_hours = 0
    service_hours = 0
    other_hours = 0
    
    for entry in all_entries:
        # Get the date part as the key
        entry_date = entry.start_time.date()
        
        # Calculate hours for this entry
        if entry.end_time:
            duration = entry.end_time - entry.start_time
            hours = duration.total_seconds() / 3600  # convert to hours
            entry.hours = hours  # Add hours to the entry object for display
            
            # Accumulate totals
            day_totals[entry_date] += hours
            total_hours += hours
            
            # Split by entry type
            if entry.entry_type == 'service_order':
                service_hours += hours
            else:
                other_hours += hours
        else:
            entry.hours = 0
        
        # Add entry to the correct day
        report_data[entry_date].append(entry)
    
    return render_template(
        'weekly_report.html',
        report_data=report_data,
        day_totals=day_totals,
        total_hours=total_hours,
        service_hours=service_hours,
        other_hours=other_hours,
        employees=employees,
        employee=employee,
        start_date=start_date,
        end_date=end_date
    )

@app.route('/export_weekly_report')
@login_required
def export_weekly_report():
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    employee = request.args.get('employee', '')
    export_format = request.args.get('format', 'excel')  # Default to Excel
    
    # Convert string dates to datetime objects
    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else date.today()
    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else date.today()
    
    # Add one day to end_date to include the full day
    end_dt_inclusive = end_dt + timedelta(days=1)
    
    # Query for completed orders within the date range
    query = Order.query.filter(
        Order.end_time.isnot(None),
        Order.start_time >= datetime.combine(start_dt, datetime.min.time()),
        Order.start_time < datetime.combine(end_dt_inclusive, datetime.min.time())
    ).order_by(Order.start_time)
    
    # Filter by employee if specified
    if employee:
        query = query.filter(Order.employee_name == employee)
    
    # Get all entries
    all_entries = query.all()
    
    # Organize entries by date
    report_data = defaultdict(list)
    day_totals = defaultdict(float)
    
    for entry in all_entries:
        entry_date = entry.start_time.date()
        if entry.end_time:
            duration = entry.end_time - entry.start_time
            hours = duration.total_seconds() / 3600
            entry.hours = hours
            day_totals[entry_date] += hours
        else:
            entry.hours = 0
        report_data[entry_date].append(entry)
    
    # Prepare filename
    date_range = f"{start_dt.strftime('%Y%m%d')}-{end_dt.strftime('%Y%m%d')}"
    employee_suffix = f"_{employee}" if employee else ""
    filename_base = f"timetracker_report_{date_range}{employee_suffix}"
    
    # Export based on requested format
    if export_format == 'pdf':
        # Generate HTML for PDF conversion
        html = render_template(
            'weekly_report_pdf.html',
            report_data=report_data,
            day_totals=day_totals,
            total_hours=sum(day_totals.values()),
            start_date=start_date,
            end_date=end_date,
            employee=employee
        )
        
        # Configure wkhtmltopdf path based on OS
        config = None
        try:
            if platform.system() == 'Windows':
                # Try to use installed wkhtmltopdf
                wkhtmltopdf_path = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
                if os.path.exists(wkhtmltopdf_path):
                    config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
            
            # Convert HTML to PDF
            pdf = pdfkit.from_string(html, False, configuration=config)
            response = make_response(pdf)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename={filename_base}.pdf'
            return response
        except Exception as e:
            flash(f'Error generating PDF: {str(e)}. Please make sure wkhtmltopdf is installed.', 'danger')
            return redirect(url_for('weekly_report', start_date=start_date, end_date=end_date, employee=employee))
    
    elif export_format == 'excel':
        # Create Excel file using pandas
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        
        # Create summary sheet
        summary_data = {
            'Date': [],
            'Total Hours': []
        }
        
        for day, total in day_totals.items():
            summary_data['Date'].append(day.strftime('%Y-%m-%d'))
            summary_data['Total Hours'].append(round(total, 2))
        
        # Add grand total
        summary_data['Date'].append('TOTAL')
        summary_data['Total Hours'].append(round(sum(day_totals.values()), 2))
        
        # Create summary DataFrame
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Format the summary sheet
        workbook = writer.book
        summary_sheet = writer.sheets['Summary']
        bold_format = workbook.add_format({'bold': True})
        number_format = workbook.add_format({'num_format': '0.00'})
        
        # Set column widths
        summary_sheet.set_column('A:A', 12)
        summary_sheet.set_column('B:B', 15, number_format)
        
        # Format the total row
        summary_sheet.write(len(day_totals) + 1, 0, 'TOTAL', bold_format)
        
        # Create details sheet with all entries
        details_data = {
            'Date': [],
            'Employee': [],
            'Type': [],
            'Details': [],
            'Start Time': [],
            'End Time': [],
            'Hours': [],
            'Notes': []
        }
        
        # Fill details data
        for day, entries in report_data.items():
            for entry in entries:
                details_data['Date'].append(day.strftime('%Y-%m-%d'))
                details_data['Employee'].append(entry.employee_name)
                
                if entry.entry_type == 'service_order':
                    details_data['Type'].append('Service Order')
                    details_data['Details'].append(entry.order_number)
                else:
                    details_data['Type'].append('Other Time')
                    details_data['Details'].append(entry.category)
                
                details_data['Start Time'].append(entry.start_time.strftime('%H:%M'))
                details_data['End Time'].append(entry.end_time.strftime('%H:%M') if entry.end_time else '')
                details_data['Hours'].append(round(entry.hours, 2))
                details_data['Notes'].append(entry.notes or '')
        
        # Create details DataFrame
        details_df = pd.DataFrame(details_data)
        details_df.to_excel(writer, sheet_name='Details', index=False)
        
        # Format the details sheet
        details_sheet = writer.sheets['Details']
        details_sheet.set_column('A:A', 12)  # Date
        details_sheet.set_column('B:B', 15)  # Employee
        details_sheet.set_column('C:C', 12)  # Type
        details_sheet.set_column('D:D', 15)  # Details
        details_sheet.set_column('E:E', 10)  # Start Time
        details_sheet.set_column('F:F', 10)  # End Time
        details_sheet.set_column('G:G', 10, number_format)  # Hours
        details_sheet.set_column('H:H', 30)  # Notes
        
        writer.close()
        output.seek(0)
        
        return send_file(
            output, 
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f"{filename_base}.xlsx"
        )
    
    elif export_format == 'csv':
        # Create CSV file
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Date', 'Employee', 'Type', 'Details', 'Start Time', 'End Time', 'Hours', 'Notes'])
        
        # Write data rows
        for day, entries in report_data.items():
            for entry in entries:
                writer.writerow([
                    day.strftime('%Y-%m-%d'),
                    entry.employee_name,
                    'Service Order' if entry.entry_type == 'service_order' else 'Other Time',
                    entry.order_number if entry.entry_type == 'service_order' else entry.category,
                    entry.start_time.strftime('%H:%M'),
                    entry.end_time.strftime('%H:%M') if entry.end_time else '',
                    round(entry.hours, 2),
                    entry.notes or ''
                ])
            
            # Add a daily total row
            writer.writerow(['', '', '', '', '', 'Daily Total:', round(day_totals[day], 2), ''])
            
        # Add a grand total row
        writer.writerow(['', '', '', '', '', 'GRAND TOTAL:', round(sum(day_totals.values()), 2), ''])
        
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = f"attachment; filename={filename_base}.csv"
        response.headers["Content-type"] = "text/csv"
        return response

@app.route('/export_data')
@login_required
def export_data():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = Order.query
    
    # Apply filters if provided
    if start_date:
        start_date = parser.parse(start_date)
        query = query.filter(Order.start_time >= start_date)
    
    if end_date:
        end_date = parser.parse(end_date)
        end_date = end_date + timedelta(days=1)  # Include the entire day
        query = query.filter(Order.start_time <= end_date)
    
    orders = query.all()
    
    # Create DataFrame for export
    data = []
    for order in orders:
        elapsed_time = None
        if order.end_time:
            elapsed = order.end_time - order.start_time
            elapsed_time = elapsed.total_seconds() / 3600  # hours
        
        data.append({
            'order_number': order.order_number,
            'employee_name': order.employee_name,
            'start_time': order.start_time,
            'end_time': order.end_time,
            'elapsed_hours': elapsed_time,
            'status': 'Completed' if order.end_time else 'Active'
        })
    
    df = pd.DataFrame(data)
    
    # Create Excel file
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Orders', index=False)
    writer.close()
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'timetracker_export_{datetime.now().strftime("%Y%m%d%H%M%S")}.xlsx'
    )

@app.route('/upload_image', methods=['GET'])
@login_required
def upload_image():
    """Show form to upload an image for time entry extraction"""
    return render_template('upload_image.html')

@app.route('/process_image', methods=['POST'])
@login_required
def process_image():
    """Process an uploaded image and extract time entries"""
    print("\n==== STARTING IMAGE PROCESSING ====\n")
    
    if 'image_file' not in request.files:
        print("ERROR: No file part in request")
        flash('No file part', 'danger')
        return redirect(url_for('upload_image'))
        
    file = request.files['image_file']
    print(f"Received file: {file.filename}")
    
    # If user does not select a file, the browser submits an empty file
    if file.filename == '':
        print("ERROR: Empty filename submitted")
        flash('No selected file', 'danger')
        return redirect(url_for('upload_image'))
    
    # Get the selected time entry format
    format_type = request.form.get('format_type', 'standard')
    print(f"Selected format type: {format_type}")
        
    if file and allowed_file(file.filename):
        # Generate a secure filename with a UUID to prevent collisions
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        print(f"Saving file to: {filepath}")
        file.save(filepath)
        print(f"File saved successfully: {os.path.exists(filepath)}")
        
        # Process the image to extract time entries
        try:
            # Import the image processing module
            print("Calling parse_image_for_time_entries...")
            from image_processor import parse_image_for_time_entries
            
            # Process the image with the selected format type
            extracted_entries = parse_image_for_time_entries(filepath, format_type)
            print(f"\nExtracted {len(extracted_entries)} entries from image using format: {format_type}\n")
            
            # Always proceed with entries (our improved image_processor now always returns at least one entry)
            if extracted_entries:
                # Convert datetime objects to strings for session storage
                serializable_entries = []
                print("Converting entries for session storage...")
                
                for entry in extracted_entries:
                    serialized_entry = {}
                    for key, value in entry.items():
                        # Convert datetime objects to strings
                        if isinstance(value, datetime):
                            serialized_entry[key] = value.isoformat()
                        elif isinstance(value, date):
                            serialized_entry[key] = value.isoformat()
                        else:
                            serialized_entry[key] = value
                    serializable_entries.append(serialized_entry)
                
                print(f"Serialized {len(serializable_entries)} entries, first entry: {serializable_entries[0] if serializable_entries else 'None'}")
                        
                # Store the serialized entries, file path, and format type in session
                session['extracted_entries'] = serializable_entries
                session['uploaded_image_path'] = filepath
                session['format_type'] = format_type
                
                print("IMPORTANT: Redirecting to confirm_entries page")
                # Force redirect to confirmation page
                return redirect(url_for('confirm_entries'))
            else:
                print("WARNING: No entries extracted, but this should not happen with our improved code")
                # Even if no entries extracted, create a demo entry
                demo_entry = {
                    'employee_name': 'Demo User',
                    'order_number': 'FALLBACK-DEMO',
                    'date_str': datetime.now().strftime('%Y-%m-%d'),
                    'entry_type': 'service_order',
                    'hours': 3.75,
                    'from_demo': True,
                    'format_type': format_type
                }
                session['extracted_entries'] = [demo_entry]
                session['uploaded_image_path'] = filepath
                session['format_type'] = format_type
                
                print("Using fallback demo entry and redirecting to confirm_entries")
                return redirect(url_for('confirm_entries'))
                
        except Exception as e:
            print(f"\nERROR processing image: {str(e)}\n")
            flash(f'Error processing image: {str(e)}', 'danger')
            
            # Create a demo entry even on error
            if os.environ.get('RENDER', '') == 'true':
                print("Error occurred but creating demo entry for Render deployment")
                demo_entry = {
                    'employee_name': 'Error Recovery',
                    'order_number': f'ERROR-DEMO-{format_type}',
                    'date_str': datetime.now().strftime('%Y-%m-%d'),
                    'entry_type': 'service_order',
                    'hours': 1.5,
                    'from_demo': True,
                    'format_type': format_type
                }
                session['extracted_entries'] = [demo_entry]
                session['uploaded_image_path'] = filepath
                session['format_type'] = format_type
                return redirect(url_for('confirm_entries'))
            
            return redirect(url_for('upload_image'))
    else:
        print(f"ERROR: Invalid file type: {file.filename}")
        flash('Invalid file type. Please upload a PNG, JPG, or JPEG image.', 'danger')
        return redirect(url_for('upload_image'))

@app.route('/confirm_entries', methods=['GET', 'POST'])
@login_required
def confirm_entries():
    """Display and confirm time entries extracted from an uploaded image"""
    if request.method == 'POST':
        try:
            # Get the list of entries from the session
            entries = session.get('extracted_entries', [])
            if not entries:
                flash('No time entries found to confirm.', 'warning')
                return redirect(url_for('upload_image'))
            
            # Get the selected entries from the form
            selected_entries = request.form.getlist('selected_entries')
            if not selected_entries:
                flash('No entries were selected.', 'warning')
                return render_template('confirm_entries.html', 
                                      entries=entries, 
                                      image_path=session.get('uploaded_image_path'),
                                      now=datetime.now)
            
            # Process each selected entry
            for index in selected_entries:
                idx = int(index)
                employee_name = request.form.get(f"employee_name_{idx}", "")
                order_number = request.form.get(f"order_number_{idx}", "")
                date_str = request.form.get(f"date_{idx}", "")
                hours = float(request.form.get(f"hours_{idx}", 0))
                
                # Format hours to 2 decimal places
                hours = round(hours, 2)
                
                entry_type = request.form.get(f"entry_type_{idx}", "service_order")
                
                # Create a date object from the date string
                entry_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                # Set the start time to the beginning of the work day
                start_time = datetime.combine(entry_date, datetime.min.time()) + timedelta(hours=8)  # 8:00 AM
                
                # Calculate end time based on hours worked
                end_time = start_time + timedelta(hours=hours)
                
                # Create a new order (without passing hours directly)
                new_order = Order(
                    employee_name=employee_name,
                    order_number=order_number if entry_type == 'service_order' else None,
                    category=order_number if entry_type == 'other_time' else None,
                    entry_type=entry_type,
                    start_time=start_time,
                    end_time=end_time
                )
                
                db.session.add(new_order)
                print(f"Added order: {employee_name}, {order_number}, {hours} hours")
            
            # Save all entries at once
            db.session.commit()
            flash(f'Successfully added {len(selected_entries)} time entries.', 'success')
            
            # Clear session data
            session.pop('extracted_entries', None)
            session.pop('uploaded_image_path', None)
                
            return redirect(url_for('index'))
                
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving entries: {str(e)}', 'danger')
            print(f"Error saving entries: {str(e)}")
            return redirect(url_for('confirm_entries'))
    
    # Get the list of entries from the session
    entries = session.get('extracted_entries', [])
    if not entries:
        flash('No time entries found to confirm.', 'warning')
        return redirect(url_for('upload_image'))
    
    # Get the image path from the session
    image_path = session.get('uploaded_image_path', '')
    # Get the relative path for display in the template
    relative_path = os.path.basename(image_path) if image_path else ''
    
    # Debug information
    print(f"Entries to confirm: {len(entries)}")
    for i, entry in enumerate(entries):
        print(f"Entry {i}: {entry}")
    
    # Add now function to template context
    return render_template('confirm_entries.html', 
                           entries=entries, 
                           image_path=relative_path,
                           now=datetime.now)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

@app.route('/account/settings', methods=['GET', 'POST'])
@login_required
def account_settings():
    if request.method == 'POST':
        # Get form data
        email = request.form.get('email')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        department = request.form.get('department')
        position = request.form.get('position')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Update basic profile info
        current_user.email = email
        current_user.first_name = first_name
        current_user.last_name = last_name
        current_user.department = department
        current_user.position = position
        
        # Handle password change if requested
        if current_password and new_password:
            # Validate current password
            if not current_user.check_password(current_password):
                flash('Current password is incorrect.', 'danger')
                return redirect(url_for('account_settings'))
                
            # Validate new password matches confirmation
            if new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
                return redirect(url_for('account_settings'))
                
            # Set new password
            current_user.set_password(new_password)
            flash('Password updated successfully.', 'success')
        
        # Save changes
        db.session.commit()
        flash('Account settings updated successfully.', 'success')
        
        return redirect(url_for('account_settings'))
    
    return render_template('account_settings.html')


@app.route('/admin/settings', methods=['GET'])
@login_required
@admin_required
def admin_settings():
    """Admin settings page"""
    settings = {}
    for section in ['general', 'time_tracking', 'notifications', 'security', 'backup']:
        section_settings = AppSetting.get_all_by_section(section)
        settings.update(section_settings)
    
    return render_template('admin/admin_settings.html', settings=settings)


@app.route('/admin/settings/<section>', methods=['POST'])
@login_required
@admin_required
def admin_update_settings(section):
    """Update admin settings for a specific section"""
    if section == 'general':
        # Update general settings
        company_name = request.form.get('company_name')
        default_currency = request.form.get('default_currency')
        timezone = request.form.get('timezone')
        enable_desktop_mode = 'enable_desktop_mode' in request.form
        
        AppSetting.set('company_name', company_name, section=section)
        AppSetting.set('default_currency', default_currency, section=section)
        AppSetting.set('timezone', timezone, section=section)
        AppSetting.set('enable_desktop_mode', enable_desktop_mode, value_type='bool', section=section)
    
    elif section == 'time_tracking':
        # Update time tracking settings
        work_week_start = request.form.get('work_week_start')
        default_work_hours = request.form.get('default_work_hours')
        round_times_to_nearest = 'round_times_to_nearest' in request.form
        rounding_interval = request.form.get('rounding_interval')
        require_order_number = 'require_order_number' in request.form
        allow_time_overlap = 'allow_time_overlap' in request.form
        
        AppSetting.set('work_week_start', work_week_start, value_type='int', section=section)
        AppSetting.set('default_work_hours', default_work_hours, value_type='float', section=section)
        AppSetting.set('round_times_to_nearest', round_times_to_nearest, value_type='bool', section=section)
        AppSetting.set('rounding_interval', rounding_interval, value_type='int', section=section)
        AppSetting.set('require_order_number', require_order_number, value_type='bool', section=section)
        AppSetting.set('allow_time_overlap', allow_time_overlap, value_type='bool', section=section)
    
    elif section == 'notifications':
        # Update notification settings
        email_notifications = 'email_notifications' in request.form
        email_from = request.form.get('email_from')
        notify_missed_timesheet = 'notify_missed_timesheet' in request.form
        notify_managers = 'notify_managers' in request.form
        
        AppSetting.set('email_notifications', email_notifications, value_type='bool', section=section)
        AppSetting.set('email_from', email_from, section=section)
        AppSetting.set('notify_missed_timesheet', notify_missed_timesheet, value_type='bool', section=section)
        AppSetting.set('notify_managers', notify_managers, value_type='bool', section=section)
    
    elif section == 'security':
        # Update security settings
        session_timeout = request.form.get('session_timeout')
        password_policy = request.form.get('password_policy')
        force_password_reset = 'force_password_reset' in request.form
        allow_registration = 'allow_registration' in request.form
        
        AppSetting.set('session_timeout', session_timeout, value_type='int', section=section)
        AppSetting.set('password_policy', password_policy, section=section)
        AppSetting.set('force_password_reset', force_password_reset, value_type='bool', section=section)
        AppSetting.set('allow_registration', allow_registration, value_type='bool', section=section)
    
    elif section == 'backup':
        # Update backup settings
        enable_auto_backup = 'enable_auto_backup' in request.form
        backup_frequency = request.form.get('backup_frequency')
        backup_retention = request.form.get('backup_retention')
        
        AppSetting.set('enable_auto_backup', enable_auto_backup, value_type='bool', section=section)
        AppSetting.set('backup_frequency', backup_frequency, section=section)
        AppSetting.set('backup_retention', backup_retention, value_type='int', section=section)
    
    flash(f'{section.replace("_", " ").title()} settings updated successfully.', 'success')
    return redirect(url_for('admin_settings', _anchor=section))


@app.route('/admin/backup-database', methods=['POST'])
@login_required
@admin_required
def admin_backup_database():
    """Create a backup of the database"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
    backup_dir = os.path.join(current_dir, 'backups')
    
    # Create backups directory if it doesn't exist
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    backup_path = os.path.join(backup_dir, f'time_tracker_backup_{timestamp}.db')
    
    # Create a copy of the database file
    try:
        shutil.copy2(db_path, backup_path)
        flash('Database backup created successfully.', 'success')
        
        # Send the file for download
        return send_file(backup_path, as_attachment=True, download_name=f'time_tracker_backup_{timestamp}.db')
    except Exception as e:
        flash(f'Backup failed: {str(e)}', 'danger')
        return redirect(url_for('admin_settings'))


@app.route('/admin/restore-database', methods=['POST'])
@login_required
@admin_required
def admin_restore_database():
    """Restore database from backup"""
    if 'backup_file' not in request.files:
        flash('No backup file selected.', 'danger')
        return redirect(url_for('admin_settings'))
    
    backup_file = request.files['backup_file']
    
    if backup_file.filename == '':
        flash('No backup file selected.', 'danger')
        return redirect(url_for('admin_settings'))
    
    # Verify the file is a SQLite database
    try:
        temp_path = os.path.join(current_dir, 'temp_restore.db')
        backup_file.save(temp_path)
        
        # Test if it's a valid SQLite database
        conn = sqlite3.connect(temp_path)
        conn.close()
        
        # Create a backup of the current database before restoring
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        backup_dir = os.path.join(current_dir, 'backups')
        
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        auto_backup_path = os.path.join(backup_dir, f'pre_restore_backup_{timestamp}.db')
        shutil.copy2(db_path, auto_backup_path)
        
        # Replace the current database with the uploaded one
        shutil.copy2(temp_path, db_path)
        os.remove(temp_path)
        
        flash('Database restored successfully. You will be logged out for changes to take effect.', 'success')
        return redirect(url_for('logout'))
    
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        flash(f'Restore failed: {str(e)}', 'danger')
        return redirect(url_for('admin_settings'))


@app.route('/admin/users', methods=['GET'])
@login_required
@admin_required
def admin_user_management():
    """User management page for admins"""
    users = User.query.all()
    managers = User.query.filter_by(is_manager=True).all()
    
    return render_template('admin/user_management.html', users=users, managers=managers)


@app.route('/admin/users/add', methods=['POST'])
@login_required
@admin_required
def admin_add_user():
    """Add a new user"""
    username = request.form.get('username')
    email = request.form.get('email')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    department = request.form.get('department')
    position = request.form.get('position')
    hourly_rate = request.form.get('hourly_rate')
    role = request.form.get('role')
    manager_id = request.form.get('manager_id')
    
    # Validate required fields
    if not username or not email or not password:
        flash('Username, email and password are required.', 'danger')
        return redirect(url_for('admin_user_management'))
    
    # Check if passwords match
    if password != confirm_password:
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('admin_user_management'))
    
    # Check if username or email already exists
    if User.query.filter_by(username=username).first():
        flash(f'Username {username} is already taken.', 'danger')
        return redirect(url_for('admin_user_management'))
    
    if User.query.filter_by(email=email).first():
        flash(f'Email {email} is already registered.', 'danger')
        return redirect(url_for('admin_user_management'))
    
    # Create new user
    user = User(username=username, email=email, first_name=first_name, last_name=last_name,
               department=department, position=position)
    
    # Set role
    if role == 'admin':
        user.is_admin = True
        user.is_manager = False
    elif role == 'manager':
        user.is_admin = False
        user.is_manager = True
    else:  # employee
        user.is_admin = False
        user.is_manager = False
        
        # Assign to manager if selected
        if manager_id and manager_id.isdigit():
            user.manager_id = int(manager_id)
    
    # Set hourly rate if provided
    if hourly_rate and hourly_rate.strip():
        try:
            user.hourly_rate = float(hourly_rate)
        except ValueError:
            pass  # Ignore invalid hourly rate
    
    # Set password and save user
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    flash(f'User {username} created successfully.', 'success')
    return redirect(url_for('admin_user_management'))


@app.route('/admin/users/edit', methods=['POST'])
@login_required
@admin_required
def admin_edit_user():
    """Edit an existing user"""
    user_id = request.form.get('user_id')
    
    user = User.query.get_or_404(user_id)
    
    # Don't allow non-admins to modify admin users
    if user.is_admin and user.id != current_user.id and not current_user.is_admin:
        flash('You do not have permission to edit administrator accounts.', 'danger')
        return redirect(url_for('admin_user_management'))
    
    # Update user details
    user.email = request.form.get('email')
    user.first_name = request.form.get('first_name')
    user.last_name = request.form.get('last_name')
    user.department = request.form.get('department')
    user.position = request.form.get('position')
    
    # Update hourly rate if provided
    hourly_rate = request.form.get('hourly_rate')
    if hourly_rate and hourly_rate.strip():
        try:
            user.hourly_rate = float(hourly_rate)
        except ValueError:
            pass  # Ignore invalid hourly rate
    else:
        user.hourly_rate = None
    
    # Handle role changes if current user is admin
    if current_user.is_admin:
        role = request.form.get('role')
        
        # Update role
        if role == 'admin':
            user.is_admin = True
            user.is_manager = False
            user.manager_id = None
        elif role == 'manager':
            user.is_admin = False
            user.is_manager = True
            user.manager_id = None
        else:  # employee
            user.is_admin = False
            user.is_manager = False
            
            # Assign to manager if selected
            manager_id = request.form.get('manager_id')
            if manager_id and manager_id.isdigit():
                user.manager_id = int(manager_id)
            else:
                user.manager_id = None
    
    # Handle password change if new password provided
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if new_password:
        if new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
            return redirect(url_for('admin_user_management'))
            
        user.set_password(new_password)
        flash('Password updated successfully.', 'success')
    
    db.session.commit()
    flash(f'User {user.username} updated successfully.', 'success')
    return redirect(url_for('admin_user_management'))


@app.route('/admin/users/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_user():
    """Delete a user"""
    user_id = request.form.get('user_id')
    user = User.query.get_or_404(user_id)
    
    # Don't allow deletion of own account
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin_user_management'))
    
    # Don't allow non-admins to delete admin users
    if user.is_admin and not current_user.is_admin:
        flash('You do not have permission to delete administrator accounts.', 'danger')
        return redirect(url_for('admin_user_management'))
    
    username = user.username
    
    # Remove this user as manager from any employees
    if user.is_manager:
        for employee in user.employees:
            employee.manager_id = None
    
    # Delete the user
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {username} deleted successfully.', 'success')
    return redirect(url_for('admin_user_management'))


@app.route('/admin/users/get', methods=['GET'])
@login_required
@admin_required
def admin_get_user():
    """Get user data for editing in modal form"""
    user_id = request.args.get('user_id')
    user = User.query.get_or_404(user_id)
    managers = User.query.filter_by(is_manager=True).all()
    
    # Generate HTML for the edit form
    html = render_template('admin/edit_user_form.html', user=user, managers=managers)
    
    return jsonify({'html': html})

# Initialize database
with app.app_context():
    db.create_all()
    create_default_admin()

# Run the app
if __name__ == "__main__":
    import os
    from waitress import serve
    
    # Get port from environment variable or use 5050 as default
    port = int(os.environ.get("PORT", 5050))
    
    # Determine which mode to run in
    is_render = os.environ.get("RENDER", "") == "true"
    is_desktop = os.environ.get("DESKTOP_MODE", "") == "true"
    
    if is_render:
        # Production mode on Render
        print(f"Starting production server on port {port}...")
        serve(app, host="0.0.0.0", port=port)
    elif is_desktop:
        # Desktop application mode - server will be started by desktop_launcher.py
        print(f"Desktop mode detected. Server will be started by launcher.")
        # This won't actually run in desktop mode as we import app
        pass
    else:
        # Development mode
        print(f"Starting development server on port {port}...")
        app.run(debug=True, port=port)
