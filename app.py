#!/usr/bin/python3

from flask import Flask, render_template, request, redirect, url_for
import subprocess
from datetime import datetime, timedelta
from fire import fireplace
import multiprocessing


app = Flask(__name__)

HOUR = 60*60
MAX_ON_TIME = 4 * HOUR
DEFAULT_ON_TIME = 15#1 * HOUR

# global variables
class fire_state:

    def __init__(self):
        self.fire_on = False
        self.time_on = datetime.min
        self.time_off = datetime.min
        self.time_off_max = datetime.min

app_state = fire_state()

producer, consumer = multiprocessing.Pipe()

def run_app():
    # Run the app. Note: disable debug mode in production
    app.run(debug=False, host='0.0.0.0')


def fireplace_handler(pipe):

    global state

    # init object
    fireplace_obj = fireplace(hardware=True)
    # turn the fireplace off when we start the web app
    fireplace_obj.off()

    state = fire_state()

    # how often to run the loop
    loop_time = 5 # seconds

    # run forever
    while(True):

        # run once every five seconds
        if(pipe.poll(timeout=loop_time)):
            form = pipe.recv()
            
            if 'set_button' in form:
                if not state.fire_on:
                    state.fire_on = True
                    state.time_off = datetime.now() + timedelta(seconds=DEFAULT_ON_TIME)
                    state.time_off_max = datetime.now() + timedelta(seconds=MAX_ON_TIME) 
                    fireplace_obj.on()
            elif 'unset_button' in form:
                state.fire_on = False        
                fireplace_obj.off()
            elif 'add_hour' in form:
                state.time_off += timedelta(seconds=HOUR)
                if state.time_off > state.time_off_max:
                    state.time_off = state.time_off_max
            elif 'subtract_hour' in form:
                state.time_off -= timedelta(seconds=HOUR)

            # send back current state
            pipe.send(state)

        else:
            if state.fire_on:
                # check to see if it's time to turn off the fire
                current_time = datetime.now()
                if current_time > state.time_off or current_time > state.time_off_max:
                    fireplace_obj.off()
                    state.fire_on = False

                    # send app updated state
                    pipe.send(state)

@app.route('/', methods=['GET', 'POST'])
def index():

    global app_state
    
    # send form to fireplace handler for processing
    producer.send(request.form)
    # wait for current state to come back from fireplace handler
    if producer.poll():
        app_state = producer.recv()

    # display fire status
    if app_state.fire_on:
        fire_status_str = "ON"
        off_time_str = f"Fire will turn off at {app_state.time_off.strftime('%I:%M:%S %p')}"
    else:
        fire_status_str = "OFF"        
        off_time_str = ""
 
    # Render the template and pass the current variable value to the HTML
    return render_template('index.html', fire_status=fire_status_str, fire_off_time=off_time_str)

@app.route('/get_time')
def get_time():
    """API endpoint to get the current server time."""
    
    global app_state

    # read the updated state if it's been updated
    if producer.poll():
        app_state = producer.recv()

    off_time_str = f"Fire will turn off at {app_state.time_off.strftime('%I:%M:%S %p')}"
   
    # display fire status
    if app_state.fire_on:
        fire_status_str = "The Fireplace is ON"
    else:
        fire_status_str = "The Fireplace is OFF"
        off_time_str = ""

    return_dict = {"fire_off_time" : off_time_str, "current_time": datetime.now().strftime("%I:%M:%S %p"),"fire_status_str" : fire_status_str}
 
    #print(return_dict)
    return return_dict

if __name__ == '__main__':

    # we need to run two concurrent threads...one for the web app and one for the fireplace handler
    # if we only had the web app, we wouldn't be able to turn off the fireplace unless a client was connected to the server
    fireplace_process = multiprocessing.Process(target=fireplace_handler, args=(consumer,))
    webapp_process = multiprocessing.Process(target=run_app)
    fireplace_process.start()
    webapp_process.start()
    fireplace_process.join()
    webapp_process.join()

