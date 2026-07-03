"""
app/routes/font.py
Google Fonts benzeri font servis sistemi
Subdomain: yigitgulyurt.net.tr/font
"""

import os
import re
import time
from flask import Blueprint, render_template, request, Response, current_app, send_from_directory, abort, jsonify

font_bp = Blueprint('font', __name__)

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
    'playfair': {'name': 'Playfair', 'cat': 'Serif'},
    'rajdhani': {'name': 'Rajdhani', 'cat': 'Sans-Serif'},
    'noto_sans_old_turkic': {'name': 'Noto Sans Old Turkic', 'cat': 'Sans-Serif'},
    'gokturkfont': {'name': 'Gokturk Font', 'cat': 'Sans-Serif'}
    
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

@font_bp.route('/')
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

@font_bp.route('/cssy')
def cssy():
    """
    Google Fonts benzeri CSS API'si.
    Örnek: /cssy?family=Montserrat:ital,wght@0,100..900;1,100..900&display=swap 
    """
    families_param = request.args.getlist('family')
    display = request.args.get('display', 'swap')
    
    if not families_param:
        return Response("/* No families specified */", mimetype='text/css')

    fonts_data = get_fonts_data()
    css_output = []
    
    # Base URL'i belirle (url prefix üzerinden)
    base_url = f"https://{current_app.config.get('SERVER_NAME', 'yigitgulyurt.net.tr')}/font"

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
                font_url = f"{base_url}/{folder_name}/{font['file']}"
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

@font_bp.route('/<family>/<filename>')
def serve_font(family, filename):
    """Font dosyalarını servis eder."""
    fonts_dir = os.path.join(current_app.root_path, 'static', 'fonts', family)
    if not os.path.exists(os.path.join(fonts_dir, filename)):
        abort(404)
    
    response = send_from_directory(fonts_dir, filename)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    return response

@font_bp.route('/api/fonts')
def api_fonts():
    """
    Yapay zekalar ve crawler'lar için JSON API endpoint'i.
    Tüm fontları ve varyantlarını yapılandırılmış formatta döndürür.
    
    Query Parametreleri:
    - search: Font ismine göre arama (ör: ?search=montserrat)
    - category: Kategoriye göre filtreleme (ör: ?category=Sans-Serif)
    - weight: Ağırlığa göre filtreleme (ör: ?weight=400 veya ?weight=400,700)
    - style: Stile göre filtreleme (ör: ?style=italic veya ?style=normal,italic)
    - page: Sayfa numarası (ör: ?page=2)
    - per_page: Sayfa başına font sayısı (varsayılan: 50, maks: 100)
    """
    fonts_data = get_fonts_data()
    
    # Query parametrelerini al
    search_query = request.args.get('search', '').lower().strip()
    category_filter = request.args.get('category', '').strip()
    weight_filter = request.args.get('weight', '').strip()
    style_filter = request.args.get('style', '').strip()
    page = max(1, int(request.args.get('page', 1)))
    per_page = min(100, max(1, int(request.args.get('per_page', 50))))
    
    # Tekilleştir
    unique_families = {}
    for data in fonts_data.values():
        unique_families[data['display_name']] = data
    
    all_families = list(unique_families.items())
    
    # Filtreleme uygula
    filtered_families = []
    for display_name, data in all_families:
        # Arama filtresi
        if search_query:
            if search_query not in display_name.lower() and search_query not in data['original_name'].lower():
                continue
        
        # Kategori filtresi
        if category_filter:
            if data.get('category', 'Sans-Serif') != category_filter:
                continue
        
        # Ağırlık filtresi
        if weight_filter:
            weights = [w.strip() for w in weight_filter.split(',')]
            has_matching_weight = any(v['weight'] in weights for v in data['variants'])
            if not has_matching_weight:
                continue
        
        # Stil filtresi
        if style_filter:
            styles = [s.strip().lower() for s in style_filter.split(',')]
            has_matching_style = any(v['style'].lower() in styles for v in data['variants'])
            if not has_matching_style:
                continue
        
        filtered_families.append((display_name, data))
    
    # Sayfalama
    total_items = len(filtered_families)
    total_pages = (total_items + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_families = filtered_families[start_idx:end_idx]
    
    # Formatı düzenle
    fonts_list = []
    for display_name, data in paginated_families:
        font_entry = {
            'family_name': display_name,
            'family_slug': data['original_name'].lower().replace(' ', '-'),
            'category': data.get('category', 'Sans-Serif'),
            'folder_name': data['original_name'],
            'total_variants': len(data['variants']),
            'available_weights': sorted(list(set(int(v['weight']) for v in data['variants']))),
            'available_styles': sorted(list(set(v['style'] for v in data['variants']))),
            'available_formats': sorted(list(set(v['format'] for v in data['variants']))),
            'variants': [],
            'api_detail_url': f"https://{current_app.config.get('SERVER_NAME', 'yigitgulyurt.net.tr')}/font/api/fonts/{data['original_name']}"
        }
        
        for variant in data['variants']:
            font_entry['variants'].append({
                'weight': variant['weight'],
                'weight_name': next((k for k, v in WEIGHT_MAP.items() if v == variant['weight']), 'Regular'),
                'style': variant['style'],
                'format': variant['format'],
                'file': variant['file'],
                'url': f"https://{current_app.config.get('SERVER_NAME', 'yigitgulyurt.net.tr')}/font/{data['original_name']}/{variant['file']}"
            })
        
        fonts_list.append(font_entry)
    
    # Sonuç
    result = {
        'api_version': '1.0',
        'metadata': {
            'total_families': total_items,
            'total_pages': total_pages,
            'current_page': page,
            'per_page': per_page,
            'has_next': page < total_pages,
            'has_prev': page > 1,
            'generated_at': int(time.time()),
            'cache_duration': CACHE_DURATION
        },
        'filters': {
            'search': search_query if search_query else None,
            'category': category_filter if category_filter else None,
            'weight': weight_filter if weight_filter else None,
            'style': style_filter if style_filter else None
        },
        'available_categories': sorted(list(set(data.get('category', 'Sans-Serif') for _, data in all_families))),
        'available_weights': sorted(list(WEIGHT_MAP.values())),
        'available_styles': ['normal', 'italic'],
        'fonts': fonts_list,
        'pagination': {
            'next_url': f"https://{current_app.config.get('SERVER_NAME', 'yigitgulyurt.net.tr')}/font/api/fonts?page={page + 1}&per_page={per_page}" if page < total_pages else None,
            'prev_url': f"https://{current_app.config.get('SERVER_NAME', 'yigitgulyurt.net.tr')}/font/api/fonts?page={page - 1}&per_page={per_page}" if page > 1 else None
        }
    }
    
    response = jsonify(result)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Cache-Control'] = 'public, max-age=300'
    return response

@font_bp.route('/api/fonts/<family_slug>')
def api_font_detail(family_slug):
    """
    Tek bir font ailesi için detaylı endpoint.
    
    Parametreler:
    - family_slug: Font klasör adı (ör: montserrat)
    """
    fonts_data = get_fonts_data()
    
    # Normalize edilmiş isimle ara
    search_name = family_slug.lower().replace(" ", "").replace("-", "")
    
    if search_name not in fonts_data:
        return jsonify({
            'error': 'Font not found',
            'family_slug': family_slug
        }), 404
    
    data = fonts_data[search_name]
    
    font_entry = {
        'family_name': data['display_name'],
        'family_slug': data['original_name'].lower().replace(' ', '-'),
        'category': data.get('category', 'Sans-Serif'),
        'folder_name': data['original_name'],
        'total_variants': len(data['variants']),
        'available_weights': sorted(list(set(int(v['weight']) for v in data['variants']))),
        'available_styles': sorted(list(set(v['style'] for v in data['variants']))),
        'available_formats': sorted(list(set(v['format'] for v in data['variants']))),
        'css_url': f"https://{current_app.config.get('SERVER_NAME', 'yigitgulyurt.net.tr')}/font/cssy?family={data['display_name'].replace(' ', '+')}",
        'variants': []
    }
    
    for variant in data['variants']:
        font_entry['variants'].append({
            'weight': variant['weight'],
            'weight_name': next((k for k, v in WEIGHT_MAP.items() if v == variant['weight']), 'Regular'),
            'style': variant['style'],
            'format': variant['format'],
            'file': variant['file'],
            'url': f"https://{current_app.config.get('SERVER_NAME', 'yigitgulyurt.net.tr')}/font/{data['original_name']}/{variant['file']}",
            'css_face': f"https://{current_app.config.get('SERVER_NAME', 'yigitgulyurt.net.tr')}/font/cssy?family={data['display_name'].replace(' ', '+')}:{variant['style']},wght@{variant['weight']}"
        })
    
    response = jsonify(font_entry)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Cache-Control'] = 'public, max-age=300'
    return response

@font_bp.route('/api/schema')
def api_schema():
    """
    API'nin OpenAPI benzeri şema dokümantasyonu.
    Yapay zekalar için API yapısını anlamak için kullanılır.
    """
    schema = {
        'openapi': '3.0.0',
        'info': {
            'title': 'Font Service API',
            'version': '1.0.0',
            'description': 'Google Fonts benzeri font servisi için REST API',
            'contact': {
                'url': 'https://yigitgulyurt.net.tr'
            }
        },
        'servers': [
            {
                'url': f"https://{current_app.config.get('SERVER_NAME', 'yigitgulyurt.net.tr')}/font"
            }
        ],
        'paths': {
            '/api/fonts': {
                'get': {
                    'summary': 'Tüm fontları listele',
                    'description': 'Tüm font ailelerini ve varyantlarını döndürür. Filtreleme ve sayfalama destekler.',
                    'parameters': [
                        {
                            'name': 'search',
                            'in': 'query',
                            'description': 'Font ismine göre arama',
                            'required': False,
                            'schema': {
                                'type': 'string'
                            }
                        },
                        {
                            'name': 'category',
                            'in': 'query',
                            'description': 'Kategoriye göre filtreleme (Sans-Serif, Serif, Monospace, Display)',
                            'required': False,
                            'schema': {
                                'type': 'string'
                            }
                        },
                        {
                            'name': 'weight',
                            'in': 'query',
                            'description': 'Ağırlığa göre filtreleme (örn: 400 veya 400,700',
                            'required': False,
                            'schema': {
                                'type': 'string'
                            }
                        },
                        {
                            'name': 'style',
                            'in': 'query',
                            'description': 'Stile göre filtreleme (normal, italic)',
                            'required': False,
                            'schema': {
                                'type': 'string'
                            }
                        },
                        {
                            'name': 'page',
                            'in': 'query',
                            'description': 'Sayfa numarası',
                            'required': False,
                            'schema': {
                                'type': 'integer',
                                'default': 1
                            }
                        },
                        {
                            'name': 'per_page',
                            'in': 'query',
                            'description': 'Sayfa başına font sayısı',
                            'required': False,
                            'schema': {
                                'type': 'integer',
                                'default': 50,
                                'minimum': 1,
                                'maximum': 100
                            }
                        }
                    ]
                }
            },
            '/api/fonts/{family_slug}': {
                'get': {
                    'summary': 'Tek font detayı',
                    'description': 'Belirli bir font ailesinin detaylı bilgisini döndürür',
                    'parameters': [
                        {
                            'name': 'family_slug',
                            'in': 'path',
                            'description': 'Font klasör adı',
                            'required': True,
                            'schema': {
                                'type': 'string'
                            }
                        }
                    ]
                }
            },
            '/cssy': {
                'get': {
                    'summary': 'Google Fonts benzeri CSS API',
                    'description': 'CSS @font-face kurallarını üretir'
                }
            }
        },
        'components': {
            'schemas': {
                'FontFamily': {
                    'type': 'object',
                    'properties': {
                        'family_name': {'type': 'string'},
                        'family_slug': {'type': 'string'},
                        'category': {'type': 'string'},
                        'folder_name': {'type': 'string'},
                        'total_variants': {'type': 'integer'},
                        'available_weights': {'type': 'array', 'items': {'type': 'integer'}},
                        'available_styles': {'type': 'array', 'items': {'type': 'string'}},
                        'available_formats': {'type': 'array', 'items': {'type': 'string'}},
                        'variants': {'type': 'array', 'items': {'$ref': '#/components/schemas/FontVariant'}},
                        'api_detail_url': {'type': 'string'}
                    }
                },
                'FontVariant': {
                    'type': 'object',
                    'properties': {
                        'weight': {'type': 'string'},
                        'weight_name': {'type': 'string'},
                        'style': {'type': 'string'},
                        'format': {'type': 'string'},
                        'file': {'type': 'string'},
                        'url': {'type': 'string'}
                    }
                }
            }
        }
    }
    
    response = jsonify(schema)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Cache-Control'] = 'public, max-age=300'
    return response
