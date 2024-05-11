import logging

def log_config(file_path):
    logging.basicConfig(filename=file_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
