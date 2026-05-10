"""
app/routes/image.py
Görsel servis sistemi
Subdomain: image.yigitgulyurt.net.tr
"""

import os
from flask import Blueprint, request, Response, current_app, send_from_directory, abort

image_bp = Blueprint('image', __name__, subdomain='image')


@image_bp.route('/<path:filename>')
def serve_image(filename):
    """Görsel dosyalarını servis eder."""
    images_dir = os.path.join(current_app.root_path, 'static', 'img')
    if not os.path.exists(os.path.join(images_dir, filename)):
        abort(404)
    
    response = send_from_directory(images_dir, filename)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    return response
