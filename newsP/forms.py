from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from .models import Post, Comment

class UpdateProfile(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']

class UpdatePasswords(PasswordChangeForm):
    pass

class savePost(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content', 'category', 'image']

class saveComment(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']