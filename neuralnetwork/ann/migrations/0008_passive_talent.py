from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ann', '0007_interview'),
    ]

    operations = [
        migrations.AddField(
            model_name='candidateprofile',
            name='open_to_work',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='TalentRecommendation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(
                    choices=[
                        ('pending',     'Pending'),
                        ('contacted',   'Contacted'),
                        ('shortlisted', 'Shortlisted'),
                        ('dismissed',   'Dismissed'),
                    ],
                    default='pending',
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('candidate', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='talent_recommendations',
                    to='ann.candidateprofile',
                )),
                ('job', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='talent_recommendations',
                    to='ann.job',
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='talentrecommendation',
            unique_together={('candidate', 'job')},
        ),
    ]
