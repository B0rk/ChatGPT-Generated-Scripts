#!/usr/bin/env python3
"""
File Upload Server

This service provides:
 - A web-based GUI (HTML form) for uploading any file
 - Configurable save directory and listening port via CLI
 - Listing of uploaded files with download links
 - Basic error handling and user feedback
"""

import os
import argparse
from flask import (
    Flask, request, render_template_string, redirect,
    url_for, flash, send_from_directory
)
from werkzeug.utils import secure_filename

# HTML template for upload page
UPLOAD_PAGE = """
<!doctype html>
<html>
  <head>
    <title>File Upload Service</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 2rem; }
      h1 { color: #333; }
      .messages { color: red; }
      ul.files { list-style: none; padding: 0; }
      ul.files li { margin: 0.5rem 0; }
    </style>
  </head>
  <body>
    <h1>Upload a File</h1>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <div class="messages">
          <ul>
          {% for msg in messages %}
            <li>{{ msg }}</li>
          {% endfor %}
          </ul>
        </div>
      {% endif %}
    {% endwith %}
    <form method="post" enctype="multipart/form-data">
      <input type="file" name="file">
      <button type="submit">Upload</button>
    </form>
    <h2>Uploaded Files</h2>
    <ul class="files">
    {% for filename in files %}
      <li><a href="{{ url_for('download_file', filename=filename) }}">{{ filename }}</a></li>
    {% endfor %}
    </ul>
  </body>
</html>
"""

def create_app(upload_folder):
    app = Flask(__name__)
    app.config['UPLOAD_FOLDER'] = upload_folder
    app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1 GiB max; adjust as needed
    app.secret_key = os.urandom(16)

    @app.route('/', methods=['GET', 'POST'])
    def upload_file():
        if request.method == 'POST':
            # Verify 'file' part present
            if 'file' not in request.files:
                flash('No file part in the request.')
                return redirect(request.url)
            file = request.files['file']
            # Check filename
            if not file or file.filename == '':
                flash('No file selected for uploading.')
                return redirect(request.url)
            # Sanitize and save
            filename = secure_filename(file.filename)
            dest = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                file.save(dest)
                flash(f'File “{filename}” uploaded successfully.')
            except Exception as e:
                flash(f'Error saving file: {e}')
            return redirect(request.url)

        # GET: list files
        try:
            files = sorted(os.listdir(app.config['UPLOAD_FOLDER']))
        except Exception:
            files = []
            flash('Could not list uploaded files.')
        return render_template_string(UPLOAD_PAGE, files=files)

    @app.route('/uploads/<filename>')
    def download_file(filename):
        return send_from_directory(
            app.config['UPLOAD_FOLDER'], filename, as_attachment=True
        )

    return app

def main():
    parser = argparse.ArgumentParser(
        description='Simple Python File Upload Server'
    )
    parser.add_argument(
        '-p', '--port',
        type=int, default=5000,
        help='Port to listen on (default: 5000)'
    )
    parser.add_argument(
        '-d', '--directory',
        default=os.getcwd(),
        help='Directory to save uploaded files (default: cwd)'
    )
    args = parser.parse_args()

    # Validate upload directory
    if not os.path.isdir(args.directory):
        parser.error(f'Directory not found or not a directory: {args.directory}')

    app = create_app(args.directory)
    app.run(host='0.0.0.0', port=args.port)

if __name__ == '__main__':
    main()
