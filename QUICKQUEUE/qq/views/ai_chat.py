import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from qq.gemini_service import ask_gemini


@csrf_exempt
def ai_chat(request):
    if request.method != "POST":
        return JsonResponse(
            {"error": "Only POST requests are allowed."},
            status=405
        )

    try:
        data = json.loads(request.body)
        message = data.get("message", "").strip()

        if not message:
            return JsonResponse(
                {"error": "Message is required."},
                status=400
            )

        reply = ask_gemini(message)

        if reply is None:
            return JsonResponse(
                {"error": "AI service is currently unavailable."},
                status=503
            )

        return JsonResponse({
            "reply": reply
        })

    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON."},
            status=400
        )

    except Exception as e:
        print(f"AI Chat Error: {e}")

        return JsonResponse(
            {"error": "Something went wrong."},
            status=500
        )