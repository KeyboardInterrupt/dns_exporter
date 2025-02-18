# DNS Exporter with Prometheus Metrics

This Python script is a DNS exporter that monitors DNS query performance and exposes metrics for Prometheus scraping. It queries multiple DNS servers for a list of domains, tracks response times, and reports various DNS statistics such as response times, timeouts, no answers, and other failure scenarios.

### Features
- Queries multiple DNS servers for a list of domains.
- Collects DNS query response times (average, minimum, and maximum).
- Tracks DNS timeouts, no answers, and failures.
- Exposes Prometheus-compatible metrics for scraping.
- Configurable parameters through environment variables.
- Uses a sliding window mechanism to track DNS metrics over a specified time window.

### Prerequisites
- Python 3.x
- Prometheus client (`prometheus_client`)
- `dnspython` library for DNS resolution

### Setup

#### Manual Way

1. **Clone the repository** (or download the script and required files).
2. **Configure the environment** variables:
   - `DNS_SERVERS`: A comma-separated list of DNS server IPs (default: `8.8.8.8,1.1.1.1`).
   - `TEST_DOMAINS`: A comma-separated list of domains to test (default: `example.com,google.com`).
   - `PORT`: The port for Prometheus to scrape metrics (default: `8000`).
   - `WINDOW_SIZE`: The window size in seconds to track DNS response times (default: `60`).
   - `SLEEP_INTERVAL`: The sleep interval between queries in seconds (default: `1`).

3. **Install dependencies**:
   Run the following command to install the required Python libraries:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Script**:
   You can run the script directly by executing:
   ```bash
   python3 dns_exporter.py
   ```

5. **Prometheus Configuration**:
   In your Prometheus configuration file, add the following scrape configuration:
   ```yaml
   scrape_configs:
     - job_name: 'dns_exporter'
       static_configs:
         - targets: ['<your_host>:8000']
   ```

#### Docker Setup

To deploy the script with Docker, we provide a `Dockerfile` and `docker-compose.yml` for easy setup.

#### example docker-compose.yml

```yaml
version: '3'

services:
  dns_exporter:
    build: .
    ports:
      - "8000:8000"
    environment:
      DNS_SERVERS: "8.8.8.8,1.1.1.1"
      TEST_DOMAINS: "example.com,google.com"
      WINDOW_SIZE: 60
      SLEEP_INTERVAL: 1
    restart: always
```

### Running with Docker

1. **Build and run the container** using Docker Compose:
   ```bash
   docker-compose up -d --build
   ```

2. **Access Prometheus Metrics**:
   Once the container is running, the Prometheus metrics will be available at `http://<server_address>:8000`.

### Metrics Exposed
- `dns_response_avg_seconds_<window_size>s`: Average DNS response time in seconds for each server and domain.
- `dns_response_min_seconds_<window_size>s`: Minimum DNS response time in seconds for each server and domain.
- `dns_response_max_seconds_<window_size>s`: Maximum DNS response time in seconds for each server and domain.
- `dns_timeouts_total_<window_size>s`: Total number of DNS timeouts over the specified window.
- `dns_no_answer_total_<window_size>s`: Total number of DNS queries with no answer over the specified window.
- `dns_lifetime_timeout_total_<window_size>s`: Total number of DNS queries that timed out over the specified window.
- `dns_server_failures_total_<window_size>s`: Total number of DNS server failures over the specified window.
- `dns_other_failures_total_<window_size>s`: Total number of other DNS failures over the specified window.
- `dns_high_latency_total_<window_size>s`: Total number of DNS queries with high latency (>= 1s) over the specified window.
- `dns_response_queue_length_<window_size>s`: Queue length for DNS response times over the specified window.

### Troubleshooting
- **No Metrics Exposed**: Ensure that Prometheus is configured to scrape the correct port and that the DNS servers are accessible.
- **DNS Failures**: The script logs errors when DNS queries fail, including no answers, timeouts, and other DNS exceptions to STDOUT (check `docker logs`)

### License
This project is licensed under the MIT License. See LICENSE for more information.
