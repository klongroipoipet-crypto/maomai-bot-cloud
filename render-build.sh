#!/usr/bin/env bash
# ล้างตัวตัดบรรทัด Windows (\r) ออกจากไฟล์ requirements.txt ก่อนรัน
sed -i 's/\r//g' requirements.txt

# ติดตั้ง library
pip install -r requirements.txt
