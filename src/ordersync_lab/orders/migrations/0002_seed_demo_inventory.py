from django.db import migrations


DEMO_STOCK = {
    "MUG-BLUE": 25,
    "NOTEBOOK-A5": 50,
    "TOTE-BLACK": 10,
}


def seed_demo_inventory(apps, schema_editor):  # noqa: ARG001
    warehouse_stock = apps.get_model("orders", "WarehouseStock")
    for sku, quantity in DEMO_STOCK.items():
        warehouse_stock.objects.get_or_create(
            sku=sku,
            defaults={"available_quantity": quantity},
        )


def remove_demo_inventory(apps, schema_editor):  # noqa: ARG001
    warehouse_stock = apps.get_model("orders", "WarehouseStock")
    warehouse_stock.objects.filter(sku__in=DEMO_STOCK).delete()


class Migration(migrations.Migration):
    dependencies = [("orders", "0001_initial")]

    operations = [migrations.RunPython(seed_demo_inventory, remove_demo_inventory)]
