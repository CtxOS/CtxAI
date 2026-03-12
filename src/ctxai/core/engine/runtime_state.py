_job_queue = None

def get_job_queue():
    global _job_queue
    return _job_queue

def set_job_queue(queue):
    global _job_queue
    _job_queue = queue
