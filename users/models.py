from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

# Create your models here.
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, null=False, max_length=255)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    # Section access flags — staff users bypass these automatically
    access_products  = models.BooleanField(default=False, help_text="Can access Products section")
    access_quotes    = models.BooleanField(default=False, help_text="Can access Quotes section")
    access_scouting  = models.BooleanField(default=False, help_text="Can access Scouting section")
    access_shipments = models.BooleanField(default=False, help_text="Can view Shipments (no costs, no add/edit)")
    access_shipments_logistics = models.BooleanField(default=False, help_text="Logistics: can add/edit shipments and see unit costs")

    # Legacy fields (kept for compatibility during migration)
    role = models.CharField(
        max_length=20,
        choices=[('Admin', 'Admin'), ('Marketing', 'Marketing'), ('User', 'User')],
        default='User'
    )
    scouting_only = models.BooleanField(default=False, help_text="[Deprecated] Superseded by access_scouting")
    must_change_password = models.BooleanField(default=False, help_text="Force password change on next login")

    # User Manager
    objects = CustomUserManager()

    # Set email as the unique identifier
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email

    def get_short_name(self):
        return self.first_name or self.email

    def __str__(self):
        return self.email

    # Convenience properties — always True for staff
    @property
    def can_access_products(self):
        return self.is_staff or self.access_products

    @property
    def can_access_quotes(self):
        return self.is_staff or self.access_quotes

    @property
    def can_access_scouting(self):
        return self.is_staff or self.access_scouting

    @property
    def can_access_shipments(self):
        return self.is_staff or self.access_shipments or self.access_shipments_logistics

    @property
    def can_access_shipments_logistics(self):
        return self.is_staff or self.access_shipments_logistics