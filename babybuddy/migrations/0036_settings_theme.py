from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("babybuddy", "0035_alter_settings_language"),
    ]

    operations = [
        migrations.AddField(
            model_name="settings",
            name="theme",
            field=models.CharField(
                choices=[
                    ("auto", "Match system"),
                    ("light", "Light"),
                    ("dark", "Dark"),
                ],
                default="auto",
                help_text='"Match system" follows the light or dark setting of your device.',
                max_length=5,
                verbose_name="Appearance",
            ),
        ),
    ]
