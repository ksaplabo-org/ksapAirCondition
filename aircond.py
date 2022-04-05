import RPi.GPIO as GPIO
import dht11
import time
import datetime
import paho.mqtt.client
import json
import asyncio
import ssl
import board
import adafruit_ccs811
import signal
from adafruit_ssd1306 import SSD1306_I2C
from PIL import Image, ImageDraw, ImageFont

i2c = board.I2C()
ccs811 = adafruit_ccs811.CCS811(i2c)
display = SSD1306_I2C(128, 64, board.I2C(), addr=0x3C)

FONT_SANS_12 = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc" ,12)
FONT_SANS_18 = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc" ,18)

while not ccs811.data_ready:
    pass

# initialize GPIO
GPIO.setwarnings(True)
GPIO.setmode(GPIO.BCM)
temp_sensor = dht11.DHT11(pin=14)

# Mqtt Define      # add
AWSIoT_ENDPOINT = "alij9rhkrwgll-ats.iot.ap-northeast-1.amazonaws.com"
MQTT_PORT = 8883
MQTT_TOPIC_PUB = "ksap-aircondition-topic"
MQTT_TOPIC_SUB = "topicAirConditionSub"
MQTT_ROOTCA = "/home/pi/Downloads/AmazonRootCA1.pem"
MQTT_CERT = "/home/pi/Downloads/d809f41470b4a2d96ef70d807bbaabae3a27b7df436c049c34366bb90985d4fe-certificate.pem.crt"
MQTT_PRIKEY = "/home/pi/Downloads/d809f41470b4a2d96ef70d807bbaabae3a27b7df436c049c34366bb90985d4fe-private.pem.key"

temp_val=0
humi_val=0
eco2_val=0
tvoc_val=0
timer_cnt=0

def mqtt_connect(client, userdata, flags, respons_code):
    print('mqtt connected.')
    # Entry Mqtt Subscribe.
    client.subscribe(MQTT_TOPIC_SUB)
    print('subscribe topic : ' + MQTT_TOPIC_SUB)

def mqtt_message(client, userdata, msg):
    # Get Received Json Data 
    json_dict = json.loads(msg.payload)
    # if use ... json_dict['xxx']

# Publish Loop
def mqtt_publish(arg1 ,arg2):

    global timer_cnt

    tm = datetime.datetime.now()
    tmstr = "{0:%Y-%m-%d %H:%M:%S}".format(tm)

    isSend=False
    if timer_cnt==600:
        isSend=True
        json_msg = json.dumps({"GetDateTime": tmstr, "Temperature": temp_val,"Humidity":humi_val,"CO2":eco2_val,"TVOC":tvoc_val})
        client.publish(MQTT_TOPIC_PUB ,json_msg ,qos=1)
        timer_cnt=0;

    # monitor show
    img = Image.new("1",(display.width, display.height))
    draw = ImageDraw.Draw(img)
    draw.text((0,0),'時刻 ' + tm.strftime('%H:%M:%S'),font=FONT_SANS_12,fill=1)
    draw.text((0,16),'温度 {0:.1f}℃ 湿度 {1:.1f}%'.format(float(temp_val) ,float(humi_val)) ,font=FONT_SANS_12,fill=1)
    draw.text((0,32),'CO2 '+'{:4}'.format(eco2_val)+ ' PPM',font=FONT_SANS_12,fill=1)
    draw.text((0,48),'TVOC '+'{:4}'.format(tvoc_val)+ ' PPB',font=FONT_SANS_12,fill=1)
    display.image(img)
    display.show()

    # print console
    print("[" + ("MQTT送信" if isSend else "        ") + "]datetime:" + tmstr + " Temperature: %-3.1f C" % temp_val + " Humidity: %-3.1f %%" % humi_val + " CO2: %d PPM" % eco2_val + " TVOC: %d PPB" % tvoc_val)

    # counter increment
    timer_cnt = timer_cnt + 1

# Get AirCondition
async def collection_loop():

    global temp_val
    global humi_val
    global eco2_val
    global tvoc_val

    while True:
        try:
            # Get Temperature / Humidity
            result = temp_sensor.read()
            if result.is_valid():
                temp_val = result.temperature
                humi_val = result.humidity
            # Get CO2/TVOC
            if ccs811.data_ready:
                eco2_val=ccs811.eco2
                tvoc_val=ccs811.tvoc
        except Exception as e:
            print("Err!")

        time.sleep(1)

# Main Procedure
if __name__ == '__main__':
    # Mqtt Client Initialize
    client = paho.mqtt.client.Client()
    client.on_connect = mqtt_connect
    client.on_message = mqtt_message
    client.tls_set(MQTT_ROOTCA, certfile=MQTT_CERT, keyfile=MQTT_PRIKEY, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)

    # Connect To Mqtt Broker(aws)
    client.connect(AWSIoT_ENDPOINT, port=MQTT_PORT, keepalive=60)

    # Start Mqtt Subscribe
    client.loop_start()

    # Start Mqtt_Publish
    signal.signal(signal.SIGALRM ,mqtt_publish)
    signal.setitimer(signal.ITIMER_REAL ,1 ,1)

    # Start Collection Loop
    loop = asyncio.get_event_loop()
    loop.run_until_complete(collection_loop())


