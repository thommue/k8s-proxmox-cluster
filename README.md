
# 🚀 Kubernetes Cluster Setup with Proxmox Integration (Python)

Welcome to k8s-proxmox-cluster, a streamlined solution for setting up Kubernetes clusters – whether simple or complex – with ease. 
This package automates the deployment process, starting from cloning virtual machines on a Proxmox server to bootstrapping 
a fully functional Kubernetes cluster.
It's your go-to tool for quickly spinning up clusters for testing, development, or production environments.
Whether you're a DevOps enthusiast or a systems engineer, this package handles the heavy lifting, so you can focus on
what matters most: building and scaling your infrastructure.



## ✨ What does this package do?

---

With this package, you can automate the entire process of setting up Kubernetes clusters. It leverages Proxmox Virtual
Environment as the virtualization platform and requires an Ubuntu 24.04 template to clone virtual machines.

Here’s what happens step by step:

- Clone Virtual Machines from your Proxmox server.
- Automatically install and configure all necessary components.
- Bootstrap your cluster – ready to go, whether it's a simple or complex setup.



## 🎯 Prerequisites

---

Before using this package, ensure you have the following:

- A Proxmox server with a configured Ubuntu 24.04 VM template (If you do not have one, check out my [ProxmoxTemplates](https://github.com/thommue/ProxmoxTemplates) pkg, here you can creat one easily).
- A JSON configuration file containing Proxmox connection details (e.g., hostname, API token).
- A cluster setup configuration file:
- For simple setups: basic VM settings like name, CPU, and memory.
- For complex setups: additional details to tailor your Kubernetes environment.


## 🛠️ Simple vs. Complex Cluster Setups

---

With KubeCluster-Proxmox, you can choose between a simple or complex Kubernetes cluster setup depending on your needs.

Simple Cluster: A straightforward configuration with one master node and multiple worker nodes. 
- Example configuration: `vm-simple-conf-example.json`
Complex Cluster: A high-availability (HA) setup featuring multiple master nodes and two load balancers configured with 
HAProxy and Keepalived to ensure redundancy and failover. 
- Example configuration: `vm-complex-conf-example.json`
In both cases, a Proxmox connection configuration file (`proxmox-conf-example.json`) is required to interact with your 
- Proxmox environment. Simply fill out the provided example with your values.

## 📦 Installation

---

Install the package with pip:
```
pip install k8s-proxmox-cluster
```

## 🚀 Usage

---

for a simple setup:
```
simple-cluster-setup --proxmox-config <PATH_TO_YOUR_CONF_FILE> --vm-config <PATH_TO_YOUR_CONF_FILE>
```

for a complex setup:
```
complex-cluster-setup --proxmox-config <PATH_TO_YOUR_CONF_FILE> --vm-config <PATH_TO_YOUR_CONF_FILE>
```

## 🧹 Cleanup

---

If you need to delete the entire cluster, including all virtual machines, use the following command with the same 
configuration files:
```
cluster-cleanup --proxmox-config <PATH_TO_YOUR_CONF_FILE> --vm-config <PATH_TO_YOUR_CONF_FILE>
```