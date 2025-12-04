from django.db import models
import re

class Template(models.Model):
    template_code = models.CharField(max_length=100)
    language = models.CharField(max_length=10, default="en")
    subject = models.CharField(max_length=255)
    body = models.TextField()
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("template_code", "language", "version")
        ordering = ['-version']

    def __str__(self):
        return f"{self.template_code} v{self.version} ({self.language})"
    
    def substitute_variables(self, variables):
        # Replace template variables like {{name}} with actual values
        subject = self.subject
        body = self.body
        
        for key, value in variables.items():
            pattern = r'{{\s*' + re.escape(key) + r'\s*}}'
            subject = re.sub(pattern, str(value), subject)
            body = re.sub(pattern, str(value), body)
        
        return {'subject': subject, 'body': body}

