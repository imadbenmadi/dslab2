"""
MQTT-Based Smart City System - Complete Deployment Guide

This document covers:

- MQTT infrastructure setup with PKI/mTLS
- Multi-service deployment with MQTT messaging
- Security, monitoring, and production best practices
  """

# ============================================================================

# 1. QUICK START (5 minutes)

# ============================================================================

"""
Fastest way to get MQTT services running:

1. Install dependencies:
   pip install -r requirements.txt

2. Run the orchestrator (handles everything):
   python -m services.orchestrator_mqtt

    OR if you already have MQTT broker running:
    python -m services.orchestrator_mqtt --skip-broker

3. Check health:
   curl http://localhost:5000/health
4. Stop with Ctrl+C
   """

# ============================================================================

# 2. MQTT INFRASTRUCTURE SETUP

# ============================================================================

"""
The system uses three-tier PKI with MQTT for production-grade security.

PKI Hierarchy:
┌─────────────────────────────────────────┐
│ Root CA (4096-bit RSA, 10-year) │
│ Self-signed, offline storage │
└─────────────────────────────────────────┘
│
├─→ Intermediate CA (2048-bit, 5-year)
│ Online signing
│
├─→ Intermediate CA (2048-bit, 5-year)
│ (Optional for different roles)
│
└─→ [Services Sign with Intermediate]

Service Certificates (2048-bit RSA, 1-year):

- vehicle-service.crt / .key
- fog-service.crt / .key
- cloud-service.crt / .key
- mosquitto.crt / .key (MQTT broker)

Auto-rotation:

- Background daemon checks every 24h
- Rotates certs 30 days before expiry
- Graceful renewal without downtime
- CRL tracking for revocation
  """

# ============================================================================

# 3. DOCKER SETUP (Recommended for Development)

# ============================================================================

"""
Start MQTT broker with Docker:

docker run -d \\
--name dslab-mosquitto \\
-p 1883:1883 \\
-p 8883:8883 \\
-v $(pwd)/certs:/mosquitto/certs \\
-v $(pwd)/certs/mosquitto.conf:/mosquitto/config/mosquitto.conf \\
eclipse-mosquitto:latest

Verify connection:
nc -zv localhost 8883

Monitor logs:
docker logs -f dslab-mosquitto
"""

# ============================================================================

# 4. KUBERNETES DEPLOYMENT

# ============================================================================

KUBERNETES_MANIFEST = """

# Mosquitto MQTT Broker ConfigMap

---

apiVersion: v1
kind: ConfigMap
metadata:
name: mosquitto-config
namespace: smart-city
data:
mosquitto.conf: |
listener 1883
protocol mqtt
listener 8883  
 protocol mqtt
cafile /etc/mqtt/certs/ca.crt
certfile /etc/mqtt/certs/mosquitto.crt
keyfile /etc/mqtt/certs/mosquitto.key
require_certificate true
persistence true
persistence_location /mosquitto/data/

# Mosquitto Certificates Secret

---

apiVersion: v1
kind: Secret
metadata:
name: mqtt-certs
namespace: smart-city
type: Opaque
stringData:
ca.crt: |
-----BEGIN CERTIFICATE-----
[Insert CA certificate here - from certs/ca.crt]
-----END CERTIFICATE-----
mosquitto.crt: |
-----BEGIN CERTIFICATE-----
[Insert broker certificate here]
-----END CERTIFICATE-----
mosquitto.key: |
-----BEGIN PRIVATE KEY-----
[Insert broker private key here]
-----END PRIVATE KEY-----

# Mosquitto MQTT Broker Deployment

---

apiVersion: apps/v1
kind: Deployment
metadata:
name: mosquitto
namespace: smart-city
spec:
replicas: 1
selector:
matchLabels:
app: mosquitto
template:
metadata:
labels:
app: mosquitto
spec:
containers: - name: mosquitto
image: eclipse-mosquitto:2.0
ports: - containerPort: 1883
name: mqtt - containerPort: 8883
name: mqtt-tls
volumeMounts: - name: config
mountPath: /mosquitto/config - name: certs
mountPath: /etc/mqtt/certs - name: data
mountPath: /mosquitto/data
resources:
requests:
memory: "256Mi"
cpu: "250m"
limits:
memory: "512Mi"
cpu: "500m"
livenessProbe:
tcpSocket:
port: 1883
initialDelaySeconds: 10
periodSeconds: 10
volumes: - name: config
configMap:
name: mosquitto-config - name: certs
secret:
secretName: mqtt-certs - name: data
emptyDir: {}

# Mosquitto Service

---

apiVersion: v1
kind: Service
metadata:
name: mosquitto
namespace: smart-city
spec:
selector:
app: mosquitto
ports:

- port: 1883
  targetPort: 1883
  name: mqtt
  protocol: TCP
- port: 8883
  targetPort: 8883
  name: mqtt-tls
  protocol: TCP
  type: ClusterIP

# Vehicle Service Deployment

---

apiVersion: apps/v1
kind: Deployment
metadata:
name: vehicle-service
namespace: smart-city
spec:
replicas: 2
selector:
matchLabels:
app: vehicle-service
template:
metadata:
labels:
app: vehicle-service
spec:
containers: - name: vehicle-service
image: smart-city:vehicle-service
env: - name: MQTT_HOST
value: "mosquitto" - name: MQTT_PORT
value: "8883" - name: CERT_DIR
value: "/etc/mqtt/certs"
volumeMounts: - name: certs
mountPath: /etc/mqtt/certs
readOnly: true
resources:
requests:
memory: "512Mi"
cpu: "250m"
limits:
memory: "1Gi"
cpu: "500m"
volumes: - name: certs
secret:
secretName: mqtt-certs

# Fog Service Deployment

---

apiVersion: apps/v1
kind: Deployment
metadata:
name: fog-service
namespace: smart-city
spec:
replicas: 2
selector:
matchLabels:
app: fog-service
template:
metadata:
labels:
app: fog-service
spec:
containers: - name: fog-service
image: smart-city:fog-service
env: - name: MQTT_HOST
value: "mosquitto" - name: MQTT_PORT
value: "8883" - name: CERT_DIR
value: "/etc/mqtt/certs"
volumeMounts: - name: certs
mountPath: /etc/mqtt/certs
readOnly: true
volumes: - name: certs
secret:
secretName: mqtt-certs

# Cloud Service Deployment

---

apiVersion: apps/v1
kind: Deployment
metadata:
name: cloud-service
namespace: smart-city
spec:
replicas: 1
selector:
matchLabels:
app: cloud-service
template:
metadata:
labels:
app: cloud-service
spec:
containers: - name: cloud-service
image: smart-city:cloud-service
ports: - containerPort: 5000
name: api
env: - name: MQTT_HOST
value: "mosquitto" - name: MQTT_PORT
value: "8883" - name: CERT_DIR
value: "/etc/mqtt/certs"
volumeMounts: - name: certs
mountPath: /etc/mqtt/certs
readOnly: true
resources:
requests:
memory: "512Mi"
cpu: "250m"
limits:
memory: "1Gi"
cpu: "500m"
volumes: - name: certs
secret:
secretName: mqtt-certs

# Cloud Service API Endpoint

---

apiVersion: v1
kind: Service
metadata:
name: cloud-service-api
namespace: smart-city
spec:
selector:
app: cloud-service
ports:

- port: 5000
  targetPort: 5000
  name: api
  type: LoadBalancer
  """

# ============================================================================

# 5. CERTIFICATE SETUP COMMANDS

# ============================================================================

"""
Bootstrap PKI infrastructure:

python -c "
from infrastructure.pki_manager import PKIManager
from infrastructure.mqtt_pki_integration import bootstrap_mqtt_infrastructure

pki, provisioner = bootstrap_mqtt_infrastructure(cert_dir='certs')
print('PKI bootstrapped successfully')
print(f'Services: {provisioner.list_provisioned_services()}')
"

Check certificate status:

python -c "
from infrastructure.pki_manager import PKIManager

pki = PKIManager()
rotation_needed = pki.check_rotation_needed()
for cert_path in rotation_needed:
print(f'Rotate: {cert_path}')
"

Export deployment bundle:

python -c "
from infrastructure.mqtt_pki_integration import MQTTServiceProvisioner
from infrastructure.pki_manager import PKIManager

pki = PKIManager()
provisioner = MQTTServiceProvisioner(pki)
provisioner.export_cert_bundle('deployment-bundle.tar.gz')
"

Rotate a certificate manually:

python -c "
from infrastructure.pki_manager import PKIManager

pki = PKIManager()
cert, key, chain = pki.rotate_certificate(
'certs/vehicle-service.crt',
'vehicle-service',
'vehicle'
)
"
"""

# ============================================================================

# 6. MQTT CLIENT EXAMPLES

# ============================================================================

MQTT_PUBLISH_EXAMPLE = """
from infrastructure.mqtt_bus import MQTTServiceBus, MQTTQoS

# Connect with mTLS

bus = MQTTServiceBus(
service_name='my-client',
broker_host='localhost',
broker_port=8883,
cert_dir='certs',
enable_tls=True,
qos=MQTTQoS.AT_LEAST_ONCE
)

if bus.connect(): # Publish message
msg_id = bus.publish(
'vehicle/status',
{'vehicle_id': 'v001', 'status': 'online'},
target_service='fog-service',
qos=1
)
print(f'Published: {msg_id}')

    # Subscribe to events
    def on_message(msg):
        print(f'Received: {msg.payload}')

    bus.subscribe('fog/decision', on_message)

    # Request-reply pattern
    response = bus.request_reply(
        'compute/task',
        {'data': 'hello'},
        target_service='fog-service',
        timeout_s=5.0
    )
    if response:
        print(f'Reply: {response}')

"""

# ============================================================================

# 7. MONITORING AND DEBUGGING

# ============================================================================

"""
Check MQTT broker status:

mosquitto_sub -h localhost -p 8883 \\
--cafile certs/ca.crt \\
--cert certs/cloud-service.crt \\
--key certs/cloud-service.key \\
-t '#'

Publish test message:

mosquitto_pub -h localhost -p 8883 \\
--cafile certs/ca.crt \\
--cert certs/cloud-service.crt \\
--key certs/cloud-service.key \\
-t 'test/message' \\
-m 'Hello MQTT'

Monitor service connections:

docker exec dslab-mosquitto mosquitto_info

View MQTT broker logs:

docker logs -f dslab-mosquitto | grep -E 'client|error|warn'

Check certificate expiration:

openssl x509 -in certs/vehicle-service.crt -text -noout | grep -E 'Not Before|Not After'
"""

# ============================================================================

# 8. PRODUCTION CHECKLIST

# ============================================================================

"""
☐ PKI ROOT CA stored offline (not in certs/ dir)
☐ Certificate rotation daemon running continuously
☐ MQTT broker replicated (Kubernetes StatefulSet recommended)
☐ All service connections require TLS/mTLS (enable_tls=True)
☐ QoS set appropriately:

- Critical events: QoS 2 (exactly once)
- High priority: QoS 1 (at least once)
- Best-effort: QoS 0 (at most once)
  ☐ MQTT broker monitored for:
- Connection count
- Message rate (pub/sub)
- Memory usage
- Disk persistence
  ☐ Certificate monitoring alerts:
- 60 days before expiry
- Rotation failures
- CRL updates
  ☐ Network segmentation:
- MQTT broker on separate subnet
- Service-to-broker TLS only
- No plaintext MQTT in production (port 1883 disabled)
  ☐ Backup certificates and encryption keys
  ☐ Regular certificate rotation schedule (quarterly minimum)
  ☐ CRL (Certificate Revocation List) endpoint operational
  ☐ Service health checks:
- /health endpoint (5s interval)
- MQTT keepalive: 60s
- Circuit breaker for broker connection loss
  ☐ OpenFlow controller integrated for network control
  ☐ Model signing enabled for Agent protection
  """

# ============================================================================

# 9. TROUBLESHOOTING

# ============================================================================

"""
Issue: Services fail to connect to MQTT broker

Debug steps:

1. Check broker is running:
   nc -zv localhost 8883

2. Check certificates exist:
   ls -la certs/

3. Check certificate validity:
   openssl x509 -in certs/cloud-service.crt -text -noout

4. Verify cert chain:
   openssl verify -CAfile certs/ca.crt certs/vehicle-service.crt

5. Test TLS connection:
   openssl s_client -connect localhost:8883 \\
   -cert certs/vehicle-service.crt \\
   -key certs/vehicle-service.key \\
   -CAfile certs/ca.crt

Issue: Certificate rotation not working

Check:

1. Rotation daemon is running:
   ps aux | grep rotation

2. Certificate expiry dates:
   openssl x509 -in certs/vehicle-service.crt -noout -dates

3. Daemon logs for errors:
   tail -f mqtt-pki-rotation.log

Issue: High latency/dropped messages

Analyze:

1. MQTT broker CPU/memory:
   docker stats dslab-mosquitto

2. Network packet loss:
   ping -c 100 localhost | grep loss

3. Increase QoS (at cost of overhead):
   qos=MQTTQoS.EXACTLY_ONCE # QoS 2

4. Adjust keepalive:
   client.keepalive = 120 # seconds
   """

# ============================================================================

# 10. SCALING CONSIDERATIONS

# ============================================================================

"""
For production scale:

MQTT Broker HA:

- Use EMQX or HiveMQ (enterprise support)
- Clustering with node discovery
- Persistent message queue
- Load balancing across brokers

Service Scaling:

- Kubernetes auto-scaling based on MQTT message rate
- Service discovery (DNS, Consul, Kubernetes service)
- Session affinity for stateful services

Data Persistence:

- Enable MQTT broker persistence
- Archive task history to time-series DB
- Backup encryption keys separately

Security Enhancements:

- Rate limiting per service
- Message signing (in addition to transport TLS)
- Access control lists (ACLs) per topic
- DDoS protection on MQTT broker

Monitoring Stack (Recommended):

- Prometheus for metrics (MQTT broker + services)
- Grafana for visualization
- ELK stack for log aggregation
- Jaeger for distributed tracing
  """

if **name** == "**main**":
print(**doc**)
