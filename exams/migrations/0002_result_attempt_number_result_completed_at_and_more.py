# Generated by Django 4.2.18 on 2025-01-29 21:52

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('exams', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='result',
            name='attempt_number',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='result',
            name='completed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='result',
            name='is_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='result',
            name='time_taken',
            field=models.DurationField(blank=True, null=True),
        ),
        migrations.AlterUniqueTogether(
            name='result',
            unique_together={('user', 'exam', 'attempt_number')},
        ),
        migrations.CreateModel(
            name='StudentProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_blocked', models.BooleanField(default=False)),
                ('blocked_at', models.DateTimeField(blank=True, null=True)),
                ('block_reason', models.TextField(blank=True)),
                ('blocked_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='blocked_students', to=settings.AUTH_USER_MODEL)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='student_profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='StudentActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activity_type', models.CharField(choices=[('block', 'Blocked'), ('unblock', 'Unblocked'), ('exam_block', 'Exam Access Blocked'), ('exam_unblock', 'Exam Access Unblocked'), ('exam_attempt', 'Exam Attempted'), ('exam_complete', 'Exam Completed')], max_length=20)),
                ('description', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('exam', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='exams.exams')),
                ('performed_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='performed_activities', to=settings.AUTH_USER_MODEL)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activities', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Student Activities',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='StudentExamAccess',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_blocked', models.BooleanField(default=False)),
                ('blocked_at', models.DateTimeField(blank=True, null=True)),
                ('block_reason', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('blocked_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='blocked_exam_access', to=settings.AUTH_USER_MODEL)),
                ('exam', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='exams.exams')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exam_access', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Student Exam Access',
                'unique_together': {('student', 'exam')},
            },
        ),
    ]
