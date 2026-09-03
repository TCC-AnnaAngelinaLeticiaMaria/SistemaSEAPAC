from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("seapac", "0026_municipality_comunidade_alter_family_data_inicio_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE seapac_family
                ALTER COLUMN data_inicio DROP NOT NULL;
            """,
            reverse_sql="""
                ALTER TABLE seapac_family
                ALTER COLUMN data_inicio SET NOT NULL;
            """,
        ),
    ]