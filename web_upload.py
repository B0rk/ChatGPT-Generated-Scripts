#!/usr/bin/env python3
import os
from flask import Flask, request, render_template_string
from werkzeug.utils import secure_filename

# Configuration: Files will be saved in the directory where this script is located.
UPLOAD_FOLDER = os.path.abspath(os.path.dirname(__file__))

# Utility function to allow all file types
def allowed_file(filename):
    # Return True to allow files with any extension.
    return True

# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# HTML template for the upload page
UPLOAD_PAGE = '''
<!doctype html>
<html>
  <head>
    <title>File Upload Service</title>
  </head>
  <body>
    <h1>Upload a File</h1>
    <form method="post" enctype="multipart/form-data">
      <input type="file" name="file">
      <input type="submit" value="Upload">
    </form>
  </body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Verify that a file part exists in the request
        if 'file' not in request.files:
            return 'Error: No file part in the request.', 400

        file = request.files['file']
        # Check if the user submitted an empty file field
        if file.filename == '':
            return 'Error: No file selected for uploading.', 400

        # Save the file after sanitizing the filename
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            return f'Success: File uploaded to {file_path}.', 200
        else:
            return 'Error: File type not allowed.', 400

    # Render the upload form for GET requests
    return render_template_string(UPLOAD_PAGE)

if __name__ == '__main__':
    # For production, remove debug=True and properly configure the host and port as needed.
    app.run(host='0.0.0.0', port=443, debug=False)
