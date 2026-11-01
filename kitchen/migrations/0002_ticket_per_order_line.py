import uuid

from django.db import migrations, models


def split_tickets_per_line(apps, schema_editor):
    """注文 1 件 = チケット 1 枚(明細は items に JSON で入っていた)を、明細 1 行 = 1 枚に分ける。
    分けたチケットは元のチケットのステータス・作成時刻を引き継ぐ。
    """
    TicketModel = apps.get_model("kitchen", "TicketModel")
    for ticket in TicketModel.objects.all():
        items = ticket.items or []
        if not items:
            continue
        first, *rest = items
        ticket.line_no, ticket.name, ticket.quantity = 1, first["name"], first["quantity"]
        ticket.save(update_fields=["line_no", "name", "quantity"])
        for line_no, item in enumerate(rest, start=2):
            new = TicketModel.objects.create(
                id=uuid.uuid4(),
                order_id=ticket.order_id,
                line_no=line_no,
                name=item["name"],
                quantity=item["quantity"],
                status=ticket.status,
                items=[],
            )
            # auto_now_add は create 時に今の時刻を入れるので、元の時刻に戻す
            TicketModel.objects.filter(id=new.id).update(created_at=ticket.created_at)


class Migration(migrations.Migration):

    dependencies = [
        ('kitchen', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ticketmodel',
            name='order_id',
            field=models.UUIDField(db_index=True),
        ),
        migrations.AddField(
            model_name='ticketmodel',
            name='line_no',
            field=models.PositiveSmallIntegerField(default=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='ticketmodel',
            name='name',
            field=models.CharField(default='', max_length=128),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='ticketmodel',
            name='quantity',
            field=models.PositiveSmallIntegerField(default=1),
            preserve_default=False,
        ),
        migrations.RunPython(split_tickets_per_line, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='ticketmodel',
            name='items',
        ),
        migrations.AddConstraint(
            model_name='ticketmodel',
            constraint=models.UniqueConstraint(fields=('order_id', 'line_no'), name='kitchen_ticket_one_per_line'),
        ),
    ]
