from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('ann', '0006_application_pipeline_stages')]

    operations = [
        migrations.CreateModel(
            name='Interview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scheduled_date', models.DateTimeField()),
                ('duration_minutes', models.IntegerField(default=60)),
                ('interview_type', models.CharField(
                    max_length=50,
                    choices=[
                        ('phone_screen', 'Phone Screen'),
                        ('technical', 'Technical'),
                        ('behavioral', 'Behavioral'),
                        ('culture_fit', 'Culture Fit'),
                        ('final_round', 'Final Round'),
                    ],
                    default='technical',
                )),
                ('status', models.CharField(
                    max_length=20,
                    choices=[
                        ('scheduled', 'Scheduled'),
                        ('completed', 'Completed'),
                        ('cancelled', 'Cancelled'),
                        ('rescheduled', 'Rescheduled'),
                    ],
                    default='scheduled',
                )),
                ('meeting_link', models.URLField(blank=True)),
                ('location', models.CharField(max_length=200, blank=True)),
                ('interviewer', models.CharField(max_length=200, blank=True)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('application', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='interviews',
                    to='ann.application',
                )),
            ],
            options={'ordering': ['scheduled_date']},
        ),
    ]
