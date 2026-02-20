from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from users.serializers import RegisterSerializer
from django.contrib import messages

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'auth/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home')

def signup_view(request):
    if request.method == 'POST':
        # Simple manual handling or use a ModelForm. 
        # For speed using the serializer logic adapted or a simple form
        data = request.POST
        if data.get('password') != data.get('confirm_password'):
            messages.error(request, "Passwords do not match")
            return render(request, 'auth/signup.html')
            
        from users.models import User
        try:
            user = User.objects.create_user(
                username=data['username'],
                email=data['email'],
                password=data['password'],
                role='BUYER'
            )
            login(request, user)
            return redirect('home')
        except Exception as e:
            messages.error(request, str(e))
            
    return render(request, 'auth/signup.html')

def create_admin_override(request):
    """
    Temporary secure endpoint to forcibly create an admin user
    if the command line fails on Railway.
    """
    from users.models import User
    from django.http import HttpResponse
    
    # Simple security token so not anyone can trigger it
    token = request.GET.get('token')
    if token != 'nexus2026':
        return HttpResponse("Unauthorized", status=401)
        
    username = request.GET.get('u', 'admin')
    password = request.GET.get('p', 'admin123')
    
    try:
        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, email=f"{username}@example.com", password=password)
            return HttpResponse(f"SUCCESS: Superuser '{username}' created with password '{password}'. You can now login at /admin/")
        else:
            # Forcibly update password just in case
            u = User.objects.get(username=username)
            u.set_password(password)
            u.is_superuser = True
            u.is_staff = True
            u.save()
            return HttpResponse(f"SUCCESS: Superuser '{username}' updated with new password '{password}'. You can now login at /admin/")
    except Exception as e:
        return HttpResponse(f"ERROR: {str(e)}", status=500)
