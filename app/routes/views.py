from flask import Blueprint, render_template, Response, url_for, current_app, request, jsonify, redirect, abort, flash, send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from app.models import Project, BlogPost, StreamConfig, QrRedirect, Admin, ContactMessage
from app import db
from datetime import datetime
import random
import string
import re
import os
import io
import markdown as md
import requests
from threading import Thread
from urllib.parse import urlparse, parse_qs
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont

# --- Blueprints ---
main_bp     = Blueprint('main', __name__)
blog_bp     = Blueprint('blog', __name__)
projects_bp = Blueprint('projects', __name__)
contact_bp  = Blueprint('contact', __name__)
admin_bp    = Blueprint('admin', __name__)
og_bp       = Blueprint('og', __name__)

# --- Helpers ---
def send_async_notification(app, name, email, subject, message):
    with app.app_context():
        send_admin_notification(name, email, subject, message)

def send_admin_notification(name, email, subject, message):
    telegram_token = current_app.config.get('TELEGRAM_TOKEN')
    admin_id       = current_app.config.get('ADMIN_TELEGRAM_ID')
    if telegram_token and admin_id:
        try:
            text = (f"📩 *Yeni İletişim Mesajı (yigitgulyurt.net.tr)*\n\n"
                    f"👤 *Gönderen:*   {name}\n"
                    f"📧 *E-posta:*   {email}\n"
                    f"📌 *Konu:*   {subject.capitalize() if subject else 'Yok'}\n\n"
                    f"📝 *Mesaj:*\n\n{message}")
            requests.post(
                f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                json={"chat_id": admin_id, "text": text, "parse_mode": "Markdown"},
                timeout=10,
            )
        except Exception as e:
            current_app.logger.error(f"Telegram notification error: {e}")

def generate_id(length=7):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def clean_slug(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\-_]', '', text)
    return text[:30]

def slugify(text):
    text = text.lower().strip()
    replacements = {"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u"}
    for tr, en in replacements.items():
        text = text.replace(tr, en)
    text = re.sub(r'[\s]+', '-', text)
    text = re.sub(r'[^\w\-]', '', text)
    return text

def extract_slug(url):
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        
        domain_map = {
            'youtube.com': 'yt', 'youtu.be': 'yt', 'twitch.tv': 'tv', 'vimeo.com': 'vm', 'netflix.com': 'nf',
            'twitter.com': 'tw', 'x.com': 'tw', 'instagram.com': 'ig', 'facebook.com': 'fb', 'fb.com': 'fb',
            'tiktok.com': 'tk', 'reddit.com': 'rd', 'linkedin.com': 'ln', 'pinterest.com': 'pin',
            'spotify.com': 'sp', 'open.spotify.com': 'sp', 'soundcloud.com': 'sc', 'music.apple.com': 'am',
            'github.com': 'gh', 'gitlab.com': 'gl', 'stackoverflow.com': 'so', 'codepen.io': 'cp',
            'medium.com': 'md', 'dev.to': 'dev', 'behance.net': 'be', 'dribbble.com': 'dr',
            'amazon.com': 'amz', 'amazon.com.tr': 'amz', 'wikipedia.org': 'wiki', 'discord.com': 'dc',
            'steamcommunity.com': 'st', 'steampowered.com': 'st', 't.me': 'tg', 'telegram.org': 'tg'
        }
        
        short_domain = domain_map.get(domain)
        if not short_domain:
            for d, code in domain_map.items():
                if domain.endswith('.' + d):
                    short_domain = code
                    break
        
        if not short_domain:
            short_domain = domain.split('.')[0][:10]
        
        qs = parse_qs(parsed.query)
        param_keys = ['v', 'id', 'p', 'slug', 'article', 'track', 'album', 's', 'post']
        for key in param_keys:
            if key in qs and qs[key]:
                val = qs[key][0]
                if len(val) >= 3:
                    return short_domain, clean_slug(val)
        
        path_parts = [p for p in parsed.path.split('/') if p]
        if path_parts:
            trigger_keywords = [
                'track', 'album', 'playlist', 'u', 'user', 'posts', 'p', 'watch', 
                'video', 'article', 'item', 'product', 'groups', 'community', 'channel'
            ]
            for i, part in enumerate(path_parts[:-1]):
                if part.lower() in trigger_keywords:
                    return short_domain, clean_slug(path_parts[i+1])
            
            last_segment = path_parts[-1]
            if '.' in last_segment:
                last_segment = last_segment.rsplit('.', 1)[0]
            
            if len(last_segment) >= 3:
                if last_segment.lower() in [short_domain.lower(), domain.split('.')[0].lower()]:
                    return short_domain, None
                return short_domain, clean_slug(last_segment)
                
        return short_domain, None
    except Exception:
        pass
    return "link", None

# --- Main Routes ---
@main_bp.route('/')
def index():
    featured_projects = Project.query.filter_by(featured=True).order_by(Project.order).limit(3).all()
    recent_posts = BlogPost.query.filter_by(published=True).order_by(BlogPost.created_at.desc()).limit(3).all()
    stats = {
        'projects': Project.query.count(),
        'posts': BlogPost.query.filter_by(published=True).count(),
    }
    stream_config = StreamConfig.get()
    show_stream = stream_config.show_section
    stream_live = False
    if show_stream:
        try:
            import requests as req_lib
            key = stream_config.stream_key or current_app.config.get('STREAM_KEY', '')
            r = req_lib.get('http://localhost:9997/v3/paths/list', timeout=1)
            items = r.json().get('items', [])
            path = next((p for p in items if p.get('name') == f'canli/{key}'), None)
            stream_live = bool(path and path.get('ready'))
        except Exception:
            stream_live = False

    return render_template('main/index.html',
                           featured_projects=featured_projects,
                           recent_posts=recent_posts,
                           stats=stats,
                           show_stream=show_stream,
                           stream_live=stream_live,
                           stream_config=stream_config)

@main_bp.route('/Mustafa-Kemal-Ataturk')
def ataturk():
    return render_template('main/ataturk.html')

@main_bp.route('/hakkimda')
def about():
    projects = Project.query.order_by(Project.order, Project.created_at.desc()).all()
    return render_template('main/about.html', projects=projects)

@main_bp.route('/cv')
def cv():
    projects = Project.query.order_by(Project.order, Project.created_at.desc()).all()
    return render_template('main/cv.html', projects=projects)

@main_bp.route('/sitemap.xml')
def sitemap():
    pages = []
    base = 'https://yigitgulyurt.net.tr'
    static_pages = [
        ('main.ataturk',   '0.8',  'monthly'),
        ('main.index',    '1.0',  'weekly'),
        ('main.about',    '0.8',  'monthly'),
        ('main.cv',       '0.7',  'monthly'),
        ('projects.index','0.9',  'weekly'),
        ('blog.index',    '0.9',  'weekly'),
        ('contact.index', '0.5',  'monthly'),
        ('main.qr_okuyucu', '0.8',  'monthly')
    ]
    for endpoint, priority, changefreq in static_pages:
        pages.append({
            'loc': base + url_for(endpoint),
            'priority': priority,
            'changefreq': changefreq,
            'lastmod': datetime.utcnow().strftime('%Y-%m-%d'),
        })
    for p in Project.query.all():
        pages.append({
            'loc': base + url_for('projects.detail', slug=p.slug),
            'priority': '0.8',
            'changefreq': 'monthly',
            'lastmod': p.created_at.strftime('%Y-%m-%d'),
        })
    for post in BlogPost.query.filter_by(published=True).all():
        pages.append({
            'loc': base + url_for('blog.detail', slug=post.slug),
            'priority': '0.7',
            'changefreq': 'monthly',
            'lastmod': post.updated_at.strftime('%Y-%m-%d'),
        })
    xml = render_template('main/sitemap.xml', pages=pages)
    return Response(xml, mimetype='application/xml')

@main_bp.route('/api/shorten', methods=['POST'])
def shorten():
    data = request.get_json(silent=True, force=True)
    if not data: return jsonify({'error': 'JSON parse edilemedi'}), 400
    url = data.get('url', '').strip()
    if not url: return jsonify({'error': 'URL gerekli'}), 400
    existing = QrRedirect.query.filter_by(url=url).first()
    if existing:
        return jsonify({'short_id': existing.id, 'short_domain': existing.short_domain or 'r'})
    short_domain_val, slug = extract_slug(url)
    if slug:
        short_id = slug
        if QrRedirect.query.get(short_id):
            short_id = f"{slug}-{generate_id(3)}"
            while QrRedirect.query.get(short_id):
                short_id = f"{slug}-{generate_id(3)}"
    else:
        short_id = generate_id()
        while QrRedirect.query.get(short_id):
            short_id = generate_id()
    redirect_obj = QrRedirect(id=short_id, short_domain=short_domain_val, url=url)
    db.session.add(redirect_obj)
    db.session.commit()
    return jsonify({'short_id': short_id, 'short_domain': short_domain_val})

@main_bp.route('/r/<short_id>')
@main_bp.route('/r/<short_domain>/<short_id>')
def redirect_url(short_id, short_domain=None):
    obj = QrRedirect.query.get_or_404(short_id)
    obj.hit_count += 1
    db.session.commit()
    return redirect(obj.url)

@main_bp.route('/qr-okuyucu')
def qr_okuyucu():
    return render_template('qr-reader/qr-reader.html')

@main_bp.route('/robots.txt')
def robots():
    content = "User-agent: *\nAllow: /\nDisallow: /admin/\n\nSitemap: https://yigitgulyurt.net.tr/sitemap.xml\n"
    return Response(content, mimetype='text/plain')

@main_bp.route('/font-test')
def font_test():
    return render_template('main/font-test.html')

@main_bp.route('/sw.js')
def serve_sw():
    version = "1.0.0"
    sw_path = os.path.join(current_app.root_path, '..', 'sw.js')
    try:
        with open(sw_path, 'r', encoding='utf-8') as f:
            content = f.read()
        content = content.replace('${VERSION}', version)
        resp = Response(content, mimetype='application/javascript; charset=utf-8')
        resp.headers['Cache-Control'] = 'no-cache'
        return resp
    except Exception:
        return "Service Worker Not Found", 404

@main_bp.route('/offline')
def offline():
    return render_template('main/offline.html')

# --- Blog Routes ---
@blog_bp.route('/')
def index():
    posts = BlogPost.query.filter_by(published=True).order_by(BlogPost.created_at.desc()).all()
    return render_template('blog/index.html', posts=posts)

@blog_bp.route('/<slug>')
def detail(slug):
    post = BlogPost.query.filter_by(slug=slug, published=True).first_or_404()
    post.content_html = md.markdown(post.content or '', extensions=['fenced_code', 'tables'])
    return render_template('blog/detail.html', post=post)

# --- Project Routes ---
@projects_bp.route('/')
def index():
    projects = Project.query.order_by(Project.order, Project.created_at.desc()).all()
    return render_template('projects/index.html', projects=projects)

@projects_bp.route('/<slug>')
def detail(slug):
    project = Project.query.filter_by(slug=slug).first_or_404()
    project.content_html = md.markdown(project.content or '', extensions=['fenced_code', 'tables'])
    return render_template('projects/detail.html', project=project)

# --- Contact Routes ---
@contact_bp.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name, email = request.form.get('name', '').strip(), request.form.get('email', '').strip()
        subject, message = request.form.get('subject', '').strip(), request.form.get('message', '').strip()
        if not name or not email or not message:
            flash('Lütfen zorunlu alanları doldurun.', 'error')
            return render_template('contact/index.html')
        msg = ContactMessage(name=name, email=email, subject=subject, message=message)
        db.session.add(msg)
        db.session.commit()
        
        # Telegram Bildirimi Gönder
        app = current_app._get_current_object()
        Thread(target=send_async_notification, args=(app, name, email, subject, message)).start()

        flash('Mesajınız alındı, teşekkürler!', 'success')
        return redirect(url_for('contact.index'))
    return render_template('contact/index.html')

# --- Admin Routes ---
@admin_bp.route('/giris', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('admin.dashboard'))
    if request.method == 'POST':
        user = Admin.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            return redirect(url_for('admin.dashboard'))
        flash('Hatalı kullanıcı adı veya şifre.', 'error')
    return render_template('admin/login.html')

@admin_bp.route('/cikis')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@admin_bp.route('/')
@login_required
def dashboard():
    stats = {
        'projects': Project.query.count(),
        'posts': BlogPost.query.count(),
        'messages': ContactMessage.query.filter_by(read=False).count(),
    }
    return render_template('admin/dashboard.html', stats=stats)

@admin_bp.route('/projeler')
@login_required
def projects():
    projects = Project.query.order_by(Project.order).all()
    return render_template('admin/projects.html', projects=projects)

@admin_bp.route('/projeler/yeni', methods=['GET', 'POST'])
@admin_bp.route('/projeler/<int:id>/duzenle', methods=['GET', 'POST'])
@login_required
def project_edit(id=None):
    project = Project.query.get_or_404(id) if id else Project()
    if request.method == 'POST':
        project.title = request.form['title']
        project.slug = request.form.get('slug') or slugify(request.form['title'])
        project.description = request.form.get('description')
        project.tech_stack = request.form.get('tech_stack')
        image_file = request.files.get('image')
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            upload_dir = os.path.join(current_app.root_path, 'static', 'img', 'projects')
            os.makedirs(upload_dir, exist_ok=True)
            image_file.save(os.path.join(upload_dir, filename))
            project.image = filename
        project.content, project.live_url = request.form.get('content'), request.form.get('live_url')
        project.github_url = request.form.get('github_url')
        project.featured, project.order = bool(request.form.get('featured')), int(request.form.get('order') or 0)
        if not id: db.session.add(project)
        db.session.commit()
        flash('Proje kaydedildi.', 'success')
        return redirect(url_for('admin.projects'))
    return render_template('admin/project_edit.html', project=project)

@admin_bp.route('/projeler/<int:id>/sil', methods=['POST'])
@login_required
def project_delete(id):
    project = Project.query.get_or_404(id)
    db.session.delete(project)
    db.session.commit()
    flash('Proje silindi.', 'success')
    return redirect(url_for('admin.projects'))

@admin_bp.route('/blog')
@login_required
def blog():
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template('admin/blog.html', posts=posts)

@admin_bp.route('/blog/yeni', methods=['GET', 'POST'])
@admin_bp.route('/blog/<int:id>/duzenle', methods=['GET', 'POST'])
@login_required
def post_edit(id=None):
    post = BlogPost.query.get_or_404(id) if id else BlogPost()
    if request.method == 'POST':
        post.title = request.form['title']
        post.slug = request.form.get('slug') or slugify(request.form['title'])
        post.summary, post.content = request.form.get('summary'), request.form.get('content')
        post.published = bool(request.form.get('published'))
        if not id: db.session.add(post)
        db.session.commit()
        flash('Yazı kaydedildi.', 'success')
        return redirect(url_for('admin.blog'))
    return render_template('admin/post_edit.html', post=post)

@admin_bp.route('/blog/<int:id>/sil', methods=['POST'])
@login_required
def post_delete(id):
    post = BlogPost.query.get_or_404(id)
    db.session.delete(post)
    db.session.commit()
    flash('Yazı silindi.', 'success')
    return redirect(url_for('admin.blog'))

@admin_bp.route('/preview', methods=['POST'])
@login_required
def preview():
    text = request.form.get('content', '')
    html = md.markdown(text, extensions=['fenced_code', 'tables'])
    return jsonify({'html': html})

@admin_bp.route('/yayin', methods=['GET', 'POST'])
@login_required
def stream_config():
    cfg = StreamConfig.get()
    if request.method == 'POST':
        new_key = request.form.get('stream_key', '').strip()
        if new_key: cfg.stream_key = new_key
        cfg.show_section = bool(request.form.get('show_section'))
        cfg.title, cfg.subtitle = request.form.get('title', '').strip() or 'Canlı Yayın', request.form.get('subtitle', '').strip()
        db.session.commit()
        flash('Yayın ayarları güncellendi.', 'success')
        return redirect(url_for('admin.stream_config'))
    return render_template('admin/stream_config.html', cfg=cfg)

@admin_bp.route('/izleyiciler')
@login_required
def stream_viewers():
    import json, time
    viewers = []
    try:
        import redis as redis_lib
        r = redis_lib.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'), decode_responses=True)
        keys = r.keys('yg_viewer:*')
        now = int(time.time())
        for key in keys:
            raw = r.get(key)
            if not raw: continue
            try:
                data = json.loads(raw)
                data['since'], data['ttl'] = now - data.get('last_seen', now), r.ttl(key)
                viewers.append(data)
            except Exception: pass
        viewers.sort(key=lambda x: x.get('last_seen', 0), reverse=True)
    except Exception: viewers = []
    return render_template('admin/stream_viewers.html', viewers=viewers)

@admin_bp.route('/mesajlar')
@login_required
def messages():
    msgs = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template('admin/messages.html', messages=msgs)

@admin_bp.route('/mesajlar/<int:id>')
@login_required
def message_detail(id):
    msg = ContactMessage.query.get_or_404(id)
    msg.read = True
    db.session.commit()
    return render_template('admin/message_detail.html', message=msg)

@admin_bp.route('/og')
@login_required
def og():
    return render_template('admin/showcase/og.html')

@admin_bp.route('/og/yigitgulyurt.net.tr')
@login_required
def yigitgulyurt_og():
    return render_template('admin/showcase/yigitgulyurt.html')

@admin_bp.route('/og/cagrivakti.com.tr')
@login_required
def cagrivakti_og():
    return render_template('admin/showcase/cagrivakti.html')

# --- OG Routes ---
THEMES = {
    'default': {'bg': '#0d0d0d', 'accent': '#4ade80', 'accent2': '#60a5fa', 'text': '#e2e2e2', 'text2': '#888888'},
    'live':    {'bg': '#0d0d0d', 'accent': '#f87171', 'accent2': '#60a5fa', 'text': '#e2e2e2', 'text2': '#888888'},
    'ataturk': {'bg': '#080808', 'accent': '#e30a17', 'accent2': '#c5a059', 'text': '#f0f0f0', 'text2': '#999999'},
    'blog':    {'bg': '#0d0d0d', 'accent': '#fb923c', 'accent2': '#fcd34d', 'text': '#e2e2e2', 'text2': '#888888'},
    'project': {'bg': '#0d0d0d', 'accent': '#818cf8', 'accent2': '#22d3ee', 'text': '#e2e2e2', 'text2': '#888888'},
    'contact': {'bg': '#051010', 'accent': '#10b981', 'accent2': '#2dd4bf', 'text': '#f9fafb', 'text2': '#94a3b8'},
    'about':   {'bg': '#0f172a', 'accent': '#a78bfa', 'accent2': '#f472b6', 'text': '#f8fafc', 'text2': '#94a3b8'},
    'cv':      {'bg': '#0f172a', 'accent': '#38bdf8', 'accent2': '#94a3b8', 'text': '#f1faee', 'text2': '#a8dadc'},
    'main':    {'bg': '#111827', 'accent': '#f59e0b', 'accent2': '#fbbf24', 'text': '#f9fafb', 'text2': '#9ca3af'},
    'qr':      {'bg': '#000000', 'accent': '#ffffff', 'accent2': '#888888', 'text': '#ffffff', 'text2': '#cccccc'},
}

FONT_BOLD = 'app/static/fonts/JetBrainsMonoNerdFont/JetBrainsMonoNerdFont-Bold.ttf'
FONT_REG  = 'app/static/fonts/JetBrainsMonoNerdFont/JetBrainsMonoNerdFont-Regular.ttf'
W, H, PAD, MARGIN = 1200, 630, 64, 40
DOM_PAD_X, DOM_PAD_Y, DOM_FONT_SZ, PROMPT_SZ, SUBTITLE_SZ = 16, 10, 20, 22, 26
BRACKET_LW, TITLE_SIZES = 2, (72, 58, 46, 36, 28)

def _hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _load_font(path, size):
    try: return ImageFont.truetype(path, size)
    except Exception: return ImageFont.load_default()

def _fit_title_font(draw, text, max_width):
    for size in TITLE_SIZES:
        font = _load_font(FONT_BOLD, size)
        if draw.textbbox((0, 0), text, font=font)[2] < max_width: return font, size
    return _load_font(FONT_BOLD, TITLE_SIZES[-1]), TITLE_SIZES[-1]

def _draw_bracket(draw, x1, y1, x2, y2, color):
    arm, lw = max(20, min(36, int((x2 - x1) * 0.18))), BRACKET_LW
    draw.rectangle([x1, y1, x1 + arm, y1 + lw], fill=color)
    draw.rectangle([x1, y1, x1 + lw, y1 + arm], fill=color)
    draw.rectangle([x2 - arm, y1, x2, y1 + lw], fill=color)
    draw.rectangle([x2 - lw, y1, x2, y1 + arm], fill=color)
    draw.rectangle([x1, y2 - lw, x1 + arm, y2], fill=color)
    draw.rectangle([x1, y2 - arm, x1 + lw, y2], fill=color)
    draw.rectangle([x2 - arm, y2 - lw, x2, y2], fill=color)
    draw.rectangle([x2 - lw, y2 - arm, x2, y2], fill=color)

def _draw_subtitle_multiline(draw, text, x, y, font, color, max_width, line_spacing=12):
    if '|' in text:
        line_h = draw.textbbox((0, 0), 'A', font=font)[3] + line_spacing
        for i, line in enumerate(text.split('|')): draw.text((x, y + i * line_h), line.strip(), font=font, fill=color)
        return
    words, line, cy = text.split(' '), '', y
    for word in words:
        test = (line + ' ' + word).strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width: line = test
        else:
            if line:
                draw.text((x, cy), line, font=font, fill=color)
                cy += draw.textbbox((0, 0), line, font=font)[3] + line_spacing
            line = word
    if line: draw.text((x, cy), line, font=font, fill=color)

def make_og(title, subtitle, theme, prompt, domain):
    t = THEMES.get(theme, THEMES['default'])
    img = Image.new('RGB', (W, H), _hex_to_rgb(t['bg']))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 3], fill=_hex_to_rgb(t['accent']))
    f_prompt = _load_font(FONT_REG, PROMPT_SZ)
    d.text((PAD, 48), prompt, font=f_prompt, fill=_hex_to_rgb(t['accent']))
    max_title_w = W - PAD * 2
    f_title, title_size = _fit_title_font(d, title, max_title_w)
    title_y = H // 2 - title_size - 16
    d.text((PAD, title_y), title, font=f_title, fill=_hex_to_rgb(t['text']))
    f_sub = _load_font(FONT_REG, SUBTITLE_SZ)
    _draw_subtitle_multiline(d, subtitle, PAD, title_y + title_size + 24, f_sub, _hex_to_rgb(t['text2']), max_title_w)
    f_domain = _load_font(FONT_REG, DOM_FONT_SZ)
    db = d.textbbox((0, 0), domain, font=f_domain)
    dw, dh = db[2] - db[0], db[3] - db[1]
    bx_w, bx_h = dw + DOM_PAD_X * 2, dh + DOM_PAD_Y * 2
    bx2, by2 = W - MARGIN, H - MARGIN
    bx1, by1 = bx2 - bx_w, by2 - bx_h
    d.text(((bx1 + bx2) / 2, (by1 + by2) / 2), domain, font=f_domain, fill=_hex_to_rgb(t['accent2']), anchor="mm")
    _draw_bracket(d, bx1, by1, bx2, by2, _hex_to_rgb(t['accent2']))
    return img

@lru_cache(maxsize=300)
def _cached_og(title, subtitle, theme, prompt, domain):
    img = make_og(title, subtitle, theme, prompt, domain)
    buf = io.BytesIO()
    img.save(buf, 'PNG', optimize=True)
    return buf.getvalue()

@og_bp.route('/og-image')
def og_image():
    title, subtitle, theme = request.args.get('title', 'Yiğit Gülyurt')[:80], request.args.get('subtitle', '')[:120], request.args.get('theme', 'default')
    icon, prompt, domain = request.args.get('icon', '')[:20], request.args.get('prompt', '$ whoami')[:60], request.args.get('domain', 'yigitgulyurt.net.tr')[:50]
    try:
        if icon and "\\" in icon: icon = icon.encode('utf-8').decode('unicode_escape').encode('utf-16', 'surrogatepass').decode('utf-16')
    except Exception: pass
    full_prompt = f"{icon} {prompt}".strip() if icon else prompt
    data = _cached_og(title, subtitle, theme, full_prompt, domain)
    resp = send_file(io.BytesIO(data), mimetype='image/png')
    resp.headers['Cache-Control'] = 'public, max-age=3600'
    return resp
