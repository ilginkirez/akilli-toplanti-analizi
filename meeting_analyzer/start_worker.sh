#!/bin/bash
celery -A src.celery_app worker --loglevel=info --concurrency=4 --pool=prefork
