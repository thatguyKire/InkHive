from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from modules.authentication.models import CustomUser

class CustomSignupForm(UserCreationForm):
    # Make email explicit and autofill-friendly
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            "autocomplete": "email",
            "inputmode": "email",
        })
    )
    student_id = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={
            "placeholder": "Student ID (if Student)",
            "autocomplete": "off",
            "inputmode": "text",
        })
    )
    role = forms.ChoiceField(
        choices=[("student", "Student"), ("teacher", "Teacher")],
        widget=forms.Select(attrs={"autocomplete": "off"})
    )
    # Clickwrap agreement to the Terms of Service and Privacy Policy (modules/legal)
    accept_terms = forms.BooleanField(
        required=True,
        error_messages={"required": "Please agree to the Terms of Service and Privacy Policy to create an account."},
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ["username", "email", "student_id", "role", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Accessible/autofill-friendly attributes
        self.fields["username"].widget.attrs.update({
            "autocomplete": "username",
            "autocapitalize": "none",
            "spellcheck": "false",
        })
        self.fields["password1"].widget.attrs.update({
            "autocomplete": "new-password",
        })
        self.fields["password2"].widget.attrs.update({
            "autocomplete": "new-password",
        })
        # Friendlier labels (avoid showing 'password1' / 'password2')
        self.fields["password1"].label = "Password"
        self.fields["password2"].label = "Confirm password"

    def clean(self):
        cleaned = super().clean()
        role = (cleaned.get("role") or "").lower()
        sid = (cleaned.get("student_id") or "").strip()

        if role == "student":
            if not sid:
                self.add_error("student_id", "Student ID is required for students.")
            # ensure model-level unique validation uses the normalized value
            cleaned["student_id"] = sid or None
            self.instance.student_id = sid or None
        else:
            # critical: avoid unique '' collisions for teachers/admins
            cleaned["student_id"] = None
            self.instance.student_id = None

        return cleaned

    def clean_email(self):
        """Ensure email is unique (case-insensitive) at signup.

        The model doesn't currently enforce email uniqueness at the database
        level, so we validate here and raise a friendly form error.
        """
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise forms.ValidationError("Enter a valid email address.")
        if CustomSignupForm.Meta.model.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with that email address already exists.")
        return email

    def clean_password2(self):
        """Show the mismatch and password-validator messages as form-level errors.

        Django attaches them to ``password2``, which the template would label
        "Password2"; full_clean() then drops that field's copies.
        """
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error(None, "The two password fields didn't match.")
            return password2

        if password1:
            try:
                validate_password(password1, self.instance)
            except DjangoValidationError as e:
                for msg in e.messages:
                    self.add_error(None, msg)
        return password2

    def full_clean(self):
        # Runs after every field/form validator, so this catches all copies.
        super().full_clean()
        self._errors.pop("password2", None)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = (self.cleaned_data.get("email") or "").strip().lower()
        user.role = (self.cleaned_data.get("role") or "").lower()
        # already normalized by clean()
        user.student_id = self.cleaned_data.get("student_id")
        user.accept_terms()
        if commit:
            user.save()
        return user
