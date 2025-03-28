from graph_core.watchers.file_watcher import start_file_watcher

def on_file_event(event_type, file_path):
    print(f"EVENT: {event_type} - {file_path}")

if __name__ == "__main__":
    start_file_watcher(on_file_event, watch_dir="src")
