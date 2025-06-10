from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS
import sqlite3
import json
import os
from datetime import datetime, timedelta
import base64
from io import BytesIO
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import re

# Import custom modules
from config import *
from ocr_processor import OCRProcessor

app = Flask(__name__)
CORS(app, origins=SECURITY['allowed_origins'])

# Initialize OCR processor
ocr_processor = OCRProcessor(OCR)

# Database configuration
DATABASE = os.path.join('timetracker.db')

# Initialize database
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Create tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS time_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT NOT NULL,
            entry_type TEXT NOT NULL,
            order_number TEXT,
            start_datetime TEXT NOT NULL,
            end_datetime TEXT NOT NULL,
            elapsed_time TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

# Get database connection
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# API Routes

@app.route('/api/entries', methods=['GET'])
def get_entries():
    conn = get_db()
    c = conn.cursor()
    
    # Get query parameters for filtering
    employee = request.args.get('employee')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = 'SELECT * FROM time_entries WHERE 1=1'
    params = []
    
    if employee:
        query += ' AND employee_name LIKE ?'
        params.append(f'%{employee}%')
    
    if start_date:
        query += ' AND start_datetime >= ?'
        params.append(start_date)
    
    if end_date:
        query += ' AND end_datetime <= ?'
        params.append(end_date)
    
    query += ' ORDER BY start_datetime DESC'
    
    c.execute(query, params)
    entries = []
    
    for row in c.fetchall():
        entries.append({
            'id': row['id'],
            'employeeName': row['employee_name'],
            'entryType': row['entry_type'],
            'orderNumber': row['order_number'],
            'startDateTime': row['start_datetime'],
            'endDateTime': row['end_datetime'],
            'elapsedTime': row['elapsed_time'],
            'notes': row['notes'],
            'createdAt': row['created_at']
        })
    
    conn.close()
    return jsonify(entries)

@app.route('/api/entries', methods=['POST'])
def create_entry():
    data = request.json
    conn = get_db()
    c = conn.cursor()
    
    # Validate entry type
    valid_types = [t['value'] for t in TIME_ENTRY['types']]
    if data['entryType'] not in valid_types:
        return jsonify({'error': 'Invalid entry type'}), 400
    
    # Check if order number is required
    entry_type_config = next((t for t in TIME_ENTRY['types'] if t['value'] == data['entryType']), None)
    if entry_type_config and entry_type_config['requires_order'] and not data.get('orderNumber'):
        return jsonify({'error': 'Order number is required for service entries'}), 400
    
    # Calculate elapsed time
    start = datetime.fromisoformat(data['startDateTime'].replace('Z', '+00:00'))
    end = datetime.fromisoformat(data['endDateTime'].replace('Z', '+00:00'))
    
    # Validate future dates
    if not TIME_ENTRY['allow_future_dates']:
        if start > datetime.now() or end > datetime.now():
            return jsonify({'error': 'Future dates are not allowed'}), 400
    
    elapsed = end - start
    
    # Validate max hours
    max_hours = TIME_ENTRY['max_hours_per_entry']
    if elapsed.total_seconds() / 3600 > max_hours:
        return jsonify({'error': f'Entry cannot exceed {max_hours} hours'}), 400
    
    hours = int(elapsed.total_seconds() // 3600)
    minutes = int((elapsed.total_seconds() % 3600) // 60)
    seconds = int(elapsed.total_seconds() % 60)
    elapsed_time = f"{hours:02d}h:{minutes:02d}m:{seconds:02d}s"
    
    # Check if notes are required
    if TIME_ENTRY['require_notes'] and not data.get('notes'):
        return jsonify({'error': 'Notes are required'}), 400
    
    c.execute('''
        INSERT INTO time_entries 
        (employee_name, entry_type, order_number, start_datetime, end_datetime, elapsed_time, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['employeeName'],
        data['entryType'],
        data.get('orderNumber', ''),
        data['startDateTime'],
        data['endDateTime'],
        elapsed_time,
        data.get('notes', ''),
        datetime.now().isoformat()
    ))
    
    conn.commit()
    entry_id = c.lastrowid
    conn.close()
    
    return jsonify({'id': entry_id, 'message': 'Entry created successfully'})

@app.route('/api/entries/<int:entry_id>', methods=['PUT'])
def update_entry(entry_id):
    data = request.json
    conn = get_db()
    c = conn.cursor()
    
    # Calculate elapsed time
    start = datetime.fromisoformat(data['startDateTime'].replace('Z', '+00:00'))
    end = datetime.fromisoformat(data['endDateTime'].replace('Z', '+00:00'))
    elapsed = end - start
    
    hours = int(elapsed.total_seconds() // 3600)
    minutes = int((elapsed.total_seconds() % 3600) // 60)
    seconds = int(elapsed.total_seconds() % 60)
    elapsed_time = f"{hours:02d}h:{minutes:02d}m:{seconds:02d}s"
    
    c.execute('''
        UPDATE time_entries 
        SET employee_name = ?, entry_type = ?, order_number = ?, 
            start_datetime = ?, end_datetime = ?, elapsed_time = ?, notes = ?
        WHERE id = ?
    ''', (
        data['employeeName'],
        data['entryType'],
        data.get('orderNumber', ''),
        data['startDateTime'],
        data['endDateTime'],
        elapsed_time,
        data.get('notes', ''),
        entry_id
    ))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Entry updated successfully'})

@app.route('/api/entries/<int:entry_id>', methods=['DELETE'])
def delete_entry(entry_id):
    conn = get_db()
    c = conn.cursor()
    
    c.execute('DELETE FROM time_entries WHERE id = ?', (entry_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Entry deleted successfully'})

@app.route('/api/ocr', methods=['POST'])
def process_ocr():
    try:
        data = request.json
        image_data = data['image']
        
        # Use OCR processor to extract entries
        entries = ocr_processor.extract_from_base64(image_data)
        
        if not entries:
            return jsonify({'error': 'No time entries found in image'}), 400
        
        return jsonify({'entries': entries})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/report', methods=['POST'])
def generate_report():
    data = request.json
    report_type = data['reportType']
    start_date = data['startDate']
    end_date = data['endDate']
    employee = data.get('employee', '')
    
    # Get filtered entries
    conn = get_db()
    c = conn.cursor()
    
    query = 'SELECT * FROM time_entries WHERE start_datetime >= ? AND end_datetime <= ?'
    params = [start_date, end_date + 'T23:59:59']
    
    if employee:
        query += ' AND employee_name LIKE ?'
        params.append(f'%{employee}%')
    
    query += ' ORDER BY start_datetime'
    
    c.execute(query, params)
    entries = []
    
    for row in c.fetchall():
        entries.append({
            'id': row['id'],
            'employee_name': row['employee_name'],
            'entry_type': row['entry_type'],
            'order_number': row['order_number'],
            'start_datetime': row['start_datetime'],
            'end_datetime': row['end_datetime'],
            'elapsed_time': row['elapsed_time'],
            'notes': row['notes']
        })
    
    conn.close()
    
    # Generate PDF
    pdf_buffer = generate_pdf_report(entries, report_type, start_date, end_date)
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'{report_type}_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    )

def generate_pdf_report(entries, report_type, start_date, end_date):
    """Generate PDF report using ReportLab"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Use colors from config
    primary_color = colors.HexColor(REPORTS['color_scheme']['primary'])
    secondary_color = colors.HexColor(REPORTS['color_scheme']['secondary'])
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=primary_color,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=12
    )
    
    # Add title
    elements.append(Paragraph(REPORTS['company_name'], title_style))
    elements.append(Paragraph(f"{report_type.title()} Time Report", heading_style))
    elements.append(Spacer(1, 12))
    
    # Add report info
    info_data = [
        ['Report Period:', f"{start_date} to {end_date}"],
        ['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
        ['Total Entries:', str(len(entries))]
    ]
    
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1f2937')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('PADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb'))
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # Generate report content based on type
    if report_type == 'summary':
        elements.extend(generate_summary_pdf(entries))
    elif report_type == 'detailed':
        elements.extend(generate_detailed_pdf(entries))
    elif report_type == 'employee':
        elements.extend(generate_employee_pdf(entries))
    elif report_type == 'order':
        elements.extend(generate_order_pdf(entries))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    return buffer

def generate_summary_pdf(entries):
    """Generate summary report content"""
    elements = []
    
    # Calculate summary data
    summary = {}
    total_hours = 0
    
    for entry in entries:
        emp_name = entry['employee_name']
        hours = parse_elapsed_time(entry['elapsed_time'])
        total_hours += hours
        
        if emp_name not in summary:
            summary[emp_name] = {
                'total_hours': 0,
                'entries': 0,
                'types': {}
            }
        
        summary[emp_name]['total_hours'] += hours
        summary[emp_name]['entries'] += 1
        
        entry_type = entry['entry_type']
        if entry_type not in summary[emp_name]['types']:
            summary[emp_name]['types'][entry_type] = 0
        summary[emp_name]['types'][entry_type] += hours
    
    # Add summary table
    elements.append(Paragraph("Employee Summary", getSampleStyleSheet()['Heading2']))
    
    # Create table data
    table_data = [['Employee', 'Total Hours', 'Entries']]
    
    # Add columns for each entry type
    for entry_type in TIME_ENTRY['types']:
        table_data[0].append(entry_type['label'])
    
    for emp_name, data in summary.items():
        row = [
            emp_name,
            f"{data['total_hours']:.2f}",
            str(data['entries'])
        ]
        
        # Add hours for each entry type
        for entry_type in TIME_ENTRY['types']:
            hours = data['types'].get(entry_type['value'], 0)
            row.append(f"{hours:.2f}" if hours > 0 else '-')
        
        table_data.append(row)
    
    # Add total row
    total_row = ['TOTAL', f"{total_hours:.2f}", str(len(entries))]
    total_row.extend([''] * len(TIME_ENTRY['types']))
    table_data.append(total_row)
    
    table = Table(table_data)
    
    # Apply color scheme from config
    primary_color = colors.HexColor(REPORTS['color_scheme']['primary'])
    
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f3f4f6')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb'))
    ]))
    
    elements.append(table)
    
    return elements

def generate_detailed_pdf(entries):
    """Generate detailed report content"""
    elements = []
    
    elements.append(Paragraph("Detailed Time Entries", getSampleStyleSheet()['Heading2']))
    
    # Create table data
    table_data = [['Date', 'Employee', 'Type', 'Order #', 'Start', 'End', 'Duration']]
    
    for entry in entries:
        start_dt = datetime.fromisoformat(entry['start_datetime'].replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(entry['end_datetime'].replace('Z', '+00:00'))
        
        # Get entry type config for color
        entry_type_config = next((t for t in TIME_ENTRY['types'] if t['value'] == entry['entry_type']), None)
        
        row = [
            start_dt.strftime('%Y-%m-%d'),
            entry['employee_name'],
            entry['entry_type'],
            entry['order_number'] or '-',
            start_dt.strftime('%H:%M'),
            end_dt.strftime('%H:%M'),
            entry['elapsed_time']
        ]
        table_data.append(row)
    
    table = Table(table_data, repeatRows=1)
    
    primary_color = colors.HexColor(REPORTS['color_scheme']['primary'])
    
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')])
    ]))
    
    elements.append(table)
    
    return elements

def generate_employee_pdf(entries):
    """Generate employee report content"""
    elements = []
    
    # Group by employee
    employee_data = {}
    for entry in entries:
        emp_name = entry['employee_name']
        if emp_name not in employee_data:
            employee_data[emp_name] = []
        employee_data[emp_name].append(entry)
    
    for emp_name, emp_entries in employee_data.items():
        elements.append(Paragraph(f"Employee: {emp_name}", getSampleStyleSheet()['Heading2']))
        
        # Calculate total hours
        total_hours = sum(parse_elapsed_time(e['elapsed_time']) for e in emp_entries)
        elements.append(Paragraph(f"Total Hours: {total_hours:.2f}", getSampleStyleSheet()['Normal']))
        elements.append(Spacer(1, 12))
        
        # Create table for this employee
        table_data = [['Date', 'Type', 'Order Number', 'Duration']]
        
        for entry in emp_entries:
            start_dt = datetime.fromisoformat(entry['start_datetime'].replace('Z', '+00:00'))
            
            row = [
                start_dt.strftime('%Y-%m-%d'),
                entry['entry_type'],
                entry['order_number'] or '-',
                entry['elapsed_time']
            ]
            table_data.append(row)
        
        table = Table(table_data)
        
        primary_color = colors.HexColor(REPORTS['color_scheme']['primary'])
        
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb'))
        ]))
        
        elements.append(table)
        elements.append(PageBreak())
    
    return elements

def generate_order_pdf(entries):
    """Generate service order report content"""
    elements = []
    
    # Filter and group by order number
    order_data = {}
    for entry in entries:
        if entry['order_number']:
            order_num = entry['order_number']
            if order_num not in order_data:
                order_data[order_num] = []
            order_data[order_num].append(entry)
    
    for order_num, order_entries in order_data.items():
        elements.append(Paragraph(f"Service Order: {order_num}", getSampleStyleSheet()['Heading2']))
        
        # Calculate total hours and get unique employees
        total_hours = sum(parse_elapsed_time(e['elapsed_time']) for e in order_entries)
        employees = list(set(e['employee_name'] for e in order_entries))
        
        elements.append(Paragraph(f"Total Hours: {total_hours:.2f}", getSampleStyleSheet()['Normal']))
        elements.append(Paragraph(f"Employees: {', '.join(employees)}", getSampleStyleSheet()['Normal']))
        elements.append(Spacer(1, 12))
        
        # Create table for this order
        table_data = [['Date', 'Employee', 'Start', 'End', 'Duration']]
        
        for entry in order_entries:
            start_dt = datetime.fromisoformat(entry['start_datetime'].replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(entry['end_datetime'].replace('Z', '+00:00'))
            
            row = [
                start_dt.strftime('%Y-%m-%d'),
                entry['employee_name'],
                start_dt.strftime('%H:%M'),
                end_dt.strftime('%H:%M'),
                entry['elapsed_time']
            ]
            table_data.append(row)
        
        table = Table(table_data)
        
        primary_color = colors.HexColor(REPORTS['color_scheme']['primary'])
        
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb'))
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 20))
    
    return elements

def parse_elapsed_time(elapsed_str):
    """Parse elapsed time string to hours"""
    match = re.match(r'(\d+)h:(\d+)m:(\d+)s', elapsed_str)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        seconds = int(match.group(3))
        return hours + minutes/60 + seconds/3600
    return 0

@app.route('/api/stats', methods=['GET'])
def get_stats():
    conn = get_db()
    c = conn.cursor()
    
    # Get current week's data
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Total hours this week
    c.execute('''
        SELECT elapsed_time FROM time_entries 
        WHERE start_datetime >= ?
    ''', (week_start.isoformat(),))
    
    total_hours = 0
    for row in c.fetchall():
        total_hours += parse_elapsed_time(row['elapsed_time'])
    
    # Total entries
    c.execute('SELECT COUNT(*) as count FROM time_entries')
    total_entries = c.fetchone()['count']
    
    # Active service orders
    c.execute('''
        SELECT COUNT(DISTINCT order_number) as count 
        FROM time_entries 
        WHERE entry_type = 'service' AND order_number != ''
    ''')
    active_orders = c.fetchone()['count']
    
    conn.close()
    
    return jsonify({
        'totalHoursThisWeek': round(total_hours, 1),
        'totalEntries': total_entries,
        'activeOrders': active_orders
    })

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get frontend configuration"""
    return jsonify({
        'timeEntry': TIME_ENTRY,
        'ui': UI,
        'reports': REPORTS,
        'notifications': NOTIFICATIONS
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    init_db()
    app.run(
        host=SERVER['host'],
        port=SERVER['port'],
        debug=SERVER['debug']
    )
