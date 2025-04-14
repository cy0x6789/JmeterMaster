import os
import json
import logging
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from performance_tester import PerformanceTester
from report_generator import ReportGenerator
import pandas as pd
import io
import csv

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key-for-development")

# In-memory storage for test results
test_history = []

@app.route('/')
def index():
    """Render the main page with the test configuration form."""
    return render_template('index.html')

@app.route('/run_test', methods=['POST'])
def run_test():
    """Run a performance test with the provided configuration."""
    try:
        # Get test parameters from the form
        target_url = request.form.get('target_url')
        http_method = request.form.get('http_method', 'GET')
        num_requests = int(request.form.get('num_requests', 10))
        concurrency = int(request.form.get('concurrency', 1))
        timeout = int(request.form.get('timeout', 30))
        
        # Optional parameters
        headers = {}
        headers_text = request.form.get('headers', '')
        if headers_text:
            for line in headers_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip()] = value.strip()
        
        body = request.form.get('body', '')
        
        # Validate inputs
        if not target_url:
            return jsonify({'error': 'Target URL is required'}), 400
        
        if num_requests < 1:
            return jsonify({'error': 'Number of requests must be at least 1'}), 400
            
        if concurrency < 1:
            return jsonify({'error': 'Concurrency must be at least 1'}), 400
        
        if concurrency > num_requests:
            return jsonify({'error': 'Concurrency cannot be greater than the number of requests'}), 400
        
        # Create performance tester and run the test
        tester = PerformanceTester(
            target_url=target_url,
            http_method=http_method,
            num_requests=num_requests,
            concurrency=concurrency,
            timeout=timeout,
            headers=headers,
            body=body
        )
        
        # Run test and get results
        results = tester.run_test()
        
        # Generate report
        report_generator = ReportGenerator(results)
        report = report_generator.generate_report()
        
        # Add timestamp to results
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report['timestamp'] = timestamp
        report['test_config'] = {
            'target_url': target_url,
            'http_method': http_method,
            'num_requests': num_requests,
            'concurrency': concurrency,
            'timeout': timeout
        }
        
        # Store in test history
        test_id = str(int(time.time()))
        report['test_id'] = test_id
        test_history.append(report)
        
        return jsonify({'success': True, 'test_id': test_id})
        
    except Exception as e:
        logging.error(f"Error running test: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/view_report/<test_id>')
def view_report(test_id):
    """View a specific test report."""
    for report in test_history:
        if report.get('test_id') == test_id:
            return render_template('reports.html', report=report)
    
    return render_template('reports.html', error="Report not found")

@app.route('/reports')
def reports():
    """View the most recent report or an empty report page."""
    if test_history:
        latest_report = test_history[-1]
        return render_template('reports.html', report=latest_report)
    else:
        return render_template('reports.html', error="No tests have been run yet")

@app.route('/all_reports')
def all_reports():
    """Get all test reports for the history view."""
    return jsonify(test_history)

@app.route('/export_report/<test_id>/<format>')
def export_report(test_id, format):
    """Export a report in the specified format (CSV, JSON)."""
    report = None
    for r in test_history:
        if r.get('test_id') == test_id:
            report = r
            break
    
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    
    try:
        if format == 'csv':
            # Convert report to DataFrame for easier CSV export
            df_data = {
                'Metric': [],
                'Value': []
            }
            
            # Add test configuration
            for key, value in report['test_config'].items():
                df_data['Metric'].append(f"Config: {key}")
                df_data['Value'].append(str(value))
            
            # Add summary metrics
            for key, value in report['summary'].items():
                df_data['Metric'].append(key)
                df_data['Value'].append(str(value))
            
            # Add detailed metrics if available
            if 'requests' in report:
                request_df = pd.DataFrame(report['requests'])
                
            df = pd.DataFrame(df_data)
            
            # Create in-memory CSV file
            output = io.StringIO()
            df.to_csv(output, index=False)
            output.seek(0)
            
            return send_file(
                io.BytesIO(output.getvalue().encode('utf-8')),
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'performance_test_{test_id}.csv'
            )
            
        elif format == 'json':
            return send_file(
                io.BytesIO(json.dumps(report, indent=2).encode('utf-8')),
                mimetype='application/json',
                as_attachment=True,
                download_name=f'performance_test_{test_id}.json'
            )
        else:
            return jsonify({'error': 'Unsupported export format'}), 400
            
    except Exception as e:
        logging.error(f"Error exporting report: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/clear_history', methods=['POST'])
def clear_history():
    """Clear the test history."""
    global test_history
    test_history = []
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
