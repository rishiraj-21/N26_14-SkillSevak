from django.db import migrations, models


def remap_old_statuses(apps, schema_editor):
    Application = apps.get_model('ann', 'Application')
    Application.objects.filter(status='reviewed').update(status='screening')
    Application.objects.filter(status='interview').update(status='phone_interview')


class Migration(migrations.Migration):
    dependencies = [('ann', '0005_phase4_model_updates')]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='status',
            field=models.CharField(
                max_length=50,
                choices=[
                    ('applied',         'Applied'),
                    ('screening',       'Screening'),
                    ('phone_interview', 'Phone Interview'),
                    ('technical',       'Technical Assessment'),
                    ('final_interview', 'Final Round'),
                    ('offer',           'Offer Extended'),
                    ('hired',           'Hired'),
                    ('rejected',        'Rejected'),
                ],
                default='applied',
            ),
        ),
        migrations.RunPython(remap_old_statuses, migrations.RunPython.noop),
    ]
