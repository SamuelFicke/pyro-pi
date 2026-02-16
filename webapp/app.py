from flask import Flask, render_template, request, redirect, url_for
import subprocess
import datetime

fire_on = False

app = Flask(__name__)

# This function will be called when the button is clicked
def my_script_function():
    print("Python script function executed!")
    # Add your script's logic here.
    # For running a separate script file, you can use subprocess.call:
    # subprocess.call(['/home/pi/flask/task.sh']) # Example from search results
    return "Script executed successfully!"

@app.route('/', methods=['GET', 'POST'])
def index():
    global fire_on
    if request.method == 'POST':
        # Get the value from the form input field named 'new_value'
        new_value = request.form.get("new_value")

        if 'set_button' in request.form:
            fire_on = True
        elif 'unset_button' in request.form:
            fire_on = False

    if fire_on:
        fire_status_str = "ON"
    else:
        fire_status_str = "OFF"
                
    # Render the template and pass the current variable value to the HTML
    return render_template('index.html', fire_status=fire_status_str)

@app.route('/get_time')
def get_time():
    """API endpoint to get the current server time."""
    return {"time": datetime.datetime.now().strftime("%H:%M:%S")}

@app.route('/run-script', methods=['POST'])
def run_script():
    # Call your Python function when the POST request to /run-script is received
    result_message = my_script_function()
    # Get the current date and time
    current_time_obj = datetime.datetime.now()
    # Format the time as a string (e.g., "01/20/26, 07:48:00 PM")
    formatted_time = current_time_obj.strftime("%m/%d/%Y, %I:%M:%S %p")
    # You can return a message or redirect back to the home page
    return render_template('index.html', message=result_message)
    # Or redirect to prevent form re-submission on refresh:
    # return redirect(url_for('index'))

if __name__ == '__main__':
    # Run the app. Note: disable debug mode in production
    app.run(debug=True, host='0.0.0.0')

