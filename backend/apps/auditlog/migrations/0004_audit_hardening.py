"""Phase 7 audit hardening: tamper-evident hash chain, richer fields,
append-only immutability, and a backfill that seals existing history into a
valid chain.
"""
import django.utils.timezone
from django.db import migrations, models

from apps.auditlog.hashing import GENESIS_HASH, compute_hash

_HASH_FIELDS = (
    "action", "actor_id", "hostel_id", "branch_id", "entity_type", "entity_id",
    "message", "reason", "meta", "changes", "ip_address", "user_agent",
    "request_id", "result", "status_code", "duration_ms", "created_at",
)

ACTION_CHOICES = [
    ('create', 'Create'), ('update', 'Update'), ('delete', 'Delete'),
    ('login', 'Login'), ('logout', 'Logout'), ('payment', 'Payment'),
    ('vacate', 'Vacate'), ('export', 'Export'), ('backup', 'Backup'),
    ('restore', 'Restore'), ('backup_failed', 'Backup failed'),
    ('snapshot', 'Snapshot created'), ('restore_started', 'Restore started'),
    ('restore_completed', 'Restore completed'), ('restore_failed', 'Restore failed'),
    ('retention', 'Retention deletion'), ('retention_failed', 'Retention deletion failed'),
    ('maintenance', 'Maintenance mode change'), ('access_denied', 'Access denied'),
    ('auth_failed', 'Authentication failed'), ('incident', 'Incident lifecycle'),
    ('announcement', 'System announcement'), ('feature_flag', 'Feature flag change'),
]


def backfill_chain(apps, schema_editor):
    """Assign sequence + hash chain to all pre-existing rows, then set the head."""
    AuditEvent = apps.get_model("auditlog", "AuditEvent")
    AuditChainState = apps.get_model("auditlog", "AuditChainState")

    prev_hash = GENESIS_HASH
    seq = 0
    for event in AuditEvent.objects.order_by("created_at", "id").iterator():
        seq += 1
        fields = {name: getattr(event, name) for name in _HASH_FIELDS}
        fields["sequence"] = seq
        content_hash = compute_hash(fields, prev_hash)
        AuditEvent.objects.filter(pk=event.pk).update(
            sequence=seq, prev_hash=prev_hash, content_hash=content_hash,
        )
        prev_hash = content_hash

    AuditChainState.objects.update_or_create(
        pk=1, defaults={"sequence": seq, "last_hash": prev_hash,
                        "checkpoint_sequence": 0, "checkpoint_hash": GENESIS_HASH},
    )


def noop_reverse(apps, schema_editor):
    apps.get_model("auditlog", "AuditChainState").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('auditlog', '0003_alter_auditevent_action'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditChainState',
            fields=[
                ('id', models.PositiveSmallIntegerField(default=1, primary_key=True, serialize=False)),
                ('sequence', models.BigIntegerField(default=0)),
                ('last_hash', models.CharField(default=GENESIS_HASH, max_length=64)),
                ('checkpoint_sequence', models.BigIntegerField(default=0)),
                ('checkpoint_hash', models.CharField(default=GENESIS_HASH, max_length=64)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'Audit chain state'},
        ),
        migrations.AddField(
            model_name='auditevent',
            name='sequence',
            field=models.BigIntegerField(blank=True, db_index=True, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='auditevent',
            name='prev_hash',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='auditevent',
            name='content_hash',
            field=models.CharField(blank=True, db_index=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='auditevent',
            name='reason',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='auditevent',
            name='changes',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='auditevent',
            name='request_id',
            field=models.CharField(blank=True, db_index=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='auditevent',
            name='result',
            field=models.CharField(
                choices=[('success', 'Success'), ('failure', 'Failure'), ('denied', 'Denied')],
                db_index=True, default='success', max_length=16),
        ),
        migrations.AddField(
            model_name='auditevent',
            name='status_code',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='auditevent',
            name='duration_ms',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='auditevent',
            name='created_at',
            field=models.DateTimeField(db_index=True, default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='auditevent',
            name='action',
            field=models.CharField(choices=ACTION_CHOICES, db_index=True, max_length=32),
        ),
        migrations.AddIndex(
            model_name='auditevent',
            index=models.Index(fields=['action', '-created_at'], name='auditlog_au_action_4b0516_idx'),
        ),
        migrations.AddIndex(
            model_name='auditevent',
            index=models.Index(fields=['entity_type', 'entity_id'], name='auditlog_au_entity__aa947c_idx'),
        ),
        migrations.RunPython(backfill_chain, noop_reverse),
    ]
