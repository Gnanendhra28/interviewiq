import threading
from collections import defaultdict


class MetricsCollector:
    """
    Thread-safe Prometheus-compatible Operational Metrics Collector (ADR 042).
    Tracks API request counts, latencies, status codes, background job queue depths, and AI operations.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_metrics()
            return cls._instance

    def _init_metrics(self):
        self.api_requests_total = defaultdict(int)
        self.api_errors_total = defaultdict(int)
        self.api_latency_sum = defaultdict(float)
        self.api_latency_count = defaultdict(int)

        self.job_claimed_total = defaultdict(int)
        self.job_completed_total = defaultdict(int)
        self.job_failed_total = defaultdict(int)

        self.ai_requests_total = defaultdict(int)
        self.ai_failures_total = defaultdict(int)
        self.ai_latency_sum = defaultdict(float)

    def record_api_request(self, method: str, path_template: str, status_code: int, duration_ms: float):
        status_class = f"{status_code // 100}xx"
        key = f"{method}_{path_template}_{status_class}"
        self.api_requests_total[key] += 1
        self.api_latency_sum[key] += duration_ms
        self.api_latency_count[key] += 1
        if status_code >= 400:
            self.api_errors_total[key] += 1

    def record_job_claimed(self, job_type: str):
        self.job_claimed_total[job_type] += 1

    def record_job_completed(self, job_type: str):
        self.job_completed_total[job_type] += 1

    def record_job_failed(self, job_type: str):
        self.job_failed_total[job_type] += 1

    def record_ai_operation(self, provider: str, model: str, duration_ms: float, success: bool = True):
        key = f"{provider}_{model}"
        self.ai_requests_total[key] += 1
        self.ai_latency_sum[key] += duration_ms
        if not success:
            self.ai_failures_total[key] += 1

    def export_metrics_prometheus(self) -> str:
        lines = []
        lines.append("# HELP api_requests_total Total HTTP requests handled")
        lines.append("# TYPE api_requests_total counter")
        for k, v in self.api_requests_total.items():
            lines.append(f'api_requests_total{{label="{k}"}} {v}')

        lines.append("# HELP api_errors_total Total HTTP 4xx/5xx error responses")
        lines.append("# TYPE api_errors_total counter")
        for k, v in self.api_errors_total.items():
            lines.append(f'api_errors_total{{label="{k}"}} {v}')

        lines.append("# HELP job_completed_total Total background jobs completed")
        lines.append("# TYPE job_completed_total counter")
        for k, v in self.job_completed_total.items():
            lines.append(f'job_completed_total{{job_type="{k}"}} {v}')

        lines.append("# HELP ai_requests_total Total AI Provider inferences")
        lines.append("# TYPE ai_requests_total counter")
        for k, v in self.ai_requests_total.items():
            lines.append(f'ai_requests_total{{target="{k}"}} {v}')

        return "\n".join(lines) + "\n"


metrics_collector = MetricsCollector()
