from django.db import models
from users.models import User

class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_date = models.DateTimeField(auto_now_add=True)
    transaction_type = models.CharField(max_length=50)  # e.g., 'subscription', 'tip', etc.

    def __str__(self):
        return f'Transaction of {self.amount} by {self.user.username}'
