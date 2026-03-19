from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .services import responder

@csrf_exempt
def chat(request):
    data = json.loads(request.body)
    mensaje = data.get("mensaje")

    respuesta = responder(mensaje)

    return JsonResponse({"respuesta": respuesta})