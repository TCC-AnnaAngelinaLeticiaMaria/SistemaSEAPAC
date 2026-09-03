from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("seapac", "0024_alter_project_status"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE seapac_evento
                ALTER COLUMN data TYPE smallint
                USING EXTRACT(YEAR FROM data)::smallint;

                ALTER TABLE seapac_family
                ALTER COLUMN data_inicio TYPE smallint
                USING EXTRACT(YEAR FROM data_inicio)::smallint;

                ALTER TABLE seapac_timelineevent
                ALTER COLUMN data TYPE smallint
                USING EXTRACT(YEAR FROM data)::smallint;
            """,
            reverse_sql="""
                ALTER TABLE seapac_evento
                ALTER COLUMN data TYPE date
                USING make_date(data, 1, 1);

                ALTER TABLE seapac_family
                ALTER COLUMN data_inicio TYPE date
                USING make_date(data_inicio, 1, 1);

                ALTER TABLE seapac_timelineevent
                ALTER COLUMN data TYPE date
                USING make_date(data, 1, 1);
            """,
        ),

        migrations.AlterField(
            model_name="evento",
            name="data",
            field=models.PositiveSmallIntegerField(),
        ),

        migrations.AlterField(
            model_name="family",
            name="data_inicio",
            field=models.PositiveSmallIntegerField(),
        ),

        migrations.AlterField(
            model_name="timelineevent",
            name="data",
            field=models.PositiveSmallIntegerField(),
        ),

        migrations.AlterField(
            model_name="timelineevent",
            name="secao",
            field=models.CharField(
                blank=True,
                choices=[
                    ("mundo-interno", "Interno"),
                    ("mundo-externo", "Externo"),
                ],
                max_length=100,
            ),
        ),
    ]