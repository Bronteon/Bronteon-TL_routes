import psutil
import time
import subprocess

# Change this to the name of the application you want to monitor
TARGET_APP_NAME = "TL.exe"
LOG_FILE = "remote_ips.log"

# Set to store unique IPs
logged_ips = set()

# Store previously seen connections
previous_connections = set()

#VPN route details
subnet_mask = "255.255.255.255"
gateway = "10.8.0.1"
metric = 2

def find_process_by_name(name):
    """Find a process by its name."""
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == name:
            return proc.info['pid']
    return None

def log_remote_ip(ip):
    """Log the remote IP address to a file only if it's unique."""
    if ip not in logged_ips and ip != "127.0.0.1":
        with open(LOG_FILE, 'a') as f:
            f.write(f"{ip}\n")
        logged_ips.add(ip)
        print(f"Logged new IP: {ip}")

def monitor_connections(pid):
    global previous_connections
    """Monitor network connections for a specific process by its PID."""
    try:
        proc = psutil.Process(pid)
        connections = proc.connections(kind='inet')
        new_connections = set()

        for conn in connections:
            if conn.status == psutil.CONN_ESTABLISHED:
                remote_ip = conn.raddr.ip
                if remote_ip != "127.0.0.1":
                    new_connections.add(remote_ip)

        # Find connections that are new
        new_ips = new_connections - previous_connections
        for ip in new_ips:
            log_remote_ip(ip)
            add_route(ip, subnet_mask, gateway, metric)

        # Update the previously seen connections
        previous_connections = new_connections

    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        pass

def add_route(destination, subnet_mask, gateway, metric=1):
    """
    Adds a route to the Windows routing table.

    Parameters:
    destination (str): The destination network (e.g., "192.168.1.0").
    subnet_mask (str): The subnet mask (e.g., "255.255.255.0").
    gateway (str): The gateway IP address (e.g., "192.168.1.1").
    metric (int, optional): The metric for the route (default is 1).
    """
    try:
        # Command to add a new route
        command = ["route", "add", destination, "mask", subnet_mask, gateway, "metric", str(metric)]
        
        # Run the command as admin using subprocess
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Output the result
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        # Handle errors
        #print(f"Error: {e.stderr}")
        print(e)

if __name__ == "__main__":
    # Open the file and read the IP addresses if any
    try:
        with open('remote_ips.log', 'r') as file:
            # Read each line, strip whitespace, and add the IP to the set
            for line in file:
                ip = line.strip()  # Remove any extra whitespace, like newlines
                if ip:  # Ensure the line is not empty
                    logged_ips.add(ip)
        
        # Print the set of IPs to confirm
        print("Logged IPs:", logged_ips)

    except FileNotFoundError:
        print("Error: 'remote_ips.log' file not found.")
    
    #Add known IP's to the routing table
    for ip in logged_ips:
        add_route(ip, subnet_mask, gateway, metric)

    print(f"{len(logged_ips)} routes added")

    pid = None
    while pid is None:
        try:
            pid = find_process_by_name(TARGET_APP_NAME)
            
            if pid is None:
                print(f"Application '{TARGET_APP_NAME}' not found!")
                #exit(1)
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")

    print(f"Monitoring application with PID: {pid}")

    # Monitor the network traffic in the background
    try:
        while True:
            monitor_connections(pid)  # Monitor specific application's connections
            time.sleep(3)  # Sleep for a few seconds between checks
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
