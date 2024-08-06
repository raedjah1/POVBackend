from django.db import models
from users.models import Creator, User
from videos.models import Comment

class Transaction(models.Model):
    from_user = models.ForeignKey(User, related_name='transactions_made', on_delete=models.CASCADE, default=None)
    to_user = models.ForeignKey(User, related_name='transactions_received', on_delete=models.CASCADE, default=None)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_date = models.DateTimeField(auto_now_add=True)
    transaction_type = models.CharField(max_length=50, choices=(
        ('subscription', 'Subscription'),
        ('tip', 'Tip'),), default='subscription'
    )

    def __str__(self):
        return f"{self.from_user} -> {self.to_user}: {self.amount} ({self.transaction_type})"

    def __str__(self):
        return f'Transaction of {self.amount} by {self.user.username}'

class Tip(models.Model):
    amount = models.FloatField()
    message = models.TextField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tips_given')
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name='tips_received')
    comment = models.ForeignKey(Comment, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f'Tip of {self.amount} from {self.user.username} to {self.creator.username}'
