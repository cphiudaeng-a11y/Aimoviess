# AI Film Studio EP.2 — Render Dry-Run

เว็บเวอร์ชันนี้ใช้สำหรับ **อัปโหลด JSON / ตรวจสอบ 20 ฉาก / ประเมินราคาเท่านั้น** ไม่มีการสร้างวิดีโอจริง ไม่มีการเรียก API ที่เสียเงิน และไม่มีการส่ง Google Drive โดยอัตโนมัติ

## ติดตั้งผ่าน Android
1. แตก ZIP แล้วอัปโหลดไฟล์ทั้งหมดในโฟลเดอร์นี้ขึ้น GitHub repository ส่วนตัว (private) ผ่าน github.com; ให้ `render.yaml` และ `Dockerfile` อยู่ที่ root ของ repository
2. เข้า https://dashboard.render.com/ และเข้าสู่ระบบ เลือก **New → Blueprint** เชื่อม GitHub repository และเลือก repository นี้
3. ตรวจสอบบริการ `ai-film-studio-ep2-preview` และการตั้งค่า `ENABLE_PAID_GENERATION=false` แล้วอนุมัติ deploy เฉพาะบริการเว็บตามแผน Render ที่แสดง
4. รอ Build/Deploy สำเร็จ แล้วเปิด URL `https://...onrender.com` ที่ Render จัดให้บน Chrome Android
5. กด **โหลด EP.2 ตัวอย่าง** หรืออัปโหลด `data/ep2.json` แล้วกด **ตรวจสอบ 20 ฉากและประเมินราคา**

**คำเตือน:** Render อาจคิดค่าบริการโฮสต์ตามแผนและการใช้งาน แม้ไม่เรียก xAI API; ตรวจสอบค่าใช้จ่ายที่หน้า Render ก่อนกด deploy

## API key และ Google Drive (ขั้นเตรียมระบบ)
- ยังไม่ต้องเพิ่ม `XAI_API_KEY` ใน Render เพราะ Dry Run ไม่ใช้คีย์
- ภายหลังใช้ Render → Service → Environment → Add Environment Variable → `XAI_API_KEY` โดยไม่ใส่คีย์ใน GitHub หรือแชต
- ห้ามใช้ access token Google Drive ที่มีอายุสั้นเป็นระบบเชื่อมต่อระยะยาว ต้องใช้ Google OAuth 2.0 แบบ consent + refresh token อย่างปลอดภัย และเลือกสิทธิ์ขั้นต่ำ
- งาน 20 ฉากใช้เวลานาน ควรแยก queue/worker และฐานข้อมูลสถานะงานจากเว็บ; Render instance และ storage ชั่วคราวอาจถูกรีสตาร์ต/ลบไฟล์ได้
- โค้ด `app.py` มีโครงร่างงานแบบ thread สำหรับทดสอบในเครื่อง แต่ **ไม่ใช่ระบบ production**; อย่าเปลี่ยน `ENABLE_PAID_GENERATION` เป็น `true` บน Render ก่อนทำระบบยืนยันตัวตน, persistent storage, retries, budgets และ OAuth ให้ครบ
- เสียงพูดไทยจากโมเดลวิดีโอไม่รับประกันความแม่นยำหรือลิปซิงก์ จึงต้องมีขั้น QA และอาจต้องใช้ TTS/voice pipeline แยก

## ตรวจสอบ API โดยไม่เสียเครดิต
อ่านเอกสาร https://docs.x.ai/developers/model-capabilities/video/generation และ https://docs.x.ai/developers/rest-api-reference/inference/videos
API สำหรับส่งงาน `POST /v1/videos/generations` และเช็กผล `GET /v1/videos/{request_id}` แต่เว็บ Dry Run นี้ **ไม่ได้เรียก endpoints เหล่านั้น**

## ทดลองในเครื่อง
`pip install -r requirements.txt`
`uvicorn app:app --reload`
เปิด http://localhost:8000
