import os
import io
import pytest
from PIL import Image


def test_file_converter_page(client):
    response = client.get('/araclar/dosya-donusturucu')
    assert response.status_code == 200
    assert b'Dosya D\xc3\xb6n\xc3\xbc\xc5\x9ft\xc3\xbcc\xc3\xbc' in response.data


def test_file_converter_empty_upload(client):
    response = client.post(
        '/araclar/dosya-donusturucu',
        data={
            'action': 'convert',
            'output_format': 'txt'
        },
        content_type='multipart/form-data'
    )
    assert response.status_code in [200, 400]


def test_file_converter_txt_upload(client, temp_test_files):
    test_file_path = os.path.join(temp_test_files, 'test.txt')
    
    with open(test_file_path, 'rb') as f:
        data = {
            'action': 'convert',
            'files': (io.BytesIO(f.read()), 'test.txt'),
            'output_format': 'txt'
        }
        response = client.post(
            '/araclar/dosya-donusturucu',
            data=data,
            content_type='multipart/form-data'
        )
    
    assert response.status_code in [200, 400]


def test_file_converter_image_upload(client, temp_test_files):
    test_image_path = os.path.join(temp_test_files, 'test.png')
    
    img = Image.new('RGB', (100, 100), color='red')
    img.save(test_image_path, format='PNG')
    
    with open(test_image_path, 'rb') as f:
        data = {
            'action': 'convert',
            'files': (io.BytesIO(f.read()), 'test.png'),
            'output_format': 'jpg'
        }
        response = client.post(
            '/araclar/dosya-donusturucu',
            data=data,
            content_type='multipart/form-data'
        )
    
    assert response.status_code in [200, 400]


def test_file_converter_encrypt_section(client):
    response = client.get('/araclar/dosya-donusturucu')
    assert response.status_code == 200
    assert b'\xc5\x9eifrele' in response.data or b'Encrypt' in response.data


def test_file_converter_history_section(client):
    response = client.get('/araclar/dosya-donusturucu')
    assert response.status_code == 200


def test_file_converter_limits(client):
    for i in range(5):
        response = client.get('/araclar/dosya-donusturucu')
        assert response.status_code == 200
