
<!-- #install tools -->
sudo apt update && sudo apt install open-vm-tools open-vm-tools-desktop


sudo apt update && sudo apt upgrade -y && sudo apt install -y build-essential git cmake pkg-config libpcre3-dev libxml2 libxml2-dev libyajl-dev liblmdb-dev libtool automake autoconf make gcc g++ python3 python3-venv python3-pip wget unzip

cd ~ && git clone https://github.com/pralab/modsec-learn.git && cd modsec-learn && ls -la

cd $HOME && git clone --branch v3.0.10 https://github.com/SpiderLabs/ModSecurity && cd ModSecurity && git submodule init && git submodule update

cd ~/ModSecurity && ./build.sh && ./configure && make -j$(nproc) && sudo make install

sudo sh -c 'echo "/usr/local/modsecurity/lib" > /etc/ld.so.conf.d/modsecurity.conf'
sudo ldconfig
ldconfig -p | grep modsecurity


<!-- #phải trả về -->
<!-- kali@kali-virtual-machine:~/ModSecurity$ ldconfig -p | grep modsecurity libmodsecurity.so.3 (libc6,x86-64) => /usr/local/modsecurity/lib/libmodsecurity.so.3 libmodsecurity.so (libc6,x86-64) => /usr/local/modsecurity/lib/libmodsecurity.so kali@kali-virtual-machine:~/ModSecurity$ -->


<!-- Thiết đặt biến môi trường để Python  -->
export MODSECURITY_INC=/usr/local/modsecurity/include && export MODSECURITY_LIB=/usr/local/modsecurity/lib
echo 'export MODSECURITY_INC=/usr/local/modsecurity/include' >> ~/.bashrc && echo 'export MODSECURITY_LIB=/usr/local/modsecurity/lib' >> ~/.bashrc



<!-- Clone fork pymodsecurity & install -->
cd ~ && rm -rf pymodsecurity && git clone --recurse-submodules https://github.com/AvalZ/pymodsecurity.git && cd pymodsecurity
python3 -m venv ~/modsec-ai-venv && source ~/modsec-ai-venv/bin/activate && pip install --upgrade pip setuptools wheel && pip install --upgrade pybind11
export MODSECURITY_INC=/usr/local/modsecurity/include && export MODSECURITY_LIB=/usr/local/modsecurity/lib && python3 setup.py build && python3 setup.py install
python3 -c "try:
    import ModSecurity
    print('Imported ModSecurity OK')
except Exception as e:
    print('Import ModSecurity failed:', e)"

<!-- #neu kiem tra ok thi pymodsec cai duoc r -->
python3 - <<EOF
from ModSecurity import ModSecurity, Rules, Transaction
print("Bindings working, ModSecurity version:", ModSecurity().whoAmI())
EOF


<!-- Clone bộ luật CRS**

CRS = OWASP Core Rule Set, phiên bản mà bài báo dùng là v4.0.0.  -->
cd ~
git clone --branch v4.0.0 https://github.com/coreruleset/coreruleset.git


<!-- nhớ mở terminal mới -->

cd ~/Downloads/Project/modsec-learn && source ~/modsec-ai-venv/bin/activate && pip install --upgrade pip setuptools wheel && pip install -r requirements.txt
cd ~/pymodsecurity && pip install .
mv ~/coreruleset ~/Downloads/Project/modsec-learn/
cd ~/Downloads/Project/modsec-learn/scripts && python3 scripts/run_training.py


