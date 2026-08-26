from django.utils import timezone
import uuid
from django.db import models

#section table 
class Section(models.Model):
    name = models.CharField(max_length=100)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return self.name

#table mapped with section
class Table(models.Model):
    class Status(models.TextChoices):
        VACANT = "VACANT", "Vacant"
        OCCUPIED = "OCCUPIED", "Occupied"

    section = models.ForeignKey(
        Section,
        on_delete=models.PROTECT,
        related_name="tables",
    )
    name = models.CharField(max_length=100)
    display_order = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.VACANT,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["section", "display_order", "id"]

    def __str__(self):
        return self.name

#category for menu items (food or drink) table 
class Category(models.Model):
    class CategoryType(models.TextChoices):
        FOOD = "FOOD", "Food"
        DRINK = "DRINK", "Drink"

    name = models.CharField(max_length=100, unique=True)
    category_type = models.CharField(
        max_length=5,
        choices=CategoryType.choices,
    )
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return self.name

#menu items (food and drink) table mapped with category
class MenuItem(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="menu_items",
    )
    name = models.CharField(max_length=150)
    price = models.PositiveIntegerField()
    code = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.name

#round table mapped with table
class Round(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    table = models.ForeignKey(
        Table,
        on_delete=models.PROTECT,
        related_name="rounds",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"Round {self.id} - {self.table.name}"
#round items table mapped with round
class RoundItem(models.Model):
    round = models.ForeignKey(
        Round,
        on_delete=models.CASCADE,
        related_name="items",
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.PROTECT,
        related_name="round_items",
    )

    item_name = models.CharField(max_length=150)
    category_name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=5)

    unit_price = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField()
    line_total = models.PositiveIntegerField()

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.item_name} × {self.quantity}"

#bill table mapped with table
class Bill(models.Model):

    class Status(models.TextChoices):
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"

    bill_number = models.BigIntegerField(
        editable=False,
    )

    bill_date = models.DateField(
        default=timezone.localdate, 
        editable=False,
    )

    table = models.ForeignKey(
        Table,
        on_delete=models.PROTECT,
        related_name="bills",
    )

    subtotal = models.PositiveIntegerField()

    tax_enabled = models.BooleanField(
        default=False
    )

    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    tax_amount = models.PositiveIntegerField(
        default=0
    )

    total = models.PositiveIntegerField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PAID,
    )

    paid_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-bill_number"]

    def __str__(self):
        return f"Bill #{self.bill_number}" 
    

#bill items table mapped with bill
class BillItem(models.Model):
    bill = models.ForeignKey(
        Bill,
        on_delete=models.CASCADE,
        related_name="items",
    )

    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.PROTECT,
        related_name="bill_items",
    )

    item_name = models.CharField(max_length=150)
    category_name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=5)

    unit_price = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField()
    line_total = models.PositiveIntegerField()

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.item_name} × {self.quantity}"

#cancelled order table mapped with table
class CancelledOrder(models.Model):
    table = models.ForeignKey(
        Table,
        on_delete=models.PROTECT,
        related_name="cancelled_orders",
    )
    cancelled_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cancelled Order #{self.id}"

#cancelled items table mapped with cancelled order
class CancelledItem(models.Model):
    cancelled_order = models.ForeignKey(
        CancelledOrder,
        on_delete=models.CASCADE,
        related_name="items",
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.PROTECT,
        related_name="cancelled_items",
    )

    item_name = models.CharField(max_length=150)
    unit_price = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.item_name} × {self.quantity}"

#setting table
class Setting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.CharField(max_length=255)

    def __str__(self):
        return self.key