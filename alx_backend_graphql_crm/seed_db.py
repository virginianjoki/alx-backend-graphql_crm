from crm.models import Customer, Product
import os
import django

# 🔹 IMPORTANT: Use your project name here (same one as settings.py folder)
os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                      "alx_backend_graphql_crm.settings")

# 🔹 Setup Django BEFORE importing models
django.setup()


def run():
    Customer.objects.create(name="Alice", email="alice@example.com")
    Customer.objects.create(name="Bob", email="bob@example.com")

    Product.objects.create(name="Laptop", price=1000)
    Product.objects.create(name="Phone", price=500)

    print("✅ Database seeded successfully!")


if __name__ == "__main__":
    run()
