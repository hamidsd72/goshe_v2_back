from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsSuperUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)
# =============================================================
 
class IsSuperUserOrReadOnly(BasePermission):
    
    def has_permission(self, request, view):
        
        return bool(
            # access for any readonly
            request.method in SAFE_METHODS or
            # full access for superuser
            request.user and request.user.is_superuser
        )
# =============================================================

class IsSuperUserOrStaffReadOnly(BasePermission):
    
    def has_permission(self, request, view):
        # if request.method in SAFE_METHODS and request.user.is_authenticated and request.user.is_staff:
        #     return True
       
        return bool(
            # access for auther readonly
            request.method in SAFE_METHODS and request.user and request.user.is_staff
            or
            # full access for superuser
            request.user and request.user.is_superuser
        )
# =============================================================

class IsStaffOrReadOnly(BasePermission):

    def has_permission(self, request, view):
        return bool(
            request.method in SAFE_METHODS or
            request.user and
            request.user.is_staff
        )
# =============================================================

class IsAuthorOrReadOnly(BasePermission):
    
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
       
        return bool(
            # get access for superuser
            request.user.is_authenticated and request.user.is_superuser or
            # get access for auther of object
            obj.author == request.user
        )
# =============================================================

class IsIdOrReadOnly(BasePermission):
    
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
       
        return bool(
            # get access for superuser
            request.user.is_authenticated and request.user.is_superuser or
            # get access for auther of object
            obj.id == request.user.id
        )
# =============================================================

class IsUserIdOrReadOnly(BasePermission):
    
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
       
        return bool(
            # get access for superuser
            request.user.is_authenticated and request.user.is_superuser or
            # get access for auther of object
            obj.userId == request.user
        )
# =============================================================

class IsAuthorUserIdOrReadOnly(BasePermission):
    
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
       
        return bool(
            # get access for superuser
            request.user.is_authenticated and request.user.is_superuser or
            # get access for auther of object
            obj.AuthorUserId == request.user
        )
# =============================================================




