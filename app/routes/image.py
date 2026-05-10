"""
app/routes/image.py
Görsel servis sistemi
Subdomain: image.yigitgulyurt.net.tr
"""

import os
from flask import Blueprint, request, Response, current_app, send_from_directory, abort, render_template, url_for
from flask_login import login_required

image_bp = Blueprint('image', __name__, subdomain='image')

ALLOWED_IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.ico', '.bmp')


def get_size_str(size_bytes):
    """Byte cinsinden boyutu okunabilir hale getirir."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def safe_join(img_dir, *paths):
    """Güvenli yol birleştirme ve img dizini dışına çıkış kontrolü."""
    full_path = os.path.abspath(os.path.join(img_dir, *paths))
    if not full_path.startswith(os.path.abspath(img_dir)):
        abort(403)
    return full_path


def list_items(img_dir, current_path=''):
    """Belirtilen dizindeki dosya ve klasörleri listeler."""
    full_path = safe_join(img_dir, current_path)
    items = []

    if not os.path.exists(full_path) or not os.path.isdir(full_path):
        return items

    try:
        dir_contents = os.listdir(full_path)
    except Exception:
        return items

    # Önce klasörler, sonra dosyalar (alfabetik)
    dir_contents.sort(key=lambda x: (not os.path.isdir(os.path.join(full_path, x)), x.lower()))

    for item_name in dir_contents:
        if item_name.startswith('.'):  # Gizli dosyaları atla
            continue

        item_full_path = os.path.join(full_path, item_name)
        is_dir = os.path.isdir(item_full_path)
        rel_path = os.path.join(current_path, item_name).replace('\\', '/')

        if is_dir:
            items.append({
                'name': item_name,
                'path': rel_path,
                'is_folder': True
            })
        else:
            if item_name.lower().endswith(ALLOWED_IMAGE_EXTENSIONS):
                try:
                    stats = os.stat(item_full_path)
                    items.append({
                        'name': item_name,
                        'path': rel_path,
                        'is_folder': False,
                        'size': get_size_str(stats.st_size)
                    })
                except Exception:
                    continue

    return items


def build_breadcrumb(current_path):
    """Dizin yolu için breadcrumb oluşturur."""
    if not current_path:
        return []

    breadcrumb = []
    parts = current_path.split('/')
    accumulated_path = []

    for part in parts:
        if not part:
            continue
        accumulated_path.append(part)
        breadcrumb.append({
            'name': part,
            'path': '/'.join(accumulated_path)
        })

    return breadcrumb


# En özel rotalar önce
@image_bp.route('/file/<path:filename>')
def serve_image(filename):
    """Görsel dosyalarını servis eder."""
    images_dir = os.path.join(current_app.root_path, 'static', 'img')
    full_path = safe_join(images_dir, filename)
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        abort(404)
    
    response = send_from_directory(os.path.dirname(full_path), os.path.basename(full_path))
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    return response


@image_bp.route('/browse/<path:path>')
@image_bp.route('/')
@login_required
def index(path=''):
    """Görsel galeri ana sayfası (korumalı)."""
    img_dir = os.path.join(current_app.root_path, 'static', 'img')
    items = list_items(img_dir, path)
    breadcrumb = build_breadcrumb(path)
    total_items = len(items)

    return render_template('images/index.html',
                           items=items,
                           breadcrumb=breadcrumb,
                           total_items=total_items)

