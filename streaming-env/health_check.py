from flask import Flask, Response
import psutil

app = Flask(__name__)

@app.route('/health')
def health_check():
    cpu_percent = psutil.cpu_percent()
    mem_percent = psutil.virtual_memory().percent
    
    # Define your threshold here
    if cpu_percent < 80 and mem_percent < 80:
        return Response(f"OK - CPU: {cpu_percent}%, Memory: {mem_percent}%", status=200)
    else:
        return Response("Service Unavailable", status=503)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)