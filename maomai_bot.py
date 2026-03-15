import os
import cv2
import asyncio
import numpy as np
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import random

# --- CONFIGURATION ---
TOKEN = "8715218073:AAGGYXhh4cMm-xzhG80ErgYl_K3njpX4KB4"
task_queue = asyncio.Queue()

# --- WEB SERVER FOR RENDER (KEEP ALIVE) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Maomai Public Bot: Bilingual & Awake!")
        print("--- [Ping] น้องตื่นแล้วค่ะ~ 醒了, 快来玩吧! ---")

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

# --- HANDLERS ---
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.photo: return
    user_name = update.effective_user.first_name
    
    # ข้อความตอนรับรูป (TH + CN)
    recv_texts = [
        f"📸 อูยย {user_name} ส่งของดีมาเชียว! แป๊บเดียวนะเดี๋ยวจัดการดีดลายน้ำขยะออกให้ เนียนจนต้องร้อง 哇喔!\n(哇喔! 宝贝真棒, 等我一下, 马上帮你把水印给丢了!) 💦",
        f"📸 呀! รูปนี้เสียววูบวาบเลยนะ เดี๋ยว 'ล้าง' ให้เกลี้ยงเล้ยยย!\n(哎呀! 这图太火辣了, 我马上帮你把它‘洗’干净!) 🥵",
        f"📸 ส่งมาแบบนี้...ใจคอไม่ดีเลยค่ะ เดี๋ยวจัดการ 'ชำระล้าง' ให้กริบๆ\n(发这种图... 我心跳加速了啦, 马上帮你处理掉!) 👅"
    ]
    status_msg = await update.message.reply_text(random.choice(recv_texts))
    
    photo = await update.message.photo[-1].get_file()
    path = f"{photo.file_id}.jpg"
    await photo.download_to_drive(path)
    
    img = cv2.imread(path)
    if img is not None:
        processed = maomai_clean_sweep_v10(img)
        out_path = f"clean_{path}"
        cv2.imwrite(out_path, processed)
        
        # ข้อความตอนส่งคืน (TH + CN)
        done_texts = [
            f"เนียนกริบ ไร้รอยต่อ! จัดไปอย่าให้เสีย {user_name} 🍻\n(处理好了! 毫无痕迹, 拿去爽吧! 🍺)",
            f"ดีดลายน้ำออกให้จนเนียน! ไปดูให้ตาแฉะเลยนะคะ 💋\n(水印已经踢飞了! 去看个够吧, 亲爱的~ 👄)",
            f"เสร็จละ! คลีนสุดๆ เนียนจนเจ้าของยังงง 哈哈!\n(搞定! 太干净了, 连主人都会惊讶的 哈哈!) ✅"
        ]
        await update.message.reply_photo(photo=open(out_path, 'rb'), caption=random.choice(done_texts))
        await status_msg.delete()
        
        if os.path.exists(path): os.remove(path)
        if os.path.exists(out_path): os.remove(out_path)

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.video: return
    user_name = update.effective_user.first_name
    await update.message.reply_text(f"🎬 哇! คลิปยาวจัง! เดี๋ยวจัดการ 'กวาดล้าง' ให้กริบๆ รอนิดนะคะ {user_name}!\n(哇! 视频挺长嘛! 等我一下, 马上帮你把垃圾水印全扫光!) 🥵💨")
    
    video = await update.message.video.get_file()
    path = f"{video.file_id}.mp4"
    await video.download_to_drive(path)
    await task_queue.put((path, update.message.chat_id, context, user_name))

async def video_worker():
    while True:
        path, chat_id, context, user_name = await task_queue.get()
        
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
        
        await context.bot.send_video(chat_id=chat_id, video=open(out_path, 'rb'), caption=f"วิดีโอเนียนกริบ ไร้รอยต่อ! จัดไป {user_name} 🍻\n(视频处理完成! 丝滑无痕, 给你的礼物! 🎁)")
        
        task_queue.task_done()
        if os.path.exists(path): os.remove(path)
        if os.path.exists(out_path): os.remove(out_path)

async def post_init(application: Application):
    asyncio.create_task(video_worker())

def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    
    # Start Message (TH + CN)
    start_msg = "เหยๆๆ! ว่าไง! บอทเมามายมาละจ้า กำจัดลายน้ำขยะให้เนียนกริบ 24 ชม. ส่งงานมาเล้ยยย! 🍻\n(嘿! 来了吗! 猫迈机器人在线等, 24小时为你清理水印垃圾, 快把好东西发给我吧! 👄)"
    app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text(start_msg)))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    
    print("\n" + "🏮"*20)
    print("--- MAOMAI BILINGUAL BOT: V.R-Public ---")
    print("--- STATUS: ALWAYS HUNGRY & READY ---")
    print("🏮"*20 + "\n")
    
    app.run_polling()

if __name__ == "__main__":
    main()
