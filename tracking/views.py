# views.py
import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import VehicleData, UserZone, Alert, History,SMSPosition
from .forms import ContactForm
import math
from shapely.geometry import shape, Point
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View

# --- 1. Carte principale ---
@login_required
def vehicle_map(request):
    last_position = VehicleData.objects.last()
    user_zone = UserZone.objects.filter(user=request.user).first()
    user_zone_geojson = None
    if user_zone:
        user_zone_geojson = json.dumps(user_zone.geojson)
    context = {
        'last_position': last_position,
        'user_zone_geojson': user_zone_geojson,
    }
    return render(request, 'tracking/map.html', context)


# --- 2. Liste des alertes ---
@login_required
def alert_list(request):
    alerts = Alert.objects.all().order_by('-timestamp')
    return render(request, 'tracking/alerts.html', {'alerts': alerts})


# --- 3. Sauvegarder une zone (polygone GeoJSON) ---
@csrf_exempt
@login_required
def save_zone(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Supprimer l'ancienne zone
            UserZone.objects.filter(user=request.user).delete()
            # Créer la nouvelle zone
            UserZone.objects.create(
                user=request.user,
                geojson=data,
                name="Zone de surveillance"
            )
            return JsonResponse({'message': 'Zone sauvegardée avec succès'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)


# --- 4. Vérifier la sortie de zone et créer une alerte (une seule fois) ---
def check_geofence_alert(vehicle_id, lat, lng, user):
    try:
        user_zone = UserZone.objects.get(user=user)
        zone_shape = shape(user_zone.geojson)
        point = Point(lng, lat)  # (longitude, latitude)

        if not zone_shape.contains(point):
            recent_alert = Alert.objects.filter(
                vehicle=vehicle_id,
                alert_type="Sortie de zone",
                timestamp__gte=timezone.now() - timezone.timedelta(minutes=5)
            ).exists()

            if not recent_alert:
                Alert.objects.create(
                    user=user,
                    vehicle=vehicle_id,
                    alert_type="Sortie de zone",
                    description=f"Le véhicule {vehicle_id} a quitté la zone de surveillance.",
                    timestamp=timezone.now()
                )
    except UserZone.DoesNotExist:
        pass  # Aucune zone définie


# --- 5. Mettre à jour la position ---
@csrf_exempt
def update_position(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            vehicle_id = data.get('imei') or data.get('vehicle_id') or "inconnu"
            lat = data.get('latitude')
            lon = data.get('longitude')
            speed = data.get('speed', None)

            if lat is None or lon is None:
                return JsonResponse({'status': 'error', 'message': 'Latitude ou longitude manquante'}, status=400)

            # Sauvegarder la position
            position = VehicleData.objects.create(
                vehicle_id=vehicle_id,
                latitude=lat,
                longitude=lon,
                speed=speed,
                timestamp=timezone.now()
            )

            # Mettre à jour l'historique
            history, created = History.objects.get_or_create(
                vehicle=vehicle_id,
                defaults={'path': []}
            )
            path = history.path
            point = {
                "lat": lat,
                "lng": lon,
                "timestamp": timezone.now().isoformat(),
                "speed": speed
            }
            path.append(point)
            history.path = path

            # Calculer la distance si possible
            if len(path) >= 2:
                last = path[-2]
                d = haversine(last['lat'], last['lng'], lat, lon)
                history.distance_km += d
            history.save()

            # Vérifier la sortie de zone (si l'utilisateur est authentifié)
            if request.user.is_authenticated:
                check_geofence_alert(vehicle_id, lat, lon, request.user)

            return JsonResponse({'status': 'ok'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'}, status=405)


# --- 6. Historique des positions ---
@login_required
def history_list(request):
    histories = History.objects.all().order_by('-date')
    return render(request, 'tracking/history.html', {'histories': histories})


# --- 7. Page d'accueil ---
def home(request):
    return render(request, 'tracking/home.html')


# --- 8. Gestion des utilisateurs ---
def user_list(request):
    if request.user.is_authenticated:
        return redirect('profile')

    if request.method == 'POST':
        if 'full_name' in request.POST:
            # Inscription
            full_name = request.POST.get('full_name')
            email = request.POST.get('email')
            password = request.POST.get('password')
            if User.objects.filter(username=email).exists():
                messages.error(request, "Un compte avec cet email existe déjà.")
            else:
                user = User.objects.create_user(username=email, email=email, password=password)
                user.first_name = full_name
                user.save()
                messages.success(request, "Inscription réussie. Vous pouvez vous connecter.")
                return redirect('user_list')
        else:
            # Connexion
            email = request.POST.get('email')
            password = request.POST.get('password')
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                return redirect('profile')
            else:
                messages.error(request, "Email ou mot de passe incorrect.")
    return render(request, 'tracking/users.html')


# --- 9. Contact ---
def help_contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact = form.save()
            send_mail(
                subject=f"Nouveau message de contact : {contact.subject}",
                message=f"De : {contact.full_name} <{contact.email}>\n\n{contact.message}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.CONTACT_RECEIVER_EMAIL],
                fail_silently=False,
            )
            messages.success(request, "Votre message a été envoyé avec succès.")
            return redirect('help_contact')
    else:
        form = ContactForm()
    return render(request, 'tracking/help_contact.html', {'form': form})


# --- 10. Profil ---
@login_required
def profile_view(request):
    return render(request, 'tracking/profile.html', {'user': request.user})

@login_required
def edit_email(request):
    if request.method == 'POST':
        new_email = request.POST.get('new_email')
        if new_email:
            request.user.email = new_email
            request.user.save()
            messages.success(request, "Votre email a été mis à jour.")
    return redirect('profile')

@login_required
def edit_password(request):
    if request.method == 'POST':
        new_pass1 = request.POST.get('new_password1')
        new_pass2 = request.POST.get('new_password2')
        if new_pass1 and new_pass1 == new_pass2:
            request.user.set_password(new_pass1)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, "Mot de passe changé avec succès.")
        else:
            messages.error(request, "Les mots de passe ne correspondent pas.")
    return redirect('profile')


# --- 11. Calcul de distance ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Rayon de la Terre en km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@login_required
def delete_zone(request):
    if request.method == 'POST':
        try:
            # Supprime uniquement la zone de l'utilisateur connecté
            user_zone = get_object_or_404(UserZone, user=request.user)
            user_zone.delete()
            return JsonResponse({'message': 'Zone supprimée avec succès'})
        except UserZone.DoesNotExist:
            return JsonResponse({'error': 'Aucune zone trouvée pour cet utilisateur'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)



# views.py
@csrf_exempt
def receive_sms_position(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            lat = data.get('latitude')
            lng = data.get('longitude')
            vehicle_id = data.get('vehicle_id', 'LILYGO-GPS-001')

            if lat and lng:
                SMSPosition.objects.create(
                    vehicle_id=vehicle_id,
                    latitude=lat,
                    longitude=lng
                )
                return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)


@login_required
def sms_positions(request):
    positions = SMSPosition.objects.all().order_by('-timestamp')
    data = [
        {
            'latitude': p.latitude,
            'longitude': p.longitude,
            'timestamp': p.timestamp.isoformat()
        }
        for p in positions
    ]
    return JsonResponse(data, safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class MarkAlertRead(View):
    def post(self, request, alert_id):
        alert = get_object_or_404(Alert, id=alert_id)
        alert.is_read = True
        alert.save()
        return JsonResponse({'status': 'success'})

@method_decorator(csrf_exempt, name='dispatch')
class DeleteAlert(View):
    def post(self, request, alert_id):
        alert = get_object_or_404(Alert, id=alert_id)
        alert.delete()
        return JsonResponse({'status': 'success'})