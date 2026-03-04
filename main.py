from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
import database, auth
import os
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

def send_email(target_email, code):
    # Har safar yangilash (agar .env o'zgarsa)
    load_dotenv()
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not smtp_email or "your_email" in smtp_email:
        print("ERROR SMTP Xatolik: .env faylida email sozlanmagan!")
        return False
        
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = f"1XPANEL <{smtp_email}>"
        msg['To'] = target_email
        msg['Subject'] = f"Tasdiqlash kodi: {code}"
        
        # Premium HTML Template
        html = f"""
        <html>
        <head>
            <style>
                .container {{ font-family: 'Segoe UI', sans-serif; max-width: 600px; margin: auto; border: 1px solid #e2e8f0; border-radius: 16px; overflow: hidden; }}
                .header {{ background: #3b82f6; padding: 40px; text-align: center; color: white; }}
                .content {{ padding: 40px; text-align: center; color: #1e293b; }}
                .code {{ font-size: 36px; font-weight: 800; color: #3b82f6; letter-spacing: 8px; margin: 30px 0; padding: 20px; background: #f8fafc; border-radius: 12px; }}
                .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #94a3b8; background: #f1f5f9; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin:0;">1XPANEL</h1>
                </div>
                <div class="content">
                    <h2 style="margin:0;">Tasdiqlash kodi</h2>
                    <p>Ro'yxatdan o'tishni yakunlash uchun quyidagi koddan foydalaning:</p>
                    <div class="code">{code}</div>
                    <p style="font-size: 14px;">Kod 10 daqiqa davomida amal qiladi. Uni hech kimga bermang.</p>
                </div>
                <div class="footer">
                    &copy; 2026 1XPANEL. Barcha huquqlar himoyalangan.
                </div>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html, 'html'))
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(smtp_email, smtp_password)
        server.sendmail(smtp_email, target_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"ERROR SMTP Xatolik: {e}")
        return False

app = FastAPI()

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

database.init_db()

import os
if not os.path.exists("uploads"):
    os.makedirs("uploads")

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Dependency to get DB session
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

from pydantic import BaseModel

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

# Temporary store for verification codes
import random
verification_codes = {} # {email: "1234"}

class SendCodeRequest(BaseModel):
    email: str

@app.post("/register/send-code")
async def send_verif_code(req: SendCodeRequest, db: Session = Depends(get_db)):
    email = req.email.strip().lower()
    
    # Check if email is already registered
    existing_user = db.query(database.User).filter(database.User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Ushbu email allaqachon ro'yxatdan o'tgan")

    code = f"{random.randint(1000, 9999)}"
    verification_codes[email] = code
    
    # Send actual email
    success = send_email(email, code)
    
    # Log session info
    print(f"DEBUG: Verification code {code} generated for {email}. Email sent: {success}")
    
    if success:
        return {"message": "Kod yuborildi. Gmail pochtangizni tekshiring."}
    else:
        # For development, if email fails, we still allow seeing the code in terminal
        return {"message": "Kod yuborildi (Terminalni tekshiring).", "debug_code": code}

class VerifyCodeRequest(BaseModel):
    username: str
    email: str
    password: str
    code: str

@app.post("/register/verify-code")
async def verify_and_register(req: VerifyCodeRequest, db: Session = Depends(get_db)):
    email = req.email.strip().lower()
    code = req.code.strip()
    username = req.username.strip()
    
    print(f"DEBUG: Processing verification for {email} with code {code}")
    
    if email not in verification_codes:
        print(f"ERROR: {email} uchun kod topilmadi. Mavjud: {list(verification_codes.keys())}")
        raise HTTPException(status_code=400, detail="Tasdiqlash kodi muddati o'tgan yoki so'rov yuborilmagan")

    if verification_codes[email] != code:
        print(f"ERROR: Kod mos kelmadi. Kutilgan: {verification_codes[email]}, Kelgan: {code}")
        raise HTTPException(status_code=400, detail="Tasdiqlash kodi noto'g'ri")
    
    # Check if username exists
    existing_user = db.query(database.User).filter(database.User.username == req.username).first()
    if existing_user:
        print(f"ERROR Xatolik: Username '{req.username}' band")
        raise HTTPException(status_code=400, detail="Foydalanuvchi nomi band")

    # Check if email exists
    existing_email = db.query(database.User).filter(database.User.email == req.email).first()
    if existing_email:
        print(f"ERROR Xatolik: Email '{req.email}' band")
        raise HTTPException(status_code=400, detail="Ushbu Email allaqachon ro'yxatdan o'tgan")
    
    try:
        from sqlalchemy import func
        hashed_password = auth.get_password_hash(req.password)
        
        # Determine next ID
        max_id = db.query(func.max(database.User.id)).scalar()
        next_id = 10001 if (max_id is None or max_id < 10000) else max_id + 1
        
        new_user = database.User(
            id=next_id,
            username=req.username, 
            email=req.email, 
            hashed_password=hashed_password
        )
        db.add(new_user)
        db.commit()
    except Exception as e:
        error_msg = str(e)
        print(f"ERROR: Database error: {error_msg}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ma'lumotlar bazasiga yozishda xatolik: {error_msg}")
    
    # Remove code after use
    verification_codes.pop(req.email)
    print(f"DONE: User {req.username} muvaffaqiyatli ro'yxatdan o'tdi")
    
    return {"message": "Ro'yxatdan muvaffaqiyatli o'tdingiz"}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(database.User).filter(database.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Foydalanuvchi nomi yoki parol noto'g'ri",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/admin/users")
def get_users(db: Session = Depends(get_db)):
    # In a real app, this should be protected by an admin check
    users = db.query(database.User).all()
    return [{"id": u.id, "username": u.username, "email": u.email, "balance": u.balance} for u in users]

@app.get("/orders")
def get_orders(db: Session = Depends(get_db)):
    # Temporary to simulate old app functionality
    orders = db.query(database.Order).all()
    return orders

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    username = auth.decode_access_token(token)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kirish ma'lumotlarini tasdiqlab bo'lmadi",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(database.User).filter(database.User.username == username).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    return user

@app.get("/me")
def get_me(current_user: database.User = Depends(get_current_user)):
    return {
        "id": current_user.id, 
        "username": current_user.username, 
        "balance": current_user.balance,
        "api_key": current_user.api_key
    }

@app.post("/users/me/api-key")
def regenerate_api_key(current_user: database.User = Depends(get_current_user), db: Session = Depends(get_db)):
    import uuid
    new_key = uuid.uuid4().hex + uuid.uuid4().hex # Long secure key
    current_user.api_key = new_key
    db.commit()
    return {"api_key": new_key}

async def sync_active_orders(orders: List[database.Order], db: Session):
    api_settings = db.query(database.APISettings).first()
    if not api_settings or not api_settings.api_url or not api_settings.api_key:
        return

    import time
    # Only sync orders that are not in final state and have external_id
    active_statuses = ["Pending", "Processing", "In progress", "Pending", "In_progress"]
    to_sync = [o for o in orders if o.status in active_statuses and o.external_id]
    
    if not to_sync:
        return

    async with httpx.AsyncClient() as client:
        for order in to_sync:
            try:
                payload = {
                    "key": api_settings.api_key,
                    "action": "status",
                    "order": order.external_id
                }
                resp = await client.post(api_settings.api_url, data=payload, timeout=5.0)
                if resp.status_code == 200:
                    data = resp.json()
                    if "status" in data:
                        order.status = data.get("status", order.status)
                        order.remains = int(data.get("remains", order.remains or 0))
                        order.start_count = int(data.get("start_count", order.start_count or 0))
                db.commit()
            except Exception as e:
                print(f"Sync error for order {order.id}: {e}")

@app.get("/users/me/orders")
async def get_my_orders(current_user: database.User = Depends(get_current_user), db: Session = Depends(get_db)):
    orders = db.query(database.Order).filter(database.Order.user_id == current_user.id).order_by(database.Order.id.desc()).all()
    # Trigger sync for active orders
    await sync_active_orders(orders, db)
    return orders

# Admin Balance Management
class BalanceUpdate(BaseModel):
    amount: float

class UserUpdate(BaseModel):
    username: str
    email: str

@app.post("/admin/users/{user_id}/balance")
def update_balance(user_id: int, update: BalanceUpdate, db: Session = Depends(get_db)):
    user = db.query(database.User).filter(database.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.balance += update.amount
    db.commit()
    return {"message": "Balance updated", "new_balance": user.balance}

@app.put("/admin/users/{user_id}")
def update_user(user_id: int, u: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(database.User).filter(database.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if username is already taken by another user
    existing = db.query(database.User).filter(database.User.username == u.username, database.User.id != user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    user.username = u.username
    user.email = u.email
    db.commit()
    return {"message": "User updated"}

@app.delete("/admin/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(database.User).filter(database.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    
    try:
        # Delete associated orders
        db.query(database.Order).filter(database.Order.user_id == user_id).delete()
        
        # Delete associated payment requests
        db.query(database.PaymentRequest).filter(database.PaymentRequest.user_id == user_id).delete()
        
        # Now delete the user
        db.delete(user)
        db.commit()
        return {"message": "Foydalanuvchi va unga tegishli barcha ma'lumotlar o'chirib tashlandi"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"O'chirishda xatolik: {str(e)}")

# Admin Order Management
class OrderUpdate(BaseModel):
    service: str
    qty: int
    price: float
    status: str

@app.put("/admin/orders/{order_id}")
def update_order(order_id: int, u: OrderUpdate, db: Session = Depends(get_db)):
    order = db.query(database.Order).filter(database.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
    order.service = u.service
    order.qty = u.qty
    order.price = u.price
    order.status = u.status
    db.commit()
    return {"message": "Buyurtma yangilandi"}

@app.patch("/admin/orders/{order_id}")
def update_order_status(order_id: int, status: str, db: Session = Depends(get_db)):
    order = db.query(database.Order).filter(database.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
    order.status = status
    db.commit()
    return {"message": "Buyurtma yangilandi"}

@app.delete("/admin/orders/{order_id}")
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(database.Order).filter(database.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
    db.delete(order)
    db.commit()
    return {"message": "Buyurtma o'chirildi"}

@app.get("/admin/orders")
async def get_admin_orders(db: Session = Depends(get_db)):
    # Fetch all orders with user info
    orders_data = db.query(database.Order, database.User).join(database.User, database.Order.user_id == database.User.id).all()
    
    # Extract orders for syncing
    orders_list = [o for o, u in orders_data]
    await sync_active_orders(orders_list, db)
    
    result = []
    for order, user in orders_data:
        result.append({
            "id": order.id,
            "username": user.username,
            "service": order.service,
            "qty": order.qty,
            "price": order.price,
            "status": order.status,
            "external_id": order.external_id,
            "remains": order.remains,
            "start_count": order.start_count
        })
    return result[::-1] # Reverse to show newest first

from typing import List, Optional

# Service Management
class ServiceCreate(BaseModel):
    id: Optional[int] = None
    name: str
    category: str
    price_per_1k: float
    external_service_id: str
    min_qty: int = 100
    max_qty: int = 10000
    description: Optional[str] = "Premium xizmat turi"
    average_time: Optional[str] = "1-24 soat"

@app.get("/services")
def get_services(db: Session = Depends(get_db)):
    return db.query(database.Service).all()

@app.post("/admin/services")
def save_service(s: ServiceCreate, db: Session = Depends(get_db)):
    service = None
    if s.id:
        service = db.query(database.Service).filter(database.Service.id == s.id).first()
    
    if not service:
        # Fallback to external_id lookup or create new
        service = db.query(database.Service).filter(database.Service.external_service_id == s.external_service_id).first()
    
    if not service:
        service = database.Service()
        db.add(service)
    service.name = s.name
    service.category = s.category
    service.price_per_1k = s.price_per_1k
    service.external_service_id = s.external_service_id
    service.min_qty = s.min_qty
    service.max_qty = s.max_qty
    service.description = s.description
    service.average_time = s.average_time
    db.commit()
    return {"message": "Xizmat saqlandi"}

@app.delete("/admin/services/{service_id}")
def delete_service(service_id: int, db: Session = Depends(get_db)):
    service = db.query(database.Service).filter(database.Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Xizmat topilmadi")
    db.delete(service)
    db.commit()
    return {"message": "Xizmat o'chirildi"}

import httpx

class OrderCreate(BaseModel):
    service_id: str # This is now the external_service_id or our internal ID? Let's use external_service_id for simplicity as the link
    link: str
    quantity: int

@app.post("/orders")
async def create_order(o: OrderCreate, current_user: database.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 1. Fetch Service from DB
    # We first try to treat o.service_id as our internal DB ID (integer)
    # If that fails or not found, we fallback to external_service_id lookup
    service = None
    try:
        internal_id = int(o.service_id)
        service = db.query(database.Service).filter(database.Service.id == internal_id).first()
    except (ValueError, TypeError):
        pass
    
    if not service:
        service = db.query(database.Service).filter(database.Service.external_service_id == o.service_id).first()
    
    if not service:
        raise HTTPException(status_code=404, detail="Xizmat topilmadi")

    # 2. Calculate Price
    total_price = (o.quantity / 1000) * service.price_per_1k

    # 3. Check balance
    if current_user.balance < total_price:
        raise HTTPException(status_code=400, detail="Mablug'ingiz yetarli emas")

    # 4. Save local order
    new_order = database.Order(
        user_id=current_user.id,
        service=service.name,
        qty=o.quantity,
        price=total_price,
        status="Processing",
        external_service_id=service.external_service_id
    )
    current_user.balance -= total_price
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # 5. Forward to External API (Admin-connected API)
    api_settings = db.query(database.APISettings).first()
    if api_settings and api_settings.api_key and api_settings.api_url:
        print(f"DEBUG: Forwarding order #{new_order.id} to {api_settings.api_url} using ext_id {service.external_service_id}")
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "key": api_settings.api_key,
                    "action": "add",
                    "service": service.external_service_id,
                    "link": o.link,
                    "quantity": o.quantity
                }
                # Standard SMM Panel APIs expect form-data
                resp = await client.post(api_settings.api_url, data=payload, timeout=15.0)
                
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"DEBUG: External API Response: {data}")
                    if "order" in data:
                        new_order.external_id = str(data["order"])
                        db.commit()
                    elif "error" in data:
                        print(f"WARNING: External API returned error: {data['error']}")
                else:
                    print(f"ERROR: External API returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"API Forward error for order #{new_order.id}: {e}")

    return {
        "message": "Buyurtma qabul qilindi",
        "order_id": new_order.id,
        "balance": current_user.balance,
        "service_name": service.name,
        "price": total_price,
        "link": o.link,
        "external_id": new_order.external_id
    }

# Admin API Settings
class APIConfig(BaseModel):
    provider_name: str
    api_url: str
    api_key: str

@app.get("/admin/api-settings")
def get_api_settings(db: Session = Depends(get_db)):
    settings = db.query(database.APISettings).first()
    if not settings:
        return {"provider_name": "", "api_url": "", "api_key": ""}
    return settings

@app.post("/admin/api-settings")
def save_api_settings(c: APIConfig, db: Session = Depends(get_db)):
    settings = db.query(database.APISettings).first()
    if not settings:
        settings = database.APISettings()
        db.add(settings)
    settings.provider_name = c.provider_name
    settings.api_url = c.api_url
    settings.api_key = c.api_key
    db.commit()
    return {"message": "Sozlamalar saqlandi"}

# === PAYMENT MANAGEMENT ===
class PaymentRequestCreate(BaseModel):
    amount: float
    method: str

class PaymentSettingsUpdate(BaseModel):
    card_number: Optional[str] = None
    merchant_id: Optional[str] = None
    title: Optional[str] = None
    instructions: Optional[str] = None

@app.post("/payments/request")
async def create_payment_request(
    amount: float = Form(...),
    method: str = Form(...),
    receipt: Optional[UploadFile] = File(None),
    current_user: database.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    from datetime import datetime
    import shutil
    
    receipt_path = None
    if receipt:
        file_ext = receipt.filename.split(".")[-1]
        file_name = f"{current_user.id}_{int(datetime.now().timestamp())}.{file_ext}"
        save_path = f"uploads/{file_name}"
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(receipt.file, buffer)
        receipt_path = f"/uploads/{file_name}"

    new_req = database.PaymentRequest(
        user_id=current_user.id,
        amount=amount,
        method=method,
        receipt_path=receipt_path,
        timestamp=datetime.now().isoformat()
    )
    db.add(new_req)
    db.commit()
    return {"message": "To'lov so'rovi yuborildi. Chek tasdiqlangach pul hisobingizga tushadi."}

@app.get("/admin/payment-requests")
def get_payment_requests(db: Session = Depends(get_db)):
    requests = db.query(database.PaymentRequest, database.User).join(database.User, database.PaymentRequest.user_id == database.User.id).all()
    result = []
    for req, user in requests:
        result.append({
            "id": req.id,
            "username": user.username,
            "amount": req.amount,
            "method": req.method,
            "status": req.status,
            "receipt_path": req.receipt_path,
            "timestamp": req.timestamp
        })
    return result

@app.post("/admin/payment-requests/{req_id}/status")
def update_payment_request_status(req_id: int, status: str, db: Session = Depends(get_db)):
    req = db.query(database.PaymentRequest).filter(database.PaymentRequest.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="So'rov topilmadi")
    
    if req.status == "Approved":
        raise HTTPException(status_code=400, detail="Bu so'rov allaqachon tasdiqlangan")

    req.status = status
    if status == "Approved":
        user = db.query(database.User).filter(database.User.id == req.user_id).first()
        if user:
            user.balance += req.amount
    
    db.commit()
    return {"message": f"So'rov {status.lower()} qilindi"}

@app.get("/admin/payment-settings")
def get_payment_settings(db: Session = Depends(get_db)):
    settings = db.query(database.PaymentSettings).all()
    if not settings:
        # Seed default settings if empty
        defaults = [
            {"method": "click", "title": "Click orqali to'ldirish", "instructions": "Click ilovasi orqali to'lang"},
            {"method": "payme", "title": "Payme orqali to'ldirish", "instructions": "Payme ilovasi orqali to'lang"},
            {"method": "bankomat", "title": "Bankomat orqali to'ldirish", "instructions": "Bankomat orqali transfer"}
        ]
        for d in defaults:
            db.add(database.PaymentSettings(**d))
        db.commit()
        settings = db.query(database.PaymentSettings).all()
    return settings

@app.put("/admin/payment-settings/{method}")
def update_method_settings(method: str, s: PaymentSettingsUpdate, db: Session = Depends(get_db)):
    ps = db.query(database.PaymentSettings).filter(database.PaymentSettings.method == method).first()
    if not ps:
        ps = database.PaymentSettings(method=method)
        db.add(ps)
    
    if s.card_number is not None: ps.card_number = s.card_number
    if s.merchant_id is not None: ps.merchant_id = s.merchant_id
    if s.title is not None: ps.title = s.title
    if s.instructions is not None: ps.instructions = s.instructions
    
    db.commit()
    return {"message": "Sozlamalar yangilandi"}

# === SUPPORT TICKET SYSTEM ===
@app.post("/support/tickets")
async def create_ticket(
    subject: str = Form(...),
    message: str = Form(...),
    attachment: Optional[UploadFile] = File(None),
    current_user: database.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from datetime import datetime
    import shutil
    
    attachment_path = None
    if attachment:
        file_ext = attachment.filename.split(".")[-1]
        file_name = f"support_{current_user.id}_{int(datetime.now().timestamp())}.{file_ext}"
        save_path = f"uploads/{file_name}"
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(attachment.file, buffer)
        attachment_path = f"/uploads/{file_name}"

    new_ticket = database.SupportTicket(
        user_id=current_user.id,
        subject=subject,
        message=message,
        attachment_path=attachment_path,
        timestamp=datetime.now().isoformat()
    )
    db.add(new_ticket)
    db.commit()
    return {"message": "Murojaatingiz yuborildi. Tez orada javob beramiz."}

@app.get("/support/my-tickets")
def get_user_tickets(current_user: database.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(database.SupportTicket).filter(database.SupportTicket.user_id == current_user.id).all()

@app.get("/admin/support/tickets")
def get_all_tickets(db: Session = Depends(get_db)):
    results = db.query(database.SupportTicket, database.User).join(database.User, database.SupportTicket.user_id == database.User.id).all()
    out = []
    for t, u in results:
        out.append({
            "id": t.id,
            "username": u.username,
            "subject": t.subject,
            "message": t.message,
            "attachment_path": t.attachment_path,
            "status": t.status,
            "timestamp": t.timestamp,
            "admin_reply": t.admin_reply
        })
    return out

class SupportReply(BaseModel):
    reply: str

@app.post("/admin/support/tickets/{ticket_id}/reply")
def reply_to_ticket(ticket_id: int, r: SupportReply, db: Session = Depends(get_db)):
    ticket = db.query(database.SupportTicket).filter(database.SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Murojaat topilmadi")
    ticket.admin_reply = r.reply
    ticket.status = "Answered"
    db.commit()
    return {"message": "Javob yuborildi"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# === PUBLIC API V2 (For external users) ===
@app.post("/api/v2")
async def public_api_v2(
    key: str = Form(...),
    action: str = Form(...),
    # For action=add
    service: Optional[str] = Form(None),
    link: Optional[str] = Form(None),
    quantity: Optional[int] = Form(None),
    # For action=status
    order: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    user = db.query(database.User).filter(database.User.api_key == key).first()
    if not user:
        return {"error": "Invalid API Key"}

    if action == "balance":
        return {"balance": user.balance, "currency": "UZS"}
    
    elif action == "services":
        services = db.query(database.Service).all()
        return [
            {
                "service": s.external_service_id, 
                "name": s.name, 
                "category": s.category, 
                "rate": s.price_per_1k, 
                "min": s.min_qty, 
                "max": s.max_qty,
                "type": "Default"
            } for s in services
        ]
    
    elif action == "add":
        if not service or not link or not quantity:
            return {"error": "Parameters missing"}
        
        # Reuse logic from create_order internally
        # We try external_service_id first as that's what public API usually expects
        db_service = db.query(database.Service).filter(database.Service.external_service_id == service).first()
        if not db_service:
            # Try internal id as fallback
            try:
                db_service = db.query(database.Service).filter(database.Service.id == int(service)).first()
            except: pass
            
        if not db_service:
            return {"error": "Service not found"}
        
        total_price = (quantity / 1000) * db_service.price_per_1k
        if user.balance < total_price:
            return {"error": "Insufficient balance"}
        
        new_order = database.Order(
            user_id=user.id,
            service=db_service.name,
            qty=quantity,
            price=total_price,
            status="Processing",
            external_service_id=db_service.external_service_id
        )
        user.balance -= total_price
        db.add(new_order)
        db.commit()
        db.refresh(new_order)

        # Forward to external provider if exists
        api_settings = db.query(database.APISettings).first()
        if api_settings and api_settings.api_key and api_settings.api_url:
            print(f"DEBUG API V2: Forwarding order #{new_order.id} to {api_settings.api_url}")
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    payload = {
                        "key": api_settings.api_key,
                        "action": "add",
                        "service": db_service.external_service_id,
                        "link": link,
                        "quantity": quantity
                    }
                    resp = await client.post(api_settings.api_url, data=payload, timeout=15.0)
                    if resp.status_code == 200:
                        data = resp.json()
                        if "order" in data:
                            new_order.external_id = str(data["order"])
                            db.commit()
                        elif "error" in data:
                            print(f"WARNING API V2: Provider error: {data['error']}")
                    else:
                        print(f"ERROR API V2: Provider status {resp.status_code}")
            except Exception as e:
                print(f"API Forward error in public_api_v2: {e}")

        return {"order": new_order.id}

    elif action == "status":
        if not order:
            return {"error": "Order ID missing"}
        ord_obj = db.query(database.Order).filter(database.Order.id == order, database.Order.user_id == user.id).first()
        if not ord_obj:
            return {"error": "Order not found"}
        
        return {
            "status": ord_obj.status,
            "charge": ord_obj.price,
            "currency": "UZS"
        }

    return {"error": "Invalid action"}

