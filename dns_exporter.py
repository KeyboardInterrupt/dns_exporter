#!/usr/bin/env python3

import os
import logging
from prometheus_client import start_http_server, Gauge
import dns.resolver
import time
from collections import defaultdict, deque

# Configuration from environment variables or defaults
DNS_SERVERS = os.getenv("DNS_SERVERS", "8.8.8.8,1.1.1.1").split(",")
TEST_DOMAINS = os.getenv("TEST_DOMAINS", "example.com,google.com").split(",")
PORT = int(os.getenv("PORT", 8000))
WINDOW_SIZE = int(os.getenv("WINDOW_SIZE", 60))  # 60 seconds
SLEEP_INTERVAL = float(os.getenv("SLEEP_INTERVAL", 1))  # Sleep interval in seconds, default is 1 second

# Set up logging with timestamp
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.ERROR)
logger = logging.getLogger()

# Prometheus metrics
dns_response_avg = Gauge(f"dns_response_avg_seconds_{WINDOW_SIZE}s", f"Average DNS response time over {WINDOW_SIZE}s", ["server", "domain"])
dns_response_min = Gauge(f"dns_response_min_seconds_{WINDOW_SIZE}s", f"Minimum DNS response time over {WINDOW_SIZE}s", ["server", "domain"])
dns_response_max = Gauge(f"dns_response_max_seconds_{WINDOW_SIZE}s", f"Maximum DNS response time over {WINDOW_SIZE}s", ["server", "domain"])
dns_timeouts = Gauge(f"dns_timeouts_total_{WINDOW_SIZE}s", f"Number of DNS timeouts over {WINDOW_SIZE}s", ["server", "domain"])
dns_no_answer = Gauge(f"dns_no_answer_total_{WINDOW_SIZE}s", f"Number of DNS responses with no answer over {WINDOW_SIZE}s", ["server", "domain"])
dns_lifetime_timeout = Gauge(f"dns_lifetime_timeout_total_{WINDOW_SIZE}s", f"Number of DNS queries that timed out over {WINDOW_SIZE}s", ["server", "domain"])
dns_server_failures = Gauge(f"dns_server_failures_total_{WINDOW_SIZE}s", f"Number of DNS server failures over {WINDOW_SIZE}s", ["server", "domain"])
dns_other_failures = Gauge(f"dns_other_failures_total_{WINDOW_SIZE}s", f"Number of other DNS failures over {WINDOW_SIZE}s", ["server", "domain"])
dns_high_latency = Gauge(f"dns_high_latency_total_{WINDOW_SIZE}s", f"Number of DNS queries with high latency (>= 1s) over {WINDOW_SIZE}s", ["server", "domain"])
dns_response_queue_length = Gauge(f"dns_response_queue_length_{WINDOW_SIZE}s", f"Queue length for DNS response times over {WINDOW_SIZE}s", ["server", "domain"])

# Store response times with timestamps (a sliding window)
response_times = defaultdict(lambda: defaultdict(lambda: deque()))  # No maxlen here
timeout_counts = defaultdict(lambda: defaultdict(int))
no_answer_counts = defaultdict(lambda: defaultdict(int))
lifetime_timeout_counts = defaultdict(lambda: defaultdict(int))
server_failure_counts = defaultdict(lambda: defaultdict(int))
other_failure_counts = defaultdict(lambda: defaultdict(int))
high_latency_counts = defaultdict(lambda: defaultdict(int))

def query_dns():
    current_time = time.time()
    for server in DNS_SERVERS:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [server]

        for domain in TEST_DOMAINS:
            start = time.time()
            try:
                resolver.resolve(domain, "A")
                duration = time.time() - start
                # Add the timestamped response time to the deque
                response_times[server][domain].append((current_time, duration))
                if duration >= 1:
                    high_latency_counts[server][domain] += 1
                    dns_high_latency.labels(server=server, domain=domain).set(high_latency_counts[server][domain])
            except dns.resolver.NoAnswer:
                no_answer_counts[server][domain] += 1
                dns_no_answer.labels(server=server, domain=domain).set(no_answer_counts[server][domain])
                logger.error(f"No answer for {domain} on server {server}")
            except dns.resolver.LifetimeTimeout:
                lifetime_timeout_counts[server][domain] += 1
                dns_lifetime_timeout.labels(server=server, domain=domain).set(lifetime_timeout_counts[server][domain])
                logger.error(f"Lifetime timeout for {domain} on server {server}")
            except dns.exception.DNSException as e:
                other_failure_counts[server][domain] += 1
                dns_other_failures.labels(server=server, domain=domain).set(other_failure_counts[server][domain])
                logger.error(f"DNS exception for {domain} on server {server}: {str(e)}")
            except Exception as e:
                server_failure_counts[server][domain] += 1
                dns_server_failures.labels(server=server, domain=domain).set(server_failure_counts[server][domain])
                logger.error(f"General failure for {domain} on server {server}: {str(e)}")

def update_metrics():
    current_time = time.time()
    for server in DNS_SERVERS:
        for domain in TEST_DOMAINS:
            # Remove any old response times from deque that are outside the sliding window (older than WINDOW_SIZE seconds)
            while response_times[server][domain] and current_time - response_times[server][domain][0][0] > WINDOW_SIZE:
                response_times[server][domain].popleft()  # Remove old response times

            times = [duration for timestamp, duration in response_times[server][domain]]

            if times:
                dns_response_avg.labels(server=server, domain=domain).set(sum(times) / len(times))
                dns_response_min.labels(server=server, domain=domain).set(min(times))
                dns_response_max.labels(server=server, domain=domain).set(max(times))

            # Set the queue length as a Prometheus metric
            dns_response_queue_length.labels(server=server, domain=domain).set(len(response_times[server][domain]))

if __name__ == "__main__":
    start_http_server(PORT)
    logger.info(f"DNS Exporter running on port {PORT}")

    while True:
        query_dns()
        update_metrics()
        time.sleep(SLEEP_INTERVAL)  # Sleep interval based on environment variable
