import logging
from typing import Dict, Any, List

class ReportGenerator:
    """
    Generates performance test reports from raw test results.
    """
    
    def __init__(self, test_results: Dict[str, Any]):
        """
        Initialize the report generator with test results.
        
        Args:
            test_results: The results from a PerformanceTester run
        """
        self.test_results = test_results
        self.logger = logging.getLogger(__name__)
    
    def generate_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive report from test results.
        
        Returns:
            Dictionary containing the processed report data
        """
        self.logger.info("Generating performance test report")
        
        # Extract summary stats from test results
        summary = self.test_results.get('summary', {})
        requests = self.test_results.get('requests', [])
        config = self.test_results.get('config', {})
        
        # Calculate status code distribution
        status_codes = {}
        for req in requests:
            status = req.get('status_code', 0)
            if status in status_codes:
                status_codes[status] += 1
            else:
                status_codes[status] = 1
        
        # Calculate response time distribution for histogram
        response_times = [req.get('response_time_ms', 0) for req in requests]
        max_time = max(response_times) if response_times else 0
        
        # Create bins for histogram (10 bins)
        bin_size = max_time / 10 if max_time > 0 else 1
        bins = []
        for i in range(10):
            lower = i * bin_size
            upper = (i + 1) * bin_size
            count = sum(1 for rt in response_times if lower <= rt < upper)
            bins.append({
                'range': f"{lower:.1f} - {upper:.1f} ms",
                'count': count
            })
        
        # Calculate time series data for requests over time
        if requests:
            # Sort by timestamp
            sorted_requests = sorted(requests, key=lambda x: x.get('timestamp', 0))
            start_time = sorted_requests[0].get('timestamp', 0)
            
            # Group by 1-second intervals
            time_series = []
            current_interval = 0
            interval_count = 0
            interval_response_times = []
            
            for req in sorted_requests:
                req_time = req.get('timestamp', 0) - start_time
                req_interval = int(req_time)
                
                # If we've moved to a new interval, record the previous one
                if req_interval > current_interval:
                    if interval_count > 0:
                        avg_resp_time = sum(interval_response_times) / len(interval_response_times) if interval_response_times else 0
                        time_series.append({
                            'time': current_interval,
                            'requests': interval_count,
                            'avg_response_time': avg_resp_time
                        })
                    
                    # Fill in any missing intervals
                    for i in range(current_interval + 1, req_interval):
                        time_series.append({
                            'time': i,
                            'requests': 0,
                            'avg_response_time': 0
                        })
                    
                    current_interval = req_interval
                    interval_count = 1
                    interval_response_times = [req.get('response_time_ms', 0)]
                else:
                    interval_count += 1
                    interval_response_times.append(req.get('response_time_ms', 0))
            
            # Add the last interval
            if interval_count > 0:
                avg_resp_time = sum(interval_response_times) / len(interval_response_times) if interval_response_times else 0
                time_series.append({
                    'time': current_interval,
                    'requests': interval_count,
                    'avg_response_time': avg_resp_time
                })
        else:
            time_series = []
        
        # Build the final report
        report = {
            'summary': summary,
            'status_code_distribution': [
                {'status_code': status, 'count': count}
                for status, count in status_codes.items()
            ],
            'response_time_histogram': bins,
            'time_series': time_series,
            'requests': requests,
            'config': config
        }
        
        self.logger.info("Report generation complete")
        return report
