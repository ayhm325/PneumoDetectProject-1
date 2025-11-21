import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app import create_app, db
from app.models import AnalysisResult

app = create_app()

missing = []
with app.app_context():
    results = AnalysisResult.query.all()
    upload_root = app.config.get('UPLOAD_FOLDER') or 'uploads'
    for result in results:
        print(f'Analysis ID: {result.id}')
        print(f'  image_path: {result.image_path}')
        img_path = os.path.join(upload_root, result.image_path) if result.image_path else None
        print(f'  Full image path: {img_path}')
        print(f'  Exists: {os.path.exists(img_path) if img_path else False}')
        sal_path = os.path.join(upload_root, result.saliency_path) if result.saliency_path else None
        print(f'  saliency_path: {result.saliency_path}')
        print(f'  Full saliency path: {sal_path}')
        print(f'  Exists: {os.path.exists(sal_path) if sal_path else False}')
        if img_path and not os.path.exists(img_path):
            missing.append(f'Original missing for analysis {result.id}: {img_path}')
        if sal_path and not os.path.exists(sal_path):
            missing.append(f'Saliency missing for analysis {result.id}: {sal_path}')

if not missing:
    print('All analysis images are present.')
else:
    print('Missing files:')
    for m in missing:
        print(m)
