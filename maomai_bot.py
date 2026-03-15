import os
import cv2
import asyncio
import numpy as np
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# --- CONFIGURATION ---
TOKEN = "8715218073:AAGGYXhh4cMm-xzhG80ErgYl_K3njpX4KB4"
task_queue = asyncio.Queue()

# --- WEB SERVER FOR RENDER (KEEP ALIVE) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Maomai Bot is Living!")

def run_health_server():
    # Render จะส่ง Port มาให้ผ่าน Environment Variable
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# --- BOT LOGIC (V.10 เดิมที่คุณหมิงชอบ) ---
def maomai_clean_sweep_v10(image):
    h, w = image.shape[:2]
    wm_h, wm_w = int(h * 0.028), int(w * 0.14) 
    y1, x1 = h - wm_h - 4, w - wm_w - 2
    y2, x2 = h - 4, w - 2 
    sample_top = image[max(0, y1-5):y1, x1:x2]
    sample_left = image[y1:y2, max(0, x1-10):x1]
    avg_top = cv2.mean(sample_top)[:3]
    avg_left = cv2.mean(sample_left)[:3]
    base_color = [(a + b) / 2 for a, b in zip(avg_top, avg_left)]
    overlay_box = np.zeros((y2-y1, x2-x1, 3), dtype=np.uint8)
    for c in range(3): overlay_box[:, :, c] = int(base_color[c])
    mask = np.ones((y2-y1, x2-x1), dtype=np.uint8) * 255
    mask = cv2.GaussianBlur(mask, (25, 25), 0) / 255.0
    roi = image[y1:y2, x1:x2]
    for c in range(3):
        roi[:, :, c] = (roi[:, :, c] * (1 - mask) + overlay_box[:, :, c] * mask).astype(np.uint8)
    return image

# ... (ส่วน handle_photo, handle_video, video_worker เหมือนเดิม) ...
# (เพื่อความกระชับ ผมละไว้ แต่ในไฟล์จริงคุณหมิงใส่ให้ครบนะครับ)

async def post_init(application: Application):
    asyncio.create_task(video_worker())

def main():
    # รัน Web Server แยก Thread เพื่อกัน Render ตัดการทำงาน
    threading.Thread(target=run_health_server, daemon=True).start()
    
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("บอทเมามายบน Cloud พร้อม!")))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    print("--- Maomai Bot: Cloud Version Live ---")
    app.run_polling()

if __name__ == "__main__":
    main()