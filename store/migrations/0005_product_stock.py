from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0004_schema_update'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='stock',
            field=models.IntegerField(default=0),
        ),
    ]