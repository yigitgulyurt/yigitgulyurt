from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


# --- Auth ---

class Admin(UserMixin, db.Model):
    __tablename__ = 'admins'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))


# --- Projects ---

class Project(db.Model):
    __tablename__ = 'projects'
    id            = db.Column(db.Integer, primary_key=True)
    title         = db.Column(db.String(128), nullable=False)
    slug          = db.Column(db.String(128), unique=True, nullable=False)
    description   = db.Column(db.Text)
    tech_stack    = db.Column(db.String(256))   # virgülle ayrılmış: "Flask, nginx, Redis"
    live_url      = db.Column(db.String(256))
    github_url    = db.Column(db.String(256))
    image         = db.Column(db.String(256))        # static/img/ altındaki dosya adı
    content       = db.Column(db.Text)                   # Markdown — detay sayfası
    featured      = db.Column(db.Boolean, default=False)
    order         = db.Column(db.Integer, default=0)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def tech_list(self):
        return [t.strip() for t in (self.tech_stack or '').split(',') if t.strip()]

    def __repr__(self):
        return f'<Project {self.title}>'


# --- Blog ---

class BlogPost(db.Model):
    __tablename__ = 'blog_posts'
    id            = db.Column(db.Integer, primary_key=True)
    title         = db.Column(db.String(256), nullable=False)
    slug          = db.Column(db.String(256), unique=True, nullable=False)
    summary       = db.Column(db.String(512))
    content       = db.Column(db.Text)             # Markdown
    published     = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<BlogPost {self.slug}>'


# --- Contact ---

class ContactMessage(db.Model):
    __tablename__ = 'contact_messages'
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(128), nullable=False)
    email         = db.Column(db.String(256), nullable=False)
    subject       = db.Column(db.String(256))
    message       = db.Column(db.Text, nullable=False)
    read          = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ContactMessage from {self.email}>'



# --- Stream Config ---

class StreamConfig(db.Model):
    __tablename__ = 'stream_config'
    id            = db.Column(db.Integer, primary_key=True)
    title         = db.Column(db.String(256), default='Canlı Yayın')
    subtitle      = db.Column(db.String(256), default='')
    stream_key    = db.Column(db.String(256), default='')
    show_section  = db.Column(db.Boolean, default=False)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def get():
        import os
        cfg = StreamConfig.query.first()
        if not cfg:
            cfg = StreamConfig(
                stream_key=os.environ.get('STREAM_KEY', ''),
                show_section=os.environ.get('SHOW_STREAM_SECTION', 'false').lower() == 'true',
            )
            db.session.add(cfg)
            db.session.commit()
        return cfg


# --- QR Redirect ---

class QrRedirect(db.Model):
    __tablename__ = 'qr_redirect'
    id            = db.Column(db.String(20), primary_key=True) # Uzunluğu artırdık
    short_domain  = db.Column(db.String(20), index=True) # Yeni alan
    url           = db.Column(db.Text, nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    hit_count     = db.Column(db.Integer, default=0)


# --- IP Logs ---

class IpLog(db.Model):
    __tablename__ = 'ip_logs'
    id            = db.Column(db.Integer, primary_key=True)
    ip            = db.Column(db.String(45), nullable=False) # IPv6 support
    city          = db.Column(db.String(128))
    region        = db.Column(db.String(128))
    country       = db.Column(db.String(128))
    org           = db.Column(db.String(256))
    asn           = db.Column(db.String(64))
    latitude      = db.Column(db.Float)
    longitude     = db.Column(db.Float)
    timezone      = db.Column(db.String(128))
    user_agent    = db.Column(db.Text)
    full_data     = db.Column(db.JSON) # Store the whole JSON for future use
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<IpLog {self.ip} at {self.created_at}>'

