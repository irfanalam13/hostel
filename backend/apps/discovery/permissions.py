from rest_framework.permissions import BasePermission


class IsReviewAuthor(BasePermission):
    message = "You can only modify your own review."

    def has_object_permission(self, request, view, obj):
        return obj.author_id == request.user.id
