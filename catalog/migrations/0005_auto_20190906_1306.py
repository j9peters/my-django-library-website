# Generated by Django 2.2.2 on 2019-09-06 20:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0004_auto_20190903_1429'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='bookinstance',
            options={'ordering': ['due_back'], 'permissions': (('can_mark_returned', 'Set book as returned'), ('can_view_all_borrowed_books', 'View all borrowed books'))},
        ),
    ]
