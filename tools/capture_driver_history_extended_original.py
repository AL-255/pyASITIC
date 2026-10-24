"""The complete small square/rectangular native histories, including no vias."""
import capture_driver_history_original as capture
from capture_prelude_storage_extended_original import jobs


if __name__=='__main__':capture.main(fixture_name='driver_history_extended_original.json.gz',parent_name='cache_storage_extended_original.json.gz',job_factory=jobs)
