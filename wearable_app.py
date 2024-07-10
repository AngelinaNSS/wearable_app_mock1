from flask import Flask, render_template, request, redirect, url_for
import os
import pandas as pd
import plotly.graph_objs as go
import plotly.io as pio
from datetime import timedelta

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'csv', 'json'}

def read_data(file_path):
    if file_path.endswith('.csv'):
        data = pd.read_csv(file_path)
    elif file_path.endswith('.json'):
        data = pd.read_json(file_path)
    return data

def validate_data(data):
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    data.set_index('timestamp', inplace=True)
    data = data.resample('2T').mean()  # Resample to 2-minute intervals
    return data

def find_valid_intervals(data):
    valid_intervals = []
    start_time = data.index[0]
    while start_time + timedelta(hours=2) <= data.index[-1]:
        interval_data = data[start_time:start_time + timedelta(hours=2)]
        if len(interval_data) == 60:  # 60 intervals of 2 minutes in 2 hours
            valid_intervals.append((start_time, start_time + timedelta(hours=2)))
        start_time += timedelta(minutes=2)
    return valid_intervals

def extract_heart_rate_stats(data, interval):
    interval_data = data[interval[0]:interval[1]]
    min_hr = interval_data['heartrate'].min()
    max_hr = interval_data['heartrate'].max()
    avg_hr = interval_data['heartrate'].mean()
    return min_hr, max_hr, avg_hr, interval_data

def plot_heart_rate(interval_data):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=interval_data.index, y=interval_data['heartrate'], mode='lines', name='Heart Rate'))
    fig.update_layout(title='Heart Rate over Time', xaxis_title='Time', yaxis_title='Heart Rate')
    return pio.to_html(fig, full_html=False)

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return 'No file part'
        file = request.files['file']
        if file.filename == '':
            return 'No selected file'
        if file and allowed_file(file.filename):
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            return redirect(url_for('data'))
    return render_template('index.html')

@app.route('/data')
def data():
    latest_file = sorted(os.listdir(app.config['UPLOAD_FOLDER']))[-1]
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], latest_file)
    data = read_data(file_path)
    data = validate_data(data)
    valid_intervals = find_valid_intervals(data)
    return render_template('data.html', intervals=valid_intervals)

@app.route('/latest')
def latest():
    latest_file = sorted(os.listdir(app.config['UPLOAD_FOLDER']))[-1]
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], latest_file)
    data = read_data(file_path)
    data = validate_data(data)
    valid_intervals = find_valid_intervals(data)
    if valid_intervals:
        latest_interval = valid_intervals[-1]
        min_hr, max_hr, avg_hr, interval_data = extract_heart_rate_stats(data, latest_interval)
        plot_html = plot_heart_rate(interval_data)
        return render_template('latest.html', min_hr=min_hr, max_hr=max_hr, avg_hr=avg_hr, plot_html=plot_html)
    else:
        return 'No valid 2-hour intervals found.'

if __name__ == '__main__':
    app.run(debug=True)

