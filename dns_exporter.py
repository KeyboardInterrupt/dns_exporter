#!/usr/bin/env python3

import os
import logging
import asyncio
import dns.resolver
from prometheus_client import start_http_server, Gauge
import time
from collections import defaultdict, deque

# Configuration
DNS_SERVERS = os.getenv("DNS_SERVERS", "8.8.8.8,1.1.1.1").split(",")
TEST_DOMAINS = os.getenv("TEST_DOMAINS", "example.com,google.com").split(",")
PORT = int(os.getenv("PORT", 8000))
WINDOW_SIZE = int(os.getenv("WINDOW_SIZE", 60))
SLEEP_INTERVAL = float(os.getenv("SLEEP_INTERVAL", 1))

# Logging setup
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.ERROR)
logger = logging.getLogger()

# Prometheus metrics
dns_response_avg = Gauge("dns_response_avg_seconds", "Average DNS response time", ["server", "domain"])
dns_response_min = Gauge("dns_response_min_seconds", "Minimum DNS response time", ["server", "domain"])
dns_response_max = Gauge("dns_response_max_seconds", "Maximum DNS response time", ["server", "domain"])
dns_timeouts = Gauge("dns_timeouts_total", "Total DNS timeouts", ["server", "domain"])
dns_no_answer = Gauge("dns_no_answer_total", "Total DNS responses with no answer", ["server", "domain"])
dns_response_queue_length = Gauge("dns_response_queue_length", "Queue length for DNS response times", ["server", "domain"])

# Data storage
response_times = defaultdict(lambda: defaultdict(deque))
timeout_counts = defaultdict(lambda: defaultdict(int))
no_answer_counts = defaultdict(lambda: defaultdict(int))

async def query_dns(server, domain):
    start = time.time()
    current_time = time.time()
    resolver = dns.resolver.Resolver()
    resolver.nameservers = [server]
    try:
        await asyncio.to_thread(resolver.resolve, domain, "A")
        duration = time.time() - start
        response_times[server][domain].append((current_time, duration))
    except dns.resolver.Timeout:
        timeout_counts[server][domain] += 1
        dns_timeouts.labels(server=server, domain=domain).set(timeout_counts[server][domain])
        logger.error(f"Timeout for {domain} on {server}")
    except dns.resolver.NoAnswer:
        no_answer_counts[server][domain] += 1
        dns_no_answer.labels(server=server, domain=domain).set(no_answer_counts[server][domain])
        logger.error(f"No answer for {domain} on {server}")
    except dns.exception.DNSException as e:
        logger.error(f"DNS error for {domain} on {server}: {str(e)}")

async def run_queries():
    next_run = time.monotonic()
    while True:
        tasks = [query_dns(server, domain) for server in DNS_SERVERS for domain in TEST_DOMAINS]
        await asyncio.gather(*tasks)
        update_metrics()
        next_run += SLEEP_INTERVAL
        await asyncio.sleep(max(0, next_run - time.monotonic()))

def update_metrics():
    current_time = time.time()
    for server in DNS_SERVERS:
        for domain in TEST_DOMAINS:
            while response_times[server][domain] and current_time - response_times[server][domain][0][0] > WINDOW_SIZE:
                response_times[server][domain].popleft()
            times = [t[1] for t in response_times[server][domain]]
            if times:
                dns_response_avg.labels(server=server, domain=domain).set(sum(times) / len(times))
                dns_response_min.labels(server=server, domain=domain).set(min(times))
                dns_response_max.labels(server=server, domain=domain).set(max(times))
            dns_response_queue_length.labels(server=server, domain=domain).set(len(times))

if __name__ == "__main__":
    start_http_server(PORT)
    logger.info(f"DNS Exporter running on port {PORT}")
    asyncio.run(run_queries())
