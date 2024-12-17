import paramiko
import threading
from typing import Optional, Any


class SSHConnectionPool:
    """SSH Connection Pool Manager, where the connections are managed, to avoid server issues"""

    def __init__(self) -> None:
        self.connections: dict[str, paramiko.SSHClient] = (
            {}
        )  # Dictionary to hold connections by (host, port, username) tuple
        self.lock = threading.Lock()

    @staticmethod
    def create_connection(
        ip_address: str, user: Optional[str], ssh_key: Optional[str]
    ) -> paramiko.SSHClient:
        """Creates a new SSH connection using Paramiko."""
        # set up the client
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        private_key = paramiko.RSAKey.from_private_key_file(ssh_key)  # type: ignore
        client.connect(ip_address, 22, user, pkey=private_key)
        return client

    def get_connection(
        self, ip_address: str, user: Optional[str] = None, ssh_key: Optional[str] = None
    ) -> paramiko.SSHClient:
        """Gets an existing connection or creates a new one if not available."""
        with self.lock:
            if ip_address not in self.connections:
                if not user and not ssh_key:
                    raise Exception(
                        "SSH connection failed! USER and SSH KEY are required!"
                    )
                self.connections[ip_address] = self.create_connection(
                    ip_address, user, ssh_key
                )
            return self.connections[ip_address]

    def close_connections(self, ip_addresses: list[str]) -> None:
        """Closes a specific connections and remove them from the pool."""
        with self.lock:
            for ip_address in ip_addresses:
                if ip_address in self.connections:
                    self.connections[ip_address].close()
                    del self.connections[ip_address]

    def close_all_connections(self) -> None:
        """Closes all connections in the pool."""
        with self.lock:
            for client in self.connections.values():
                client.close()
            self.connections.clear()
