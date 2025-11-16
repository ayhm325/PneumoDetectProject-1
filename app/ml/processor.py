import logging
from io import BytesIO
import torch
from transformers import AutoProcessor, AutoModelForImageClassification
from PIL import Image
import numpy as np
import cv2

logger = logging.getLogger(__name__)

# تفعيل وضع GPU إذا كان متاحاً
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f'🖥️  جهاز المعالجة: {DEVICE}')


class MLProcessor:
    """معالج التعلم الآلي لتحليل صور الأشعة السينية."""
    
    def __init__(self):
        self.processor = None
        self.model = None
        self.LABELS = ["NORMAL", "PNEUMONIA"]
        self.EXPLANATIONS = {
            'NORMAL': {
                'ar': 'الصورة طبيعية. لا يوجد دليل على التهاب رئوي.',
                'en': 'The image is normal. No evidence of pneumonia.'
            },
            'PNEUMONIA': {
                'ar': 'تم الكشف عن التهاب رئوي. يُرجى استشارة الطبيب للمراجعة.',
                'en': 'Pneumonia detected. Please consult a doctor for review.'
            }
        }
        self.is_loaded = False

    def load_model(self, model_repo, hf_token=None):
        """تحميل المعالج والنموذج ونقله إلى وحدة المعالجة."""
        try:
            logger.info(f'🔄 جاري تحميل النموذج من: {model_repo}')
            logger.info(f'📱 جهاز المعالجة: {DEVICE}')
            
            # تحميل المعالج والنموذج
            self.processor = AutoProcessor.from_pretrained(model_repo, token=hf_token)
            self.model = AutoModelForImageClassification.from_pretrained(model_repo, token=hf_token)
            
            # نقل النموذج إلى الجهاز المحدد
            self.model.to(DEVICE)
            self.model.eval()
            
            # التأكد من ترتيب التسميات
            if self.model.config.id2label:
                self.LABELS = [self.model.config.id2label.get(i) for i in range(len(self.model.config.id2label))]
            
            self.is_loaded = True
            logger.info(f'✅ تم تحميل النموذج بنجاح على {DEVICE}')
            logger.info(f'📊 التسميات: {self.LABELS}')
            
        except Exception as e:
            logger.error(f'❌ فشل تحميل النموذج: {e}', exc_info=True)
            self.model = None
            self.is_loaded = False
            raise

    @torch.no_grad()
    def analyze_image(self, image_bytes):
        """
        إجراء التحليل الأساسي للصورة.
        
        المعاملات:
            image_bytes: بايتات الصورة
        
        الإرجاع:
            dict: النتيجة والثقة والشرح والصورة
        """
        if self.model is None:
            raise Exception('Model is not loaded or available.')
        
        if not isinstance(image_bytes, bytes):
            raise ValueError('image_bytes must be bytes')
        
        if len(image_bytes) == 0:
            raise ValueError('image_bytes is empty')
        
        try:
            # 1. معالجة الصورة
            image = Image.open(BytesIO(image_bytes)).convert('RGB')
            
            # التحقق من حجم الصورة
            if image.size[0] < 50 or image.size[1] < 50:
                raise ValueError('الصورة صغيرة جداً')
            
            # 2. إدخال النموذج
            inputs = self.processor(images=image, return_tensors="pt").to(DEVICE)
            
            # 3. التنبؤ
            outputs = self.model(**inputs)
            logits = outputs.logits
            
            # 4. حساب الثقة والنتيجة
            probabilities = torch.softmax(logits, dim=1)[0]
            confidence, predicted_index = torch.max(probabilities, 0)
            
            label = self.LABELS[predicted_index.item()]
            confidence_percent = round(confidence.item() * 100, 2)
            
            logger.info(f'✅ تحليل ناجح: {label} ({confidence_percent}%)')
            
            return {
                'result': label,
                'confidence': confidence_percent,
                'explanation': self.EXPLANATIONS.get(label, self.EXPLANATIONS['NORMAL']),
                'image_pil': image,
                'probabilities': {
                    'NORMAL': round(probabilities[0].item() * 100, 2),
                    'PNEUMONIA': round(probabilities[1].item() * 100, 2)
                }
            }
            
        except Exception as e:
            logger.error(f'خطأ في تحليل الصورة: {str(e)}', exc_info=True)
            raise

    def compute_saliency_map(self, image_pil):
        """
        حساب خريطة الإبراز (Saliency Map) باستخدام تقنية Gradient.
        
        المعاملات:
            image_pil: صورة PIL
        
        الإرجاع:
            PIL.Image: خريطة الإبراز
        """
        if self.model is None or not image_pil:
            logger.warning('لم يتم حساب خريطة الإبراز: النموذج غير محمل')
            return None
        
        try:
            # 1. إعداد الإدخال
            image = image_pil.copy()
            inputs = self.processor(images=image, return_tensors="pt").to(DEVICE)
            inputs['pixel_values'].requires_grad_(True)
            
            # 2. حساب الـ Gradient
            self.model.zero_grad()
            outputs = self.model(**inputs)
            predicted_index = outputs.logits.argmax(dim=1)
            target_score = outputs.logits[0, predicted_index]
            target_score.backward()
            
            # 3. الحصول على التدرجات
            gradients = inputs['pixel_values'].grad.abs().squeeze(0).cpu().numpy()
            saliency = np.sum(gradients, axis=0)
            
            # 4. تسوية الخريطة
            saliency_min = saliency.min()
            saliency_max = saliency.max()
            
            if saliency_max - saliency_min == 0:
                saliency_map = np.zeros_like(saliency)
            else:
                saliency_map = (saliency - saliency_min) / (saliency_max - saliency_min)
            
            # 5. تحويلها إلى خريطة حرارة
            saliency_map = (saliency_map * 255).astype(np.uint8)
            saliency_map_resized = cv2.resize(saliency_map, image_pil.size)
            heatmap = cv2.applyColorMap(saliency_map_resized, cv2.COLORMAP_JET)
            
            # 6. دمج مع الصورة الأصلية
            image_cv = np.array(image_pil.convert('RGB'))
            image_cv = cv2.cvtColor(image_cv, cv2.COLOR_RGB2BGR)
            
            alpha = 0.5
            overlay = cv2.addWeighted(image_cv, 1 - alpha, heatmap, alpha, 0)
            
            # 7. تحويل النتيجة إلى PIL
            overlay_pil = Image.fromarray(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB))
            
            logger.info('✅ تم حساب خريطة الإبراز بنجاح')
            return overlay_pil
            
        except Exception as e:
            logger.error(f'خطأ في حساب خريطة الإبراز: {str(e)}', exc_info=True)
            return None
    
    def get_model_info(self):
        """الحصول على معلومات النموذج."""
        if not self.is_loaded:
            return {'error': 'Model not loaded'}
        
        return {
            'labels': self.LABELS,
            'device': str(DEVICE),
            'is_loaded': self.is_loaded,
            'model_config': {
                'num_labels': self.model.config.num_labels if hasattr(self.model.config, 'num_labels') else None
            }
        }