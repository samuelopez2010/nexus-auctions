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
