# test_list = [
# "kubeadm join 192.168.150.50:6443 --token kkhuws.dy780mogygdvyqdr \\\n",
#     "\t--discovery-token-ca-cert-hash sha256:05f7a1f3f48e772bce8bf47d4df9e17d161468173dde85f22dd32b1a6042866c \n"
# ]
#
# print(f"{test_list[0]}{test_list[1]}")
#
# test_cmd = f"{test_list[0].split("\\")[0]}{test_list[1].replace("\t", "").replace('\n', '')}"
#
# print(test_cmd)
#
# test_list = ["192.168.150.51", "192.168.150.50", "192.168.150.54", "192.168.150.53", "192.168.150.52"]
#
# print(sorted(test_list))

with open("test.txt", "r") as f:
    # content = f.read()
    lines = f.readlines()

# print(content)


print()
print(lines)
print(lines[-8].split('\\')[0].strip())
print(lines[-7].split('\\')[0].strip())
print(lines[-6].strip())
print()
print(lines[-2].split('\\')[0])
print(lines[-1].strip())


together_master = f"sudo {lines[-8].split('\\')[0].strip()} {lines[-7].split('\\')[0].strip()} {lines[-6].strip()}"
together_worker = f"sudo {lines[-2].split('\\')[0].strip()} {lines[-1].strip()}"

print(together_master)
print(together_worker)

start_index = next((i for i, line in enumerate(lines) if "kubeadm" in line), None)
print(start_index)


together_master = f"sudo {lines[start_index].split('\\')[0].strip()} {lines[start_index + 1].split('\\')[0].strip()} {lines[start_index + 2].strip()}"
together_worker = f"sudo {lines[start_index + 6].split('\\')[0].strip()} {lines[start_index + 7].strip()}"

print(together_master)
print(together_worker)


