from django.core.management.base import BaseCommand
from market.models import Product, Category
from users.models import User
from decimal import Decimal

class Command(BaseCommand):
    help = 'Popula la base de datos con tarjetas de regalo virtuales para que la tienda no se vea vacía.'

    def handle(self, *args, **kwargs):
        # 1. Obtener o crear Categoría de Tarjetas de Regalo
        category, created = Category.objects.get_or_create(
            name='Gift Cards', 
            defaults={'slug': 'gift-cards'}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Categoría 'Gift Cards' creada."))

        # 2. Conseguir un usuario administrador para asignarle los productos
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            # Si no hay superuser, crear uno rápido
            admin_user, _ = User.objects.get_or_create(
                username='nexus_admin',
                defaults={'is_superuser': True, 'is_staff': True}
            )
            self.stdout.write("Usuario admin por defecto para ventas creado/obtenido.")

        # 3. Lista de tarjetas de regalo a crear
        gift_cards_data = [
            {
                'title': 'Nexus $10 Gift Card',
                'description': 'A $10 virtual gift card to spend across the Nexus Marketplace on any digital or physical items.',
                'initial_price': Decimal('10.00'),
                'is_variable_price': False,
            },
            {
                'title': 'Nexus $50 Premium Card',
                'description': 'A $50 premium gift card. Perfect for frequent shoppers in our marketplace.',
                'initial_price': Decimal('50.00'),
                'is_variable_price': False,
            },
            {
                'title': 'Nexus Custom Amount Card',
                'description': 'Choose your own amount to gift to your friends or family. Funds will be deposited in their wallet.',
                'initial_price': Decimal('0.00'),
                'is_variable_price': True, # Esto activa la caja de ingresar monto personalizado
            },
            {
                'title': 'Amazon $25 Gift Card (Digital)',
                'description': 'Official Amazon $25 Gift Card code, delivered instantly to your inbox upon settlement.',
                'initial_price': Decimal('25.00'),
                'is_variable_price': False,
            },
            {
                'title': 'Steam $50 Wallet Code',
                'description': 'Add $50 to your Steam Wallet to buy the latest games. Instant delivery.',
                'initial_price': Decimal('50.00'),
                'is_variable_price': False,
            }
        ]

        count = 0
        for data in gift_cards_data:
            # Evita duplicados por título
            prod, prod_created = Product.objects.get_or_create(
                title=data['title'],
                defaults={
                    'seller': admin_user,
                    'category': category,
                    'description': data['description'],
                    'condition': 'NEW',
                    'location': 'Virtual Delivery',
                    'sales_type': 'DIRECT',
                    'initial_price': data['initial_price'],
                    'buy_now_price': data['initial_price'] if not data['is_variable_price'] else None,
                    'is_variable_price': data['is_variable_price'],
                    'status': 'ACTIVE',
                    'is_active': True
                }
            )
            if prod_created:
                count += 1

        if count > 0:
            self.stdout.write(self.style.SUCCESS(f"¡Exito! {count} tarjetas de regalo creadas en la base de datos."))
        else:
            self.stdout.write("Las tarjetas de regalo ya existían en la base de datos (0 creadas).")
