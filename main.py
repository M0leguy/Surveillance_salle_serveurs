import network
import time
from machine import Pin, PWM, I2C
import dht
import ujson
from i2c_lcd import I2cLcd
import umail

# Configuration du Wi-Fi
ssid = 'Wokwi-GUEST'
password = ''

# Détails de l'email
sender_email = 'tizi.tztaz2@gmail.com'
sender_name = 'Salle des serveurs du SITE 1 '
sender_app_password = 'iikramctwewtidqf'
recipient_email = 'ziadessaidi.2727@gmail.com'
email_subject = '🚨 Alerte : Intrusion ou Condition Critique Détectée.'

# Seuils de température et d'humidité
TEMP_HIGH = 27 * 1.04
TEMP_LOW = 18 * 0.96
TEMP_CRIT = 60
HUMID_HIGH = 60 * 1.04
HUMID_LOW = 40 * 0.96
HUMID_CRIT = 70

# Configuration du mouvement (PIR)
pir_pin = Pin(23, Pin.IN)

# Configuration de l'I2C pour l'écran LCD1602 (ou un modèle 20x4)
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
lcd = I2cLcd(i2c, 0x27, 4, 20)

# Capteur de température et d'humidité
sensor = dht.DHT22(Pin(15))

# Initialisation du buzzer
buzzer_pin = Pin(4, Pin.OUT)
buzzer_pwm = PWM(buzzer_pin, freq=1000, duty=0)

# Variables pour suivre les alertes
email_sent = False
last_alert = None

# Connexion au Wi-Fi
def connect_wifi(ssid, password):
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    sta_if.connect(ssid, password)
    while not sta_if.isconnected():
        time.sleep(0.1)
    print("Connected to WiFi")

# Fonction pour émettre un son sur le buzzer
def tone(frequency, duration):
    buzzer_pwm.freq(frequency)
    buzzer_pwm.duty(512)
    time.sleep(duration)
    buzzer_pwm.duty(0)

# Fonction pour mettre à jour l'affichage LCD
def update_lcd(temp, humidity, intrusion=False):
    lcd.clear()
    lcd.putstr(f'Temp: {temp:.1f}C')
    lcd.move_to(0, 1)
    lcd.putstr(f'Humid: {humidity:.1f}%')
    lcd.move_to(0, 2)
    lcd.putstr("Intrusion!" if intrusion else "")

# Fonction pour envoyer un email d'alerte
def send_alert(temp, humidity, intrusion):
    global email_sent, last_alert
    current_alert = {
        "temp": temp,
        "humidity": humidity,
        "intrusion": intrusion
    }
    
    # Vérifie si l'alerte actuelle est différente de la dernière
    if last_alert != current_alert:
        smtp = umail.SMTP('smtp.gmail.com', 465, ssl=True)
        smtp.login(sender_email, sender_app_password)
        smtp.to(recipient_email)
        smtp.write("From:" + sender_name + "<" + sender_email + ">\n")
        smtp.write("Subject:" + email_subject + "\n")
        smtp.write(f"""Bonjour,

Une alerte a été déclenchée dans votre environnement surveillé :

- Température actuelle : {temp} °C
- Humidité actuelle : {humidity} %
- Intrusion détectée : {"Oui" if intrusion else "Non"}

Prenez des mesures immédiates pour contrôler la situation et vérifier l'état des capteurs.
""")
        smtp.send()
        smtp.quit()
        email_sent = True
        last_alert = current_alert  # Met à jour la dernière alerte
        print("Alerte envoyée par email.")

# Vérification de la température et de l'humidité
def check_conditions(temperature, humidity):
    critical = False
    if TEMP_LOW <= temperature < TEMP_HIGH:
        print("Température normale")
    elif TEMP_HIGH <= temperature < TEMP_CRIT:
        print("Attention! La salle est en surchauffe")
        tone(2000, 0.5)
        critical = True
    elif temperature <= TEMP_LOW:
        print("Attention! La salle est en refroidissement")
        tone(2000, 0.5)
        critical = True
    elif temperature >= TEMP_CRIT:
        print("Température critique!")
        tone(500, 1)
        critical = True

    if HUMID_LOW <= humidity < HUMID_HIGH:
        print("Humidité normale")
    elif HUMID_HIGH <= humidity < HUMID_CRIT:
        print("Attention! La salle est en humidification")
        tone(1000, 0.5)
        critical = True
    elif humidity <= HUMID_LOW:
        print("Attention! La salle manque d'humidité")
        tone(1000, 0.5)
        critical = True
    elif humidity >= HUMID_CRIT:
        print("Humidité critique!")
        tone(250, 1)
        critical = True

    return critical

# Fonction pour détecter une intrusion
def check_intrusion():
    if pir_pin.value() == 1:
        print("Intrusion détectée!")
        tone(3000, 0.5)
        return True
    return False

# Boucle principale
connect_wifi(ssid, password)
while True:
    sensor.measure()
    temperature = sensor.temperature()
    humidity = sensor.humidity()
    intrusion_detected = check_intrusion()

    # Vérification des conditions critiques et intrusion
    critical_condition = check_conditions(temperature, humidity)

    # Mise à jour du LCD
    update_lcd(temperature, humidity, intrusion_detected)

    # Envoi d'un email si condition critique ou intrusion détectée
    if critical_condition or intrusion_detected:
        send_alert(temperature, humidity, intrusion_detected)

    time.sleep(1)
