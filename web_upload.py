#!/usr/bin/env python3
"""
File Upload & Directory Browser Server

Features:
 - Web GUI for uploading into any subdirectory
 - Directory browsing with "Up" navigation
 - Configurable root via CLI
 - Download links for every file (including nested)
 - Prevents path traversal and symlink escape outside the root
 - Hidden files (dotfiles) are excluded from listings
 - Configurable bind address (default: 0.0.0.0)
"""

import logging
import os
import posixpath
import argparse
from flask import (
    Flask, request, render_template_string, redirect,
    url_for, flash, send_from_directory, abort
)
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

# Hidden/sensitive patterns to exclude from directory listings
HIDDEN_PREFIXES = (".",)

# HTML template with directory navigation
UPLOAD_PAGE = """
<!doctype html>
<html>
  <head>
    <title>File Upload &amp; Browser</title>
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
        <li><a class="dir" href="{{ url_for('upload_file', path=join_path(current_path, dirname)) }}">{{ dirname }}/</a></li>
      {% endfor %}
      {% for filename in files %}
        <li><a href="{{ url_for('download_file', filename=join_path(current_path, filename)) }}">{{ filename }}</a></li>
      {% endfor %}
    </ul>
  </body>
</html>
"""


def safe_join(base: str, *paths: str) -> str:
    """Join and resolve (including symlinks), then ensure the result is inside base."""
    # Resolve symlinks so a symlink pointing outside root is caught
    resolved_base = os.path.realpath(base)
    final = os.path.realpath(os.path.join(base, *paths))
    # Ensure final path is the base itself or a child of it
    if not (final == resolved_base or final.startswith(resolved_base + os.sep)):
        raise ValueError("Attempt to access outside of root")
    return final


def _is_hidden(name: str) -> bool:
    """Return True if the entry name should be hidden from listings."""
    return any(name.startswith(prefix) for prefix in HIDDEN_PREFIXES)


def create_app(upload_root: str) -> Flask:
    app = Flask(__name__)
    app.config['UPLOAD_FOLDER'] = os.path.realpath(upload_root)
    app.config['MAX_CONTENT_LENGTH'] = 1024 ** 3  # 1 GiB
    app.secret_key = os.urandom(24)

    # Register a template helper for safe path joining
    @app.context_processor
    def utility_processor():
        def join_path(base: str, name: str) -> str:
            return posixpath.join(base, name).strip("/")
        return {"join_path": join_path}

    @app.route('/', methods=['GET', 'POST'])
    @app.route('/<path:path>', methods=['GET', 'POST'])
    def upload_file(path: str = "") -> str:
        root = app.config['UPLOAD_FOLDER']

        # Normalize and verify path
        try:
            current_dir = safe_join(root, path)
        except ValueError:
            abort(404)

        if not os.path.isdir(current_dir):
            abort(404)

        if request.method == 'POST':
            if 'file' not in request.files:
                flash('No file part in the request.')
                return redirect(request.url)
            file = request.files['file']
            if not file or file.filename == '':
                flash('No file selected for uploading.')
                return redirect(request.url)

            filename = secure_filename(file.filename)
            if not filename:
                flash('Invalid filename.')
                return redirect(request.url)

            # Prevent uploading hidden/dot files
            if _is_hidden(filename):
                flash('Uploading hidden (dot) files is not allowed.')
                return redirect(request.url)

            dest_path = os.path.join(current_dir, filename)

            # Prevent overwriting existing files
            if os.path.exists(dest_path):
                flash(f'File "{filename}" already exists. Rename it first.')
                return redirect(url_for('upload_file', path=path))

            try:
                file.save(dest_path)
                logger.info("Uploaded %s to %s", filename, path or "/")
                flash(f'File "{filename}" uploaded successfully to /{path}')
            except OSError:
                logger.exception("Failed to save file %s", filename)
                flash('Error saving file. Check server logs for details.')

            return redirect(url_for('upload_file', path=path))

        # Directory listing — exclude hidden entries
        try:
            entries = os.listdir(current_dir)
            dirs = sorted(
                e for e in entries
                if os.path.isdir(os.path.join(current_dir, e)) and not _is_hidden(e)
            )
            files = sorted(
                e for e in entries
                if os.path.isfile(os.path.join(current_dir, e)) and not _is_hidden(e)
            )
        except OSError:
            logger.exception("Could not list directory %s", current_dir)
            flash('Could not list directory.')
            dirs, files = [], []

        # Determine parent path
        parent_path = os.path.dirname(path) if path else None

        return render_template_string(
            UPLOAD_PAGE,
            current_path=path,
            parent_path=parent_path,
            dirs=dirs,
            files=files,
        )

    @app.route('/download/<path:filename>')
    def download_file(filename: str):
        root = app.config['UPLOAD_FOLDER']
        try:
            resolved = safe_join(root, filename)
        except ValueError:
            abort(404)

        if not os.path.isfile(resolved):
            abort(404)

        # Block downloading hidden files
        if any(_is_hidden(part) for part in filename.split("/")):
            abort(404)

        logger.info("Download requested: %s", filename)
        return send_from_directory(root, filename, as_attachment=True)

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description='Python File Upload & Browser Server')
    parser.add_argument('-p', '--port', type=int, default=5000,
                        help='Port to listen on (default: 5000)')
    parser.add_argument('-b', '--bind', default='0.0.0.0',
                        help='Address to bind to (default: 0.0.0.0)')
    parser.add_argument('-d', '--directory', default=os.getcwd(),
                        help='Root directory to serve (default: cwd)')
    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        parser.error(f'Directory not found: {args.directory}')

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
    )

    app = create_app(args.directory)
    logger.info("Serving %s on %s:%d", os.path.realpath(args.directory), args.bind, args.port)
    app.run(host=args.bind, port=args.port)


if __name__ == '__main__':
    main()
