from celery import shared_task
from .models import Template
import logging
import redis
import os

logger = logging.getLogger(__name__)
REDIS_URL = os.getenv("REDIS_URL")
redis_client = redis.from_url(REDIS_URL)

@shared_task
def cache_template(template_id):
    try:
        template = Template.objects.get(id=template_id)
        cache_key = f"template:{template.template_code}:{template.language}:v{template.version}"
        redis_client.hmset(cache_key, {
            "subject": template.subject,
            "body": template.body,
            "version": template.version
        })
        redis_client.expire(cache_key, 3600)  # Cache expires in 1 hour
        logger.info(f"Template {template.template_code} cached successfully")
    except Template.DoesNotExist:
        logger.error(f"Template {template_id} not found for caching")

