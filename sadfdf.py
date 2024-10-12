test_list = [
"kubeadm join 192.168.150.50:6443 --token kkhuws.dy780mogygdvyqdr \\\n",
    "\t--discovery-token-ca-cert-hash sha256:05f7a1f3f48e772bce8bf47d4df9e17d161468173dde85f22dd32b1a6042866c \n"
]

print(f"{test_list[0]}{test_list[1]}")

test_cmd = f"{test_list[0].split("\\")[0]}{test_list[1].replace("\t", "").replace('\n', '')}"

print(test_cmd)
