FROM alfg/nginx-rtmp

# Install Python and pip
RUN apk add --no-cache python3 py3-pip supervisor gcc musl-dev python3-dev linux-headers

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf
COPY nginx.conf /etc/nginx/nginx.conf.template

# Create directory for your data
RUN mkdir -p /opt/data/hls

# Copy your files
COPY async_hls_file_watcher.py /opt/data/
COPY requirements.txt /opt/data/
COPY .env /opt/data/
COPY health_check.py /opt/data/

# Set working directory
WORKDIR /opt/data

# Install Python requirements
RUN pip3 install -r requirements.txt

# Add Supervisor configuration
COPY supervisord.conf /etc/supervisord.conf

# Clean up build dependencies to reduce image size
RUN apk del gcc musl-dev python3-dev linux-headers

EXPOSE 80
EXPOSE 1935

# Start Supervisor
CMD envsubst "$(env | sed -e 's/=.*//' -e 's/^/\$/g')" < \
  /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf && \
  /usr/bin/supervisord -c /etc/supervisord.conf
