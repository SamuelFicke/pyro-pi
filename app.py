#!/usr/bin/python3

from flask import Flask, render_template, request, redirect, url_for
import subprocess
from datetime import datetime, timedelta
from fire import fireplace
import multiprocessing


app = Flask(__name__)

HOUR = 60*60
MAX_ON_TIME = 4 * HOUR
DEFAULT_ON_TIME = 1 * HOUR

# global variables
fire_on = False
on_time = datetime.now()
off_time = datetime.now()

# turn the fireplace off when we start the web app
fireplace_obj.off()

producer, consumer = multiprocessing.Pipe()


def fireplace_handler(connection):


@app.route('/', methods=['GET', 'POST'])
def index():
    
    # grab global variables
    global fire_on
    global on_time
    global off_time
    global max_off_time
    global fireplace_obj

    if request.method == 'POST':
        # Get the value from the form input field named 'new_value'
        new_value = request.form.get("new_value")

        if 'set_button' in request.form:
            if not fire_on:
                fire_on = True
                off_time = datetime.now() + timedelta(seconds=DEFAULT_ON_TIME)
                max_off_time = datetime.now() + timedelta(seconds=MAX_ON_TIME) 
                producer.send("hello")
                fireplace_obj.on()
        elif 'unset_button' in request.form:
            fire_on = False        
            fireplace_obj.off()
        elif 'add_hour' in request.form:
            off_time = off_time + timedelta(seconds=HOUR)
            if off_time > max_off_time:
                off_time = max_off_time
        elif 'subtract_hour' in request.form:
            off_time = off_time - timedelta(seconds=HOUR)

    # display fire status
    if fire_on:
        fire_status_str = "ON"
        off_time_str = f"Fire will turn off at {off_time.strftime('%I:%M:%S %p')}"
    else:
        fire_status_str = "OFF"        
        off_time_str = ""
 
    # Render the template and pass the current variable value to the HTML
    return render_template('index.html', fire_status=fire_status_str, fire_off_time=off_time_str)

@app.route('/get_time')
def get_time():
    """API endpoint to get the current server time."""
    
    global fireplace_obj
    global off_time
    global fire_on

    current_time = datetime.now()

    # turn fireplace off when we get to that time
    if fire_on and current_time > off_time:
        fireplace_obj.off()
        fire_on = False

    off_time_str = f"Fire will turn off at {off_time.strftime('%I:%M:%S %p')}"
   
    # display fire status
    if fire_on:
        fire_status_str = "The Fireplace is ON"
    else:
        fire_status_str = "The Fireplace is OFF"
        off_time_str = ""

    return_dict = {"fire_off_time" : off_time_str, "current_time": datetime.now().strftime("%I:%M:%S %p"),"fire_status_str" : fire_status_str}
 
    print(return_dict)
    return return_dict

@app.route('/run-script', methods=['POST'])
def run_script():

    global fire_on
    global off_time
    global on_time
    global max_off_time

    # Call your Python function when the POST request to /run-script is received
    result_message = my_script_function()
    # Get the current date and time
    current_time_obj = datetime.datetime.now()
    # Format the time as a string (e.g., "01/20/26, 07:48:00 PM")
    formatted_time = current_time_obj.strftime("%m/%d/%Y, %I:%M:%S %p")
    # You can return a message or redirect back to the home page
    
    if fire_on:
        fire_status_str = "ON"
    else:
        fire_status_str = "OFF"

    return render_template('index.html', fire_status=fire_status_str)
    # Or redirect to prevent form re-submission on refresh:
    # return redirect(url_for('index'))


if __name__ == '__main__':
    # Run the app. Note: disable debug mode in production
    app.run(debug=False, host='0.0.0.0')

