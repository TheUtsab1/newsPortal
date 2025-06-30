from django.db import IntegrityError
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Post, Category, Comment
import json
from newsP import models, forms

def context_data():
    context = {
        'site_name': 'XBDC',
        'page': 'home',
        'page_title': 'XDBC',
        'categories': models.Category.objects.all(),  # Remove status filter for simplicity
    }
    return context

# Home page - show all posts to all users
def home(request):
    context = context_data()
    posts = models.Post.objects.all().order_by('-date_created')  # Show all posts
    context['page'] = 'home'
    context['page_title'] = 'Home'
    context['latest_top'] = posts[:2]
    context['latest_bottom'] = posts[2:12]
    print(posts)  # Debug print
    return render(request, 'home.html', context)

# Register a new user
def register_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        email = request.POST.get('email')

        if not username or not password or not confirm_password:
            messages.error(request, "All fields are required.")
        elif password != confirm_password:
            messages.error(request, "Passwords do not match.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Email is already in use.")
        else:
            user = User.objects.create_user(username=username, password=password, email=email)
            user.save()
            login(request, user)
            messages.success(request, "Registration successful! You are now logged in.")
            return redirect('home-page')

    return render(request, "register.html")

# Login - prevent admin login
def login_user(request):
    context = context_data()
    context['page'] = 'login'
    context['page_title'] = 'Login'
    resp = {"status": "failed", "msg": ""}
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active and not user.is_superuser:  # Prevent superuser login
                login(request, user)
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return HttpResponse(json.dumps({"status": "success"}), content_type="application/json")
                return redirect("home-page")
            elif user.is_superuser:
                resp["msg"] = "Admin accounts are not allowed to log in."
            else:
                resp["msg"] = "Your account is inactive. Please contact the administrator."
        else:
            resp["msg"] = "Incorrect username or password."
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return HttpResponse(json.dumps(resp), content_type="application/json")
        messages.error(request, resp["msg"])
    return render(request, "login.html", context)

# Logout
def logoutuser(request):
    logout(request)
    return redirect('/')

@login_required
def update_profile(request):
    context = context_data()
    context['page_title'] = 'Update Profile'
    user = User.objects.get(id=request.user.id)
    if not request.method == 'POST':
        form = forms.UpdateProfile(instance=user)
        context['form'] = form
    else:
        form = forms.UpdateProfile(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile has been updated")
            return redirect("profile-page")
        else:
            context['form'] = form
    return render(request, 'update_profile.html', context)

@login_required
def update_password(request):
    context = context_data()
    context['page_title'] = "Update Password"
    if request.method == 'POST':
        form = forms.UpdatePasswords(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your Account Password has been updated successfully")
            update_session_auth_hash(request, form.user)
            return redirect("profile-page")
        else:
            context['form'] = form
    else:
        form = forms.UpdatePasswords(user=request.user)
        context['form'] = form
    return render(request, 'update_password.html', context)

@login_required
def profile(request):
    context = context_data()
    context['page'] = 'profile'
    context['page_title'] = "Profile"
    return render(request, 'profile.html', context)

@login_required
def manage_post(request, pk=None):
    context = context_data()
    if pk is not None:
        context['page'] = 'edit_post'
        context['page_title'] = 'Edit Post'
        context['post'] = models.Post.objects.get(id=pk)
    else:
        context['page'] = 'new_post'
        context['page_title'] = 'New Post'
        context['post'] = {}
    return render(request, 'manage_post.html', context)

@login_required
def save_post(request):
    resp = {'status': 'failed', 'msg': '', 'id': None}
    if request.method == 'POST':
        try:
            if request.POST['id'] == '':
                form = forms.savePost(request.POST, request.FILES)
            else:
                post = models.Post.objects.get(id=request.POST['id'])
                form = forms.savePost(request.POST, request.FILES, instance=post)
    
            if form.is_valid():
                post_instance = form.save(commit=False)
                if request.POST['id'] == '':
                    post_instance.user = request.user
                post_instance.save()
                if request.POST['id'] == '':
                    postID = models.Post.objects.all().last().id
                else:
                    postID = request.POST['id']
                resp['id'] = postID
                resp['status'] = 'success'
                messages.success(request, "Post has been saved successfully.")
            else:
                for field in form:
                    for error in field.errors:
                        if resp['msg'] != '':
                            resp['msg'] += '<br />'
                        resp['msg'] += f"[{field.label}] {error}"
        except IntegrityError as e:
            resp['msg'] = f"Database error: {str(e)}"
        except models.Post.DoesNotExist:
            resp['msg'] = "Post not found."
    else:
        resp['msg'] = "Request has no data sent."
    return HttpResponse(json.dumps(resp), content_type="application/json")

# View a single post - accessible to all users
def view_post(request, pk=None):
    context = context_data()
    post = models.Post.objects.get(id=pk)
    context['page'] = 'post'
    context['page_title'] = post.title
    context['post'] = post
    context['latest'] = models.Post.objects.exclude(id=pk).order_by('-date_created').all()[:10]
    context['comments'] = models.Comment.objects.filter(post=post).all()
    context['actions'] = False
    if request.user.is_authenticated and (request.user.is_superuser or request.user.id == post.user.id):
        context['actions'] = True
    return render(request, 'single_post.html', context)

from django.http import JsonResponse  # Import JsonResponse for better response handling

@login_required
def save_comment(request):
    resp = {'status': 'failed', 'msg': '', 'id': None}
    if request.method == 'POST':
        if 'content' not in request.POST or not request.POST['content'].strip():
            resp['msg'] = 'Comment content is required.'
        else:
            try:
                post_id = request.POST.get('post_id')
                if not post_id:
                    resp['msg'] = 'Post ID is missing.'
                elif request.POST.get('id') == '':
                    form = forms.saveComment(request.POST)
                else:
                    comment = models.Comment.objects.get(id=request.POST['id'])
                    form = forms.saveComment(request.POST, instance=comment)

                if 'msg' not in resp and form.is_valid():
                    comment_instance = form.save(commit=False)
                    comment_instance.user = request.user
                    comment_instance.post = models.Post.objects.get(id=post_id)
                    comment_instance.save()
                    if request.POST.get('id') == '':
                        commentID = comment_instance.id
                    else:
                        commentID = request.POST['id']
                    resp['id'] = commentID
                    resp['status'] = 'success'
                    messages.success(request, "Comment has been saved successfully.")
                elif 'msg' not in resp:
                    for field in form:
                        for error in field.errors:
                            if resp['msg']:
                                resp['msg'] += '<br />'
                            resp['msg'] += f"[{field.label}] {error}"
            except models.Post.DoesNotExist:
                resp['msg'] = 'Post not found.'
            except Exception as e:
                resp['msg'] = f"An error occurred: {str(e)}"
                print(f"Error in save_comment: {str(e)}")  # Debug log
    else:
        resp['msg'] = "Invalid request method."
    return JsonResponse(resp)  # Use JsonResponse for consistent JSON output

@login_required
def list_posts(request):
    context = context_data()
    context['page'] = 'all_post'
    context['page_title'] = 'All Posts'
    if request.user.is_superuser:
        context['posts'] = models.Post.objects.all().order_by('-date_created')
    else:
        context['posts'] = models.Post.objects.all().order_by('-date_created')  # Show all posts to all users

    context['latest'] = models.Post.objects.all().order_by('-date_created')[:10]
    
    return render(request, 'posts.html', context)

# Category page - show all posts to all users
def category_posts(request, pk=None):
    context = context_data()
    if pk is None:
        messages.error(request, "File not Found")
        return redirect('home-page')
    try:
        category = models.Category.objects.get(id=pk)
    except:
        messages.error(request, "File not Found")
        return redirect('home-page')

    context['category'] = category
    context['page'] = 'category_post'
    context['page_title'] = f'{category.name} Posts'
    context['posts'] = models.Post.objects.filter(category=category).all()  # Show all posts
    context['latest'] = models.Post.objects.all().order_by('-date_created')[:10]
    
    return render(request, 'category.html', context)

@login_required
def delete_post(request, pk=None):
    resp = {'status': 'failed', 'msg': ''}
    if pk is None:
        resp['msg'] = 'Post ID is Invalid'
        return HttpResponse(json.dumps(resp), content_type="application/json")
    try:
        post = models.Post.objects.get(id=pk)
        post.delete()
        messages.success(request, "Post has been deleted successfully.")
        resp['status'] = 'success'
    except:
        resp['msg'] = 'Post ID is Invalid'
    
    return HttpResponse(json.dumps(resp), content_type="application/json")

@login_required
def delete_comment(request, pk=None):
    resp = {'status': 'failed', 'msg': ''}
    if pk is None:
        resp['msg'] = 'Comment ID is Invalid'
        return HttpResponse(json.dumps(resp), content_type="application/json")
    try:
        comment = models.Comment.objects.get(id=pk)
        comment.delete()
        messages.success(request, "Comment has been deleted successfully.")
        resp['status'] = 'success'
    except:
        resp['msg'] = 'Comment ID is Invalid'
    
    return HttpResponse(json.dumps(resp), content_type="application/json")