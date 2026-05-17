# 1. Install Tools & Dependencies

```bash
sudo apt update && sudo apt install open-vm-tools open-vm-tools-desktop

sudo apt update && sudo apt upgrade -y && sudo apt install -y build-essential git cmake pkg-config libpcre3-dev libxml2 libxml2-dev libyajl-dev liblmdb-dev libtool automake autoconf make gcc g++ python3 python3-venv python3-pip wget unzip
```

# 2. Clone modsec-learn

```bash
cd ~ 
git clone https://github.com/pralab/modsec-learn.git 
cd modsec-learn && ls -la
```

# 3. Install & Build ModSecurity (Core Engine)

```bash
# Clone source code
cd ~
git clone --branch v3.0.10 https://github.com/SpiderLabs/ModSecurity
cd ModSecurity

# Khởi tạo submodule
git submodule init
git submodule update

# Build và cài đặt
./build.sh
./configure
make -j$(nproc)
sudo make install
```

# 4. Config Shared Library & Update Linker Path

```bash
# Liên kết thư viện động
sudo sh -c 'echo "/usr/local/modsecurity/lib" > /etc/ld.so.conf.d/modsecurity.conf'
sudo ldconfig
ldconfig -p | grep modsecurity

> Nếu thành công
nhatnguyen@openstack-aio:~/ModSecurity$ sudo sh -c 'echo "/usr/local/modsecurity/lib" > /etc/ld.so.conf.d/modsecurity.conf'
nhatnguyen@openstack-aio:~/ModSecurity$ sudo ldconfig
nhatnguyen@openstack-aio:~/ModSecurity$ ldconfig -p | grep modsecurity
	libmodsecurity.so.3 (libc6,x86-64) => /usr/local/modsecurity/lib/libmodsecurity.so.3
	libmodsecurity.so (libc6,x86-64) => /usr/local/modsecurity/lib/libmodsecurity.so

# Thiết đặt biến môi trường để Python  
export MODSECURITY_INC=/usr/local/modsecurity/include
export MODSECURITY_LIB=/usr/local/modsecurity/lib

# Lưu vĩnh viễn vào ~/.bashrc
echo 'export MODSECURITY_INC=/usr/local/modsecurity/include' >> ~/.bashrc
echo 'export MODSECURITY_LIB=/usr/local/modsecurity/lib' >> ~/.bashrc
```

# 5. Install Python Bindings (PyModSecurity) with Virtualenv

```bash
# Xoá thư mục cũ (nếu có) và clone pymodsecurity
cd ~ 
rm -rf pymodsecurity 
git clone --recurse-submodules https://github.com/AvalZ/pymodsecurity.git 
cd pymodsecurity

# Tạo môi trường ảo Python riêng biệt cho AI model
python3 -m venv ~/modsec-ai-venv 

# Kích hoạt môi trường và cập nhật pip, pybind11
source ~/modsec-ai-venv/bin/activate 
pip install --upgrade pip setuptools wheel 
pip install --upgrade pybind11

# Build và cài đặt thư viện vào trong môi trường ảo
python3 setup.py build 
python3 setup.py install

# Kiểm tra kết quả cài đặt
python3 -c "try:
    import ModSecurity
    print('Imported ModSecurity OK')
except Exception as e:
    print('Import ModSecurity failed:', e)"
```

# 6. OWASP Core Rule Set (CRS)

> CRS = OWASP Core Rule Set, phiên bản mà bài báo dùng là v4.0.0.

```bash
cd ~
git clone --branch v4.0.0 https://github.com/coreruleset/coreruleset.git
```

# 7. Instal Python Dependencies & Run the scripts

> Nhớ mở terminal mới

```bash
# Mở môi trường ảo (nếu bạn đã đóng terminal trước đó)
source ~/modsec-ai-venv/bin/activate

# Vào thư mục dự án và cài thư viện requirements
cd ~/modsec-learn
# Nếu dùng Python 3.12, pandas 1.3.5 quá cũ và sẽ bị build lỗi.
# Cập nhật pandas trong requirements.txt lên bản có wheel cho Python 3.12.
sed -i 's/^pandas==1\.3\.5$/pandas==2.2.3/' requirements.txt
pip install -r requirements.txt

# Cài đặt lại module pymodsecurity từ thư mục mã nguồn 
cd ~/pymodsecurity 
pip install .

# Đưa bộ dữ liệu OWASP CRS vào trong thư mục modsec-learn để model đọc
mv ~/coreruleset ~/modsec-learn/

# Chạy tệp training mô hình AI
cd ~/modsec-learn
# Nếu gặp lỗi LinearSVC với penalty='l1' và dual=True trên scikit-learn mới, sửa scripts/run_training.py: thêm `dual = False` vào LinearSVC(...).
# Việc sửa dual=False chỉ làm cấu hình LinearSVC hợp lệ với scikit-learn mới; output prediction trên test set vẫn giống model gốc.
python3 scripts/run_training.py

# Kiểm tra
ls -l ~/modsec-learn/data/models

```

# 8. Link with Openstack venv (Optional)

Nếu mô hình SIEM/WAF này được chạy trên nền tảng máy ảo OpenStack, trước khi kích hoạt ảo hoá AI, bạn cần chạy source môi trường của Kolla (Ansible) để nạp các kết nối admin OpenStack:

```bash
source ~/kolla-venv/bin/activate
cd /etc/kolla/ansible/inventory/
source /etc/kolla/admin-openrc.sh

source ~/modsec-ai-venv/bin/activate
# và chạy các script python của modsec-learn...
```
