from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0003_merge_0002_cart_cartitem_0002_message'),
    ]

    operations = [
        # ── 1. Supprimer les tables Cart / CartItem ─────────────────────────
        migrations.DeleteModel(name='CartItem'),
        migrations.DeleteModel(name='Cart'),

        # ── 2. USER : rendre firstname/lastname NOT NULL ─────────────────────
        migrations.AlterField(
            model_name='user',
            name='firstname',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='user',
            name='lastname',
            field=models.CharField(max_length=100),
        ),

        # ── 3. CATEGORY : rendre name UNIQUE ────────────────────────────────
        migrations.AlterField(
            model_name='category',
            name='name',
            field=models.CharField(max_length=100, unique=True),
        ),

        # ── 4. PRODUCT : reconstruire les champs ─────────────────────────────
        # Renommer la PK (id → product_id)
        migrations.RenameField(
            model_name='product',
            old_name='id',
            new_name='product_id',
        ),
        # price : IntegerField → DecimalField(10,2)
        migrations.AlterField(
            model_name='product',
            name='price',
            field=models.DecimalField(max_digits=10, decimal_places=2),
        ),
        # is_customizable → customizable (BooleanField)
        migrations.RenameField(
            model_name='product',
            old_name='is_customizable',
            new_name='customizable',
        ),
        migrations.RunSQL(
            sql='ALTER TABLE product ALTER COLUMN "customizable" TYPE boolean USING ("customizable"::int::boolean);',
            reverse_sql='ALTER TABLE product ALTER COLUMN "customizable" TYPE smallint USING ("customizable"::int);',
        ),
        # customization_options → options
        migrations.RenameField(
            model_name='product',
            old_name='customization_options',
            new_name='options',
        ),
        # weight NOT NULL
        migrations.AlterField(
            model_name='product',
            name='weight',
            field=models.IntegerField(),
        ),
        # Supprimer l'ancienne FK category (remplacée par ManyToMany)
        migrations.RemoveField(
            model_name='product',
            name='category',
        ),

        # ── 5. PRODUCT_CATEGORY (table de liaison ManyToMany) ────────────────
        migrations.CreateModel(
            name='ProductCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='store.product',
                )),
                ('category', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='store.category',
                )),
            ],
            options={
                'db_table': 'product_category',
                'unique_together': {('product', 'category')},
            },
        ),
        migrations.AddField(
            model_name='product',
            name='categories',
            field=models.ManyToManyField(
                through='store.ProductCategory',
                to='store.category',
                related_name='products',
            ),
        ),

        # ── 6. ORDER : renommer les champs ───────────────────────────────────
        migrations.RenameField(
            model_name='order',
            old_name='carrier_name',
            new_name='carrier',
        ),
        migrations.AlterField(
            model_name='order',
            name='carrier',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.RenameField(
            model_name='order',
            old_name='carrier_price',
            new_name='carrier_cost',
        ),
        migrations.AlterField(
            model_name='order',
            name='carrier_cost',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.RenameField(
            model_name='order',
            old_name='delivery_address',
            new_name='address',
        ),
        migrations.RenameField(
            model_name='order',
            old_name='is_paid',
            new_name='paid',
        ),
        migrations.RunSQL(
            sql='ALTER TABLE orders ALTER COLUMN "paid" TYPE boolean USING ("paid"::int::boolean);',
            reverse_sql='ALTER TABLE orders ALTER COLUMN "paid" TYPE smallint USING ("paid"::int);',
        ),
        migrations.RenameField(
            model_name='order',
            old_name='stripe_session_id',
            new_name='stripe_id',
        ),
        migrations.RenameField(
            model_name='order',
            old_name='created_at',
            new_name='date',
        ),
        migrations.RenameField(
            model_name='order',
            old_name='shipping_label_url',
            new_name='label',
        ),
        migrations.AlterField(
            model_name='order',
            name='label',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AlterModelOptions(
            name='order',
            options={'ordering': ['-date']},
        ),
        migrations.AlterModelTable(
            name='order',
            table='order',
        ),

        # ── 7. ORDER_DETAILS : renommer les champs ───────────────────────────
        migrations.RenameField(
            model_name='orderdetails',
            old_name='detail_id',
            new_name='order_detail_id',
        ),
        migrations.RenameField(
            model_name='orderdetails',
            old_name='product_name',
            new_name='name',
        ),
        migrations.RenameField(
            model_name='orderdetails',
            old_name='product_price',
            new_name='price',
        ),
        migrations.AlterField(
            model_name='orderdetails',
            name='price',
            field=models.DecimalField(max_digits=10, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='orderdetails',
            name='total',
            field=models.DecimalField(max_digits=10, decimal_places=2),
        ),

        # ── 8. MESSAGE : renommer created_at → date + ajouter FK user ────────
        migrations.RenameField(
            model_name='message',
            old_name='created_at',
            new_name='date',
        ),
        migrations.AlterField(
            model_name='message',
            name='phone',
            field=models.CharField(
                max_length=15,
                validators=[django.core.validators.RegexValidator(
                    regex=r'^\+?[\d\s\-().]{7,20}$',
                    message='Numéro de téléphone invalide.'
                )],
            ),
        ),
        migrations.AlterField(
            model_name='message',
            name='email',
            field=models.EmailField(max_length=320, unique=True),
        ),
        migrations.AddField(
            model_name='message',
            name='user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='messages',
                to='store.user',
            ),
        ),
        migrations.AlterModelOptions(
            name='message',
            options={'ordering': ['-date']},
        ),

        # ── 9. USER : renommer la table ──────────────────────────────────────
        migrations.AlterModelTable(
            name='user',
            table='user',
        ),
    ]