"""Cache storage in all independently selected small FFT histories."""
import capture_cache_storage_original as capture
from capture_prelude_storage_extended_original import jobs


if __name__=='__main__':capture.main(fixture_name='cache_storage_extended_original.json.gz',parent_name='libio_storage_extended_original.json.gz',job_factory=jobs)
