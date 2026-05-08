"""
app/routes/fonts.py
Google Fonts benzeri font servis sistemi
Subdomain: fonts.yigitgulyurt.net.tr
"""

import os
import re
import time
from flask import Blueprint, render_template, request, Response, current_app, send_from_directory, abort

fonts_bp = Blueprint('fonts', __name__, subdomain='fonts')

# Global cache değişkenleri
_fonts_cache      = None
_fonts_cache_time = 0
CACHE_DURATION    = 300 # 5 dakika

# Font ağırlığı haritası
WEIGHT_MAP = {
    'Thin': '100',
    'ExtraLight': '200',
    'Light': '300',
    'Regular': '400',
    'Medium': '500',
    'SemiBold': '600',
    'Bold': '700',
    'ExtraBold': '800',
    'Black': '900'
}

# Font ailesi bilgilerini (isim + kategori) içeren eşleme
FONT_METADATA = {
    'amiri': {'name': 'Amiri', 'cat': 'Serif'},
    'cinzel': {'name': 'Cinzel', 'cat': 'Serif'},
    'crimsonpro': {'name': 'Crimson Pro', 'cat': 'Serif'},
    'jetbrainsmononerdfont': {'name': 'JetBrainsMonoNerdFont', 'cat': 'Monospace'},
    'montserrat': {'name': 'Montserrat', 'cat': 'Sans-Serif'},
    'orbitron': {'name': 'Orbitron', 'cat': 'Display'},
    'playfair': {'name': 'Playfair Display', 'cat': 'Serif'},
    'rajdhani': {'name': 'Rajdhani', 'cat': 'Sans-Serif'}
}

def get_fonts_data():
    """Font klasörünü tarar ve mevcut fontları döndürür (Cache destekli)."""
    global _fonts_cache, _fonts_cache_time
    
    now = time.time()
    if _fonts_cache and (now - _fonts_cache_time < CACHE_DURATION):
        return _fonts_cache

    fonts_dir = os.path.join(current_app.root_path, 'static', 'fonts')
    fonts = {}
    
    if not os.path.exists(fonts_dir):
        return fonts

    for family_name in os.listdir(fonts_dir):
        family_path = os.path.join(fonts_dir, family_name)
        if os.path.isdir(family_path):
            # Normalize edilmiş isim (küçük harf ve boşluksuz)
            normalized_name = family_name.lower().replace(" ", "").replace("-", "")
            
            # Metadata'dan bilgileri al
            meta = FONT_METADATA.get(normalized_name, {'name': family_name, 'cat': 'Sans-Serif'})
            display_name = meta['name']
            category = meta['cat']
            
            # Arama için display_name'i de normalize et
            normalized_display_name = display_name.lower().replace(" ", "").replace("-", "")
            
            font_variants = []
            for file in os.listdir(family_path):
                if file.endswith(('.ttf', '.woff2', '.woff')):
                    name_no_ext = os.path.splitext(file)[0]
                    
                    style = "normal"
                    if "Italic" in name_no_ext or "italic" in name_no_ext:
                        style = "italic"
                    
                    weight = "400"
                    for key, val in WEIGHT_MAP.items():
                        if key in name_no_ext:
                            weight = val
                            break
                    
                    font_variants.append({
                        'file': file,
                        'weight': weight,
                        'style': style,
                        'format': 'truetype' if file.endswith('.ttf') else ('woff2' if file.endswith('.woff2') else 'woff')
                    })
            
            if font_variants:
                font_entry = {
                    'original_name': family_name,
                    'display_name': display_name,
                    'category': category,
                    'variants': font_variants
                }
                # Hem klasör adıyla hem de güzel adıyla erişilebilir yap
                fonts[normalized_name] = font_entry
                if normalized_display_name != normalized_name:
                    fonts[normalized_display_name] = font_entry
    
    _fonts_cache = fonts
    _fonts_cache_time = now
    return fonts

@fonts_bp.route('/')
def index():
    """Fontların listelendiği ana sayfa."""
    fonts_data = get_fonts_data()
    # Tekilleştir ve Template için veriyi düzenle
    unique_fonts = {}
    for data in fonts_data.values():
        unique_fonts[data['display_name']] = {
            'variants': data['variants'],
            'category': data.get('category', 'Sans-Serif')
        }
    
    return render_template('fonts/index.html', fonts=unique_fonts)

@fonts_bp.route('/css2')
def css2():
    """
    Google Fonts benzeri CSS API'si.
    Örnek: /css2?family=Montserrat:ital,wght@0,100..900;1,100..900&display=swap
    """
    families_param = request.args.getlist('family')
    display = request.args.get('display', 'swap')
    
    if not families_param:
        return Response("/* No families specified */", mimetype='text/css')

    fonts_data = get_fonts_data()
    css_output = []
    
    # Base URL'i belirle (fonts subdomain'i üzerinden)
    base_url = f"https://fonts.{current_app.config.get('SERVER_NAME', 'yigitgulyurt.net.tr')}"

    for param in families_param:
        # Parametre formatı: FamilyName:ital,wght@0,100..900;1,100..900
        parts = param.split(':')
        raw_family_name = parts[0].strip()
        # Arama için normalize et
        search_name = raw_family_name.lower().replace(" ", "").replace("-", "")
        
        if search_name not in fonts_data:
            css_output.append(f"/* Font family '{raw_family_name}' not found (searched as '{search_name}') */")
            continue

        family_info = fonts_data[search_name]
        folder_name = family_info['original_name']
        display_name = family_info['display_name']
        available_variants = family_info['variants']

        requested_variants = []
        if len(parts) > 1:
            # Variantları ayıkla (ital,wght@...)
            variant_part = parts[1]
            if '@' in variant_part:
                header_str, values_str = variant_part.split('@')
                header_parts = header_str.split(',')
                
                for val_set in values_str.split(';'):
                    val_parts = val_set.split(',')
                    variant_req = {}
                    for i, h_part in enumerate(header_parts):
                        if i < len(val_parts):
                            val = val_parts[i]
                            if '..' in val:
                                try:
                                    start, end = val.split('..')
                                    variant_req[h_part] = list(range(int(start), int(end) + 1))
                                except ValueError:
                                    continue
                            else:
                                try:
                                    variant_req[h_part] = [int(val)]
                                except ValueError:
                                    continue
                    requested_variants.append(variant_req)
        
        for font in available_variants:
            font_weight = int(font['weight'])
            font_ital = 1 if font['style'] == 'italic' else 0
            
            # Eğer hiç variant istenmemişse tümünü getir
            if not requested_variants:
                include = True
            else:
                include = False
                for req in requested_variants:
                    ital_req = req.get('ital', [0, 1])
                    wght_req = req.get('wght', list(range(100, 1000, 100)))
                    
                    if font_ital in ital_req and font_weight in wght_req:
                        include = True
                        break
            
            if include:
                font_url = f"{base_url}/s/{folder_name}/{font['file']}"
                css_output.append(f"""
@font-face {{
  font-family: '{display_name}';
  font-style: {font['style']};
  font-weight: {font['weight']};
  font-display: {display};
  src: url('{font_url}') format('{font['format']}');
}}""")

    response = Response("\n".join(css_output), mimetype='text/css')
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

@fonts_bp.route('/s/<family>/<filename>')
def serve_font(family, filename):
    """Font dosyalarını servis eder."""
    fonts_dir = os.path.join(current_app.root_path, 'static', 'fonts', family)
    if not os.path.exists(os.path.join(fonts_dir, filename)):
        abort(404)
    
    response = send_from_directory(fonts_dir, filename)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    return response
