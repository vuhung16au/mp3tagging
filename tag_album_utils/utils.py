import os
import datetime

def write_log(log_entries, operation):
    """
    Writes log entries to a timestamped log file in the 'logs' directory.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    # Ensure the logs directory exists
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, f"{operation}_{timestamp}.log")

    with open(log_file_path, 'w', encoding='utf-8') as log_file:
        log_file.write("\n".join(log_entries))
    print(f"{operation.capitalize()} operation completed. Log saved to '{log_file_path}'.")
