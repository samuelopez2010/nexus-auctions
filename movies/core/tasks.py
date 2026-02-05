from celery import shared_task
from .recommender import RecommenderSystem
from .models import UserRecommendation, CustomUser

@shared_task
def calculate_recommendations(user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
        recommender = RecommenderSystem()
        
        # In a real production system, training would be a separate, scheduled task
        # that serializes the model to a file/cache.
        # For this demo, we train on the fly.
        recommender.train() 
        
        reps = recommender.get_recommendations(user_id)
        
        UserRecommendation.objects.update_or_create(
            user=user,
            defaults={'recommendations': reps}
        )
        return f"Updated recommendations for {user.username}"
    except CustomUser.DoesNotExist:
        return f"User {user_id} not found"
