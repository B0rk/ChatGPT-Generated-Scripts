#!/usr/bin/env python3
"""
File Upload & Directory Browser Server

Features:
 - Web GUI for uploading into any subdirectory
 - Directory browsing with "Up" navigation
 - Configurable root via CLI
 - Download links for every file (including nested)
 - Prevents path traversal outside the root
"""

import os
import argparse
from flask import (
    Flask, request, render_template_string, redirect,
    url_for, flash, send_from_directory, abort
)
from werkzeug.utils import secure_filename

# HTML template with directory navigation
UPLOAD_PAGE = """
<!doctype html>
<html>
  <head>
    <title>File Upload & Browser</title>
    <style>
      body { font-family: Arial, sans-serif; margin:2rem; }
      h1, h2 { color: #333; }
      .messages { color: red; }
      ul.items { list-style: none; padding: 0; }
      ul.items li { margin: 0.5rem 0; }
      a.dir { font-weight: bold; }
    </style>
  </head>
  <body>
    <h1>Directory: /{{ current_path }}</h1>
    {% if parent_path is not none %}
      <p><a href="{{ url_for('upload_file', path=parent_path) }}">⬆ Up</a></p>
    {% endif %}
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
    <form method="post" enctype="multipart/form-data" action="{{ url_for('upload_file', path=current_path) }}">
      <input type="file" name="file">
      <button type="submit">Upload to /{{ current_path }}</button>
    </form>
    <h2>Contents</h2>
    <ul class="items">
      {% for dirname in dirs %}
        <li><a class="dir" href="{{ url_for('upload_file', path=(current_path + '/' + dirname).strip('/')) }}">{{ dirname }}/</a></li>
      {% endfor %}
      {% for filename in files %}
        <li><a href="{{ url_for('download_file', filename=(current_path + '/' + filename).strip('/')) }}">{{ filename }}</a></li>
      {% endfor %}
    </ul>
  </body>
</html>
"""

def safe_join(base, *paths):
    """Join and resolve, then ensure the result is inside base."""
    final = os.path.abspath(os.path.join(base, *paths))
    if os.path.commonpath([final, base]) != os.path.abspath(base):
        raise ValueError("Attempt to access outside of root")
    return final

def create_app(upload_root):
    app = Flask(__name__)
    app.config['UPLOAD_FOLDER'] = os.path.abspath(upload_root)
    app.config['MAX_CONTENT_LENGTH'] = 1024**3  # 1 GiB
    app.secret_key = os.urandom(16)

    @app.route('/', methods=['GET', 'POST'])
    @app.route('/<path:path>', methods=['GET', 'POST'])
    def upload_file(path=""):
        # Normalize and verify path
        try:
            current_dir = safe_join(app.config['UPLOAD_FOLDER'], path)
        except ValueError:
            abort(404, "Invalid directory")

        if request.method == 'POST':
            # Upload handling
            if 'file' not in request.files:
                flash('No file part in the request.')
                return redirect(request.url)
            file = request.files['file']
            if not file or file.filename == '':
                flash('No file selected for uploading.')
                return redirect(request.url)

            filename = secure_filename(file.filename)
            dest_path = os.path.join(current_dir, filename)
            try:
                file.save(dest_path)
                flash(f'File "{filename}" uploaded successfully to /{path}')
            except Exception as e:
                flash(f'Error saving file: {e}')

            return redirect(url_for('upload_file', path=path))

        # Directory listing
        try:
            entries = os.listdir(current_dir)
            dirs = sorted([e for e in entries if os.path.isdir(os.path.join(current_dir, e))])
            files = sorted([e for e in entries if os.path.isfile(os.path.join(current_dir, e))])
        except Exception as e:
            flash(f'Could not list directory: {e}')
            dirs, files = [], []

        # Determine parent path
        if path:
            parent = os.path.dirname(path)
            parent_path = parent
        else:
            parent_path = None

        return render_template_string(
            UPLOAD_PAGE,
            current_path=path,
            parent_path=parent_path,
            dirs=dirs,
            files=files
        )

    @app.route('/download/<path:filename>')
    def download_file(filename):
        # Ensure safe path, then serve
        try:
            # This also normalizes and prevents traversal
            safe_join(app.config['UPLOAD_FOLDER'], filename)
        except ValueError:
            abort(404, "Invalid file")
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

    return app

def main():
    parser = argparse.ArgumentParser(description='Python File Upload & Browser Server')
    parser.add_argument('-p', '--port', type=int, default=5000,
                        help='Port to listen on (default: 5000)')
    parser.add_argument('-d', '--directory', default=os.getcwd(),
                        help='Root directory to serve (default: cwd)')
    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        parser.error(f'Directory not found: {args.directory}')

    app = create_app(args.directory)
    app.run(host='0.0.0.0', port=args.port)

if __name__ == '__main__':
    main()
