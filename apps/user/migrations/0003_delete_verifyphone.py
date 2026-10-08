from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0002_alter_telegramuser_options'),
    ]

    operations = [
        migrations.DeleteModel(
            name='VerifyPhone',
        ),
    ]
