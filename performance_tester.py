import time
import requests
import concurrent.futures
import logging
from typing import Dict, List, Any, Optional
import statistics

class PerformanceTester:
    """
    A class to perform HTTP performance testing, similar to JMeter's functionality
    but simplified for local execution.
    """
    
    def __init__(
        self, 
        target_url: str,
        http_method: str = 'GET',
        num_requests: int = 10,
        concurrency: int = 1,
        timeout: int = 30,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None
    ):
        """
        Initialize the performance tester with test parameters.
        
        Args:
            target_url: The URL to test
            http_method: HTTP method to use (GET, POST, PUT, etc.)
            num_requests: Total number of requests to make
            concurrency: Number of concurrent requests
            timeout: Request timeout in seconds
            headers: HTTP headers to include in requests
            body: Request body for POST/PUT requests
        """
        self.target_url = target_url
        self.http_method = http_method.upper()
        self.num_requests = num_requests
        self.concurrency = concurrency
        self.timeout = timeout
        self.headers = headers or {}
        self.body = body
        
        # Validate inputs
        if self.http_method not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD']:
            raise ValueError(f"Unsupported HTTP method: {http_method}")
            
        if self.concurrency > self.num_requests:
            raise ValueError("Concurrency cannot be greater than the total number of requests")
            
        self.logger = logging.getLogger(__name__)
    
    def make_request(self, request_id: int) -> Dict[str, Any]:
        """
        Make a single HTTP request and return performance metrics.
        
        Args:
            request_id: Unique identifier for this request
            
        Returns:
            Dictionary containing request metrics
        """
        start_time = time.time()
        response = None
        error = None
        
        try:
            kwargs = {
                'url': self.target_url,
                'headers': self.headers,
                'timeout': self.timeout
            }
            
            # Add body for methods that support it
            if self.http_method in ['POST', 'PUT', 'PATCH']:
                kwargs['data'] = self.body
                
            response = requests.request(self.http_method, **kwargs)
            status_code = response.status_code
            response_size = len(response.content)
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
        except requests.exceptions.Timeout:
            error = "Request timed out"
            status_code = 0
            response_size = 0
            response_time = self.timeout * 1000  # Convert timeout to ms
            
        except Exception as e:
            error = str(e)
            status_code = 0
            response_size = 0
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
        return {
            'request_id': request_id,
            'timestamp': time.time(),
            'url': self.target_url,
            'method': self.http_method,
            'status_code': status_code,
            'response_time_ms': response_time,
            'response_size_bytes': response_size,
            'error': error
        }
    
    def run_test(self) -> Dict[str, Any]:
        """
        Run the performance test with the configured parameters.
        
        Returns:
            Dictionary containing all test results and metrics
        """
        self.logger.info(f"Starting performance test for {self.target_url}")
        self.logger.info(f"Method: {self.http_method}, Requests: {self.num_requests}, Concurrency: {self.concurrency}")
        
        start_time = time.time()
        results = []
        
        # Use ThreadPoolExecutor to make concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            # Submit all requests
            future_to_id = {
                executor.submit(self.make_request, i): i 
                for i in range(self.num_requests)
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_id):
                request_id = future_to_id[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Error in request {request_id}: {str(e)}")
                    results.append({
                        'request_id': request_id,
                        'timestamp': time.time(),
                        'url': self.target_url,
                        'method': self.http_method,
                        'status_code': 0,
                        'response_time_ms': 0,
                        'response_size_bytes': 0,
                        'error': str(e)
                    })
        
        total_time = time.time() - start_time
        
        # Calculate summary statistics
        success_results = [r for r in results if r['status_code'] >= 200 and r['status_code'] < 400]
        failed_results = [r for r in results if r not in success_results]
        
        if results:
            response_times = [r['response_time_ms'] for r in results if r['response_time_ms'] > 0]
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                min_response_time = min(response_times)
                max_response_time = max(response_times)
                median_response_time = statistics.median(response_times)
                p90_response_time = statistics.quantiles(response_times, n=10)[8]  # 90th percentile
                p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
                p99_response_time = statistics.quantiles(response_times, n=100)[98]  # 99th percentile
            else:
                avg_response_time = min_response_time = max_response_time = median_response_time = 0
                p90_response_time = p95_response_time = p99_response_time = 0
                
            total_bytes = sum(r['response_size_bytes'] for r in results)
            requests_per_second = self.num_requests / total_time if total_time > 0 else 0
            success_rate = (len(success_results) / self.num_requests) * 100 if self.num_requests > 0 else 0
        else:
            avg_response_time = min_response_time = max_response_time = median_response_time = 0
            p90_response_time = p95_response_time = p99_response_time = 0
            total_bytes = 0
            requests_per_second = 0
            success_rate = 0
            
        # Prepare the final results
        return {
            'summary': {
                'total_requests': self.num_requests,
                'successful_requests': len(success_results),
                'failed_requests': len(failed_results),
                'total_time_seconds': total_time,
                'requests_per_second': requests_per_second,
                'avg_response_time_ms': avg_response_time,
                'min_response_time_ms': min_response_time,
                'max_response_time_ms': max_response_time,
                'median_response_time_ms': median_response_time,
                'p90_response_time_ms': p90_response_time,
                'p95_response_time_ms': p95_response_time,
                'p99_response_time_ms': p99_response_time,
                'total_bytes': total_bytes,
                'success_rate_percent': success_rate
            },
            'requests': results,
            'config': {
                'target_url': self.target_url,
                'http_method': self.http_method,
                'num_requests': self.num_requests,
                'concurrency': self.concurrency,
                'timeout': self.timeout,
            }
        }
