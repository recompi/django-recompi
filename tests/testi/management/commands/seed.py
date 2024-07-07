from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed the database with initial data"

    def handle(self, *args, **kwargs):
        from testi.models import Product, Review, ReviewCounter, RatingChoices

        self.stdout.write("Seeding the database...")

        # Create some products
        products = [
            Product(name="Laptop", description="High performance laptop"),
            Product(name="Smartphone", description="Latest model smartphone"),
            Product(name="Headphones", description="Noise-cancelling headphones"),
        ]
        Product.objects.bulk_create(products)

        # Create review counters
        counters = [ReviewCounter(count=0) for _ in range(3)]
        ReviewCounter.objects.bulk_create(counters)

        # Create some reviews
        reviews = [
            Review(
                product=products[0],
                comment="Great laptop, very fast!",
                rating=RatingChoices.FIVE,
                counter=counters[0],
            ),
            Review(
                product=products[1],
                comment="The battery life could be better.",
                rating=RatingChoices.THREE,
                counter=counters[1],
            ),
            Review(
                product=products[2],
                comment="Excellent sound quality.",
                rating=RatingChoices.FOUR,
                counter=counters[2],
            ),
        ]
        Review.objects.bulk_create(reviews)

        self.stdout.write(self.style.SUCCESS("Database seeded successfully!"))
