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
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# --- CORE LOGIC ---
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

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.photo: return
    photo = await update.message.photo[-1].get_file()
    path = f"{photo.file_id}.jpg"
    await photo.download_to_drive(path)
    img = cv2.imread(path)
    if img is not None:
        processed = maomai_clean_sweep_v10(img)
        out_path = f"clean_{path}"
        cv2.imwrite(out_path, processed)
        await update.message.reply_photo(photo=open(out_path, 'rb'))
        if os.path.exists(path): os.remove(path)
        if os.path.exists(out_path): os.remove(out_path)

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.video: return
    await update.message.reply_text("วิดีโอกำลังเข้าคิวประมวลผล... (อาจใช้เวลาสักครู่)")
    video = await update.message.video.get_file()
    path = f"{video.file_id}.mp4"
    await video.download_to_drive(path)
    await task_queue.put((path, update.message.chat_id))

async def video_worker():
    while True:
        # แก้ไขจุดที่ทำให้เกิด SyntaxError ใน Render
        data = await task_queue.get()
        path, chat_id = data
        
        cap = cv2.VideoCapture(path)
        out_path = f"clean_{path}"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        out = cv2.VideoWriter(out_path, fourcc, fps, (width, height))
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            out.write(maomai_clean_sweep_v10(frame))
        
        cap.release()
        out.release()
        # หมายเหตุ: การส่งวิดีโอกลับบน Render ตัวฟรีอาจจะช้าหรือติดปัญหา Timeout ได้
        print(f"Finished processing video: {path}")
        task_queue.task_done()
        if os.path.exists(path): os.remove(path)

async def post_init(application: Application):
    asyncio.create_task(video_worker())

def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("บอทเมามายบน Cloud พร้อมลุย 24 ชม.!")))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    print("--- Maomai Bot: Cloud Ready (V.11 Stable) ---")
    app.run_polling()

if __name__ == "__main__":
    main()
