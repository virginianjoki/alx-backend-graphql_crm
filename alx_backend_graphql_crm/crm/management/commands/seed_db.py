from django.core.management.base import BaseCommand
from crm.models import Customer, Product


class Command(BaseCommand):
    help = "Seed the database with sample data"

    def handle(self, *args, **kwargs):
        # Example seed data
        customers = [
            {"name": "Alice", "email": "alice@example.com"},
            {"name": "Bob", "email": "bob@example.com"},
        ]

        products = [
            {"name": "Laptop", "price": 1200},
            {"name": "Phone", "price": 800},
        ]

        for c in customers:
            Customer.objects.get_or_create(**c)

        for p in products:
            Product.objects.get_or_create(**p)

        self.stdout.write(self.style.SUCCESS("Database seeded successfully!"))
