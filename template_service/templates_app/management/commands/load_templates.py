from django.core.management.base import BaseCommand
from templates_app.models import Template

class Command(BaseCommand):
    help = 'Load default email templates'

    def handle(self, *args, **options):
        templates = [
            {
                'template_code': 'welcome_email',
                'subject': 'Welcome to Distributed Notification System!',
                'body': '''Hi {{name}},
                \n Welcome to our Distributed Notification System! Your account has been created successfully. 
                Account Details:
                \n- Email: {{email}}
                \n- Registration Date: {{registration_date}}
                \n You can now start receiving notifications through your preferred channels.
                \n\n Best regards,
                \n The Notification Team'''
                },
            
            {
                'template_code': 'password_reset',
                'subject': 'Password Reset Request',
                'body': '''Hi {{name}},
                \n You have requested to reset your password for your Distributed Notification System account. Click the link below to reset your password:
                \n{{reset_link}}
                \n This link will expire in 15 minutes for security reasons. If you didn't request this password reset, please ignore this email.
                \n\n Best regards,
                \nThe Notification Team'''
                },
            
            {
                'template_code': 'email_verification',
                'subject': 'Verify Your Email Address',
                'body': '''Hi {{name}},
                \n Please verify your email address to complete your account setup. Click the link below to verify your email:
                \n {{verification_link}}
                \n This verification link will expire in 24 hours. If you didn't create this account, please ignore this email.
                \n\n Best regards,
                \n The Notification Team'''
            }
        ]

        for template_data in templates:
            template, created = Template.objects.get_or_create(
                template_code=template_data['template_code'],
                language='en',
                defaults={
                    'subject': template_data['subject'],
                    'body': template_data['body'],
                    'version': 1,
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created template: {template.template_code}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Template already exists: {template.template_code}')
                )

        self.stdout.write(self.style.SUCCESS('Template loading completed!'))


