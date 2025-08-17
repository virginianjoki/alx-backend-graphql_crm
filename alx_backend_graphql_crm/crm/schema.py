import re
import graphene
from decimal import Decimal, InvalidOperation
from graphene_django import DjangoObjectType
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from graphene_django.filter import DjangoFilterConnectionField
from .filters import CustomerFilter, ProductFilter, OrderFilter
from .models import Customer, Product, Order

# === TYPES ===


class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = ("id", "name", "email", "phone")


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = ("id", "name", "price", "stock")


class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = ("id", "customer", "products", "total_amount", "order_date")

    # Example: format the date for clarity
    order_date = graphene.String()

    def resolve_order_date(self, info):
        return self.order_date.strftime("%Y-%m-%d %H:%M:%S")


# === INPUTS ===
class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String()


# === MUTATIONS ===
class CreateCustomer(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        email = graphene.String(required=True)
        phone = graphene.String()

    customer = graphene.Field(CustomerType)
    message = graphene.String()

    def mutate(self, info, name, email, phone=None):
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            raise Exception("Invalid email format")

        if Customer.objects.filter(email=email).exists():
            raise Exception("Email already exists")

        customer = Customer(name=name, email=email, phone=phone)
        customer.full_clean()
        customer.save()
        return CreateCustomer(customer=customer, message="Customer created successfully!")


class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        customers = graphene.List(CustomerInput)

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    def mutate(self, info, customers):
        created = []
        errors = []

        for data in customers:
            try:
                if Customer.objects.filter(email=data.email).exists():
                    errors.append(f"Duplicate email: {data.email}")
                    continue

                customer = Customer(
                    name=data.name, email=data.email, phone=data.phone
                )
                customer.full_clean()
                customer.save()
                created.append(customer)
            except ValidationError as e:
                errors.append(str(e))

        return BulkCreateCustomers(customers=created, errors=errors)


class CreateProduct(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        # use string to safely handle Decimal
        price = graphene.String(required=True)
        stock = graphene.Int(required=False, default_value=0)

    product = graphene.Field(ProductType)
    message = graphene.String()

    def mutate(self, info, name, price, stock=0):
        try:
            price_decimal = Decimal(price)
        except InvalidOperation:
            raise Exception("Invalid price format")

        if price_decimal <= 0:
            raise Exception("Price must be positive")
        if stock < 0:
            raise Exception("Stock cannot be negative")

        product = Product(name=name, price=price_decimal, stock=stock)
        product.save()
        return CreateProduct(product=product, message="Product created successfully!")


class CreateOrder(graphene.Mutation):
    class Arguments:
        customer_id = graphene.ID(required=True)
        product_ids = graphene.List(graphene.ID, required=True)

    order = graphene.Field(OrderType)
    message = graphene.String()

    @transaction.atomic
    def mutate(self, info, customer_id, product_ids):
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            raise Exception("Invalid customer ID")

        if not product_ids:
            raise Exception("At least one product is required")

        products = Product.objects.select_for_update().filter(id__in=product_ids)
        if products.count() != len(product_ids):
            raise Exception("Some product IDs are invalid")

        # Ensure stock availability
        for product in products:
            if product.stock <= 0:
                raise Exception(f"Product '{product.name}' is out of stock")

        # Deduct stock and create order
        order = Order(customer=customer, order_date=timezone.now())
        order.save()
        order.products.set(products)

        for product in products:
            product.stock -= 1
            product.save()

        order.save()  # triggers total calculation
        return CreateOrder(order=order, message="Order created successfully!")


# === ROOT MUTATION CLASS ===
class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()


# === QUERY CLASS ===
class Query(graphene.ObjectType):
    customers = graphene.List(CustomerType, search=graphene.String())
    products = graphene.List(ProductType, in_stock=graphene.Boolean())
    orders = graphene.List(OrderType, customer_id=graphene.ID())

    def resolve_customers(self, info, search=None):
        qs = Customer.objects.all()
        if search:
            qs = qs.filter(name__icontains=search) | qs.filter(
                email__icontains=search)
        return qs

    def resolve_products(self, info, in_stock=None):
        qs = Product.objects.all()
        if in_stock is not None:
            qs = qs.filter(stock__gt=0) if in_stock else qs.filter(stock=0)
        return qs

    def resolve_orders(self, info, customer_id=None):
        qs = Order.objects.all()
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        return qs


# === ROOT SCHEMA ===
schema = graphene.Schema(query=Query, mutation=Mutation)
