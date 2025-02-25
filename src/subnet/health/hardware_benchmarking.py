import psutil
import time
import threading
from tqdm import tqdm
from hypermind.utils import get_logger

logger = get_logger(__name__)

# python ./src/subnet/health/hardware_benchmarking.py

def benchmark_app(interval=0.5):
  """
  Monitors CPU, RAM, storage, and network usage indefinitely, tracking max values.
  Stops when interrupted manually (Ctrl+C), with tqdm visualization.

  :param interval: How often to log system usage (in seconds).
  """
  cpu_cores = psutil.cpu_count(logical=False)  # Physical cores
  logical_cores = psutil.cpu_count(logical=True)  # Logical cores

  print(f"🔹 Benchmarking system indefinitely (Updates every {interval} sec)")
  print(f"💻 CPU Cores: {cpu_cores} Physical, {logical_cores} Logical")

  # Track max values
  max_cpu_usage = 0
  max_ram_usage = 0
  max_storage_used = 0
  max_network_sent = 0
  max_network_recv = 0

  try:
    # Initialize tqdm bars
    cpu_bar = tqdm(total=100, desc="🖥️ CPU Usage (%)", position=0, bar_format="{desc}: {percentage:.1f}%|{bar}| {n:.1f}%")
    ram_bar = tqdm(total=psutil.virtual_memory().total / (1024 ** 3), desc="🛠️ RAM Usage (GB)", position=1, bar_format="{desc}: {n:.2f}GB|{bar}| {total:.2f}GB")
    storage_bar = tqdm(total=psutil.disk_usage("/").total / (1024 ** 3), desc="💾 Storage Used (GB)", position=2, bar_format="{desc}: {n:.2f}GB|{bar}| {total:.2f}GB")
    # network_bar_sent = tqdm(total=1000, desc="🌍 Network Sent (MB)", position=3, bar_format="{desc}: {n:.2f}MB|{bar}| {total:.2f}MB")
    # network_bar_recv = tqdm(total=1000, desc="🌍 Network Received (MB)", position=4, bar_format="{desc}: {n:.2f}MB|{bar}| {total:.2f}MB")

    while True:
      # CPU Usage
      cpu_usage = psutil.cpu_percent(interval=1)
      max_cpu_usage = max(max_cpu_usage, cpu_usage)
      cpu_bar.n = cpu_usage
      cpu_bar.refresh()

      # RAM Usage
      ram_info = psutil.virtual_memory()
      ram_usage = ram_info.used / (1024 ** 3)  # Convert to GB
      max_ram_usage = max(max_ram_usage, ram_usage)
      ram_bar.n = ram_usage
      ram_bar.refresh()

      # Storage Usage
      storage_info = psutil.disk_usage("/")
      storage_used = storage_info.used / (1024 ** 3)  # Convert to GB
      max_storage_used = max(max_storage_used, storage_used)
      storage_bar.n = storage_used
      storage_bar.refresh()

      # Network Usage
      net_io = psutil.net_io_counters()
      network_sent = net_io.bytes_sent / (1024 ** 2)  # Convert to MB
      network_recv = net_io.bytes_recv / (1024 ** 2)
      max_network_sent = max(max_network_sent, network_sent)
      max_network_recv = max(max_network_recv, network_recv)

      # network_bar_sent.n = network_sent
      # network_bar_sent.refresh()

      # network_bar_recv.n = network_recv
      # network_bar_recv.refresh()

      # time.sleep(interval - 1)
      time.sleep(0.5)
  except Exception as e:
    logger.error("Exception", e, exc_info=True)
  except KeyboardInterrupt:
    print("\n🚀 Benchmarking stopped! Here are the max recorded values:")
    print(f"🔥 Max CPU Usage: {max_cpu_usage}%")
    print(f"💾 Max RAM Usage: {max_ram_usage:.2f} GB")
    print(f"📀 Max Storage Used: {max_storage_used:.2f} GB")
    print(f"🌍 Max Network Sent: {max_network_sent:.2f} MB")
    print(f"🌍 Max Network Received: {max_network_recv:.2f} MB")

if __name__ == "__main__":
  print("running")
  # Run benchmark in a separate thread so it doesn't block the app
  benchmark_thread = threading.Thread(target=benchmark_app, args=(5,), daemon=False)
  benchmark_thread.start()
