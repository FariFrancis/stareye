from django.shortcuts import render

# Create your views here.
def chat_home(request):
    render(request, "chat/home.html")
def message(request):
    render(request, "chat/message.html")
    