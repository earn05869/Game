# Multiplayer Network System

## Overview
ระบบ multiplayer สำหรับเกม BindGame ที่รองรับการเล่น 2 คน โดยต้องมีผู้เล่นครบ 2 คนจึงจะเริ่มเกมได้

## ไฟล์ที่เกี่ยวข้อง
- **server.py** - เซิร์ฟเวอร์สำหรับจัดการการเชื่อมต่อและซิงค์ข้อมูล
- **network.py** - Network client สำหรับเชื่อมต่อกับเซิร์ฟเวอร์
- **game.py** - Game loop ที่จัดการ states และการเชื่อมต่อ
- **simple_2d_game.py** - GameConfig และ game states

## วิธีการใช้งาน

### 1. เริ่มต้นเซิร์ฟเวอร์
```bash
cd BindGame
python3 server.py
```

เซิร์ฟเวอร์จะ:
- รอการเชื่อมต่อของผู้เล่นคนที่ 1
- รอการเชื่อมต่อของผู้เล่นคนที่ 2
- ส่งสัญญาณ "ready" ไปยังผู้เล่นทั้งสองเมื่อครบ 2 คน
- รับและ broadcast ตำแหน่งของผู้เล่น

### 2. เริ่มเกม (ผู้เล่นคนที่ 1)
ใน terminal ใหม่:
```bash
cd BindGame
python3 game.py
```

### 3. เริ่มเกม (ผู้เล่นคนที่ 2)
ใน terminal ใหม่:
```bash
cd BindGame
python3 game.py
```

## Game Flow

1. **STATE_HOME** - แสดงหน้า HomePage
2. กดปุ่ม **Play**
3. **STATE_CONNECTING** - กำลังเชื่อมต่อกับเซิร์ฟเวอร์
4. **STATE_WAITING** - รอผู้เล่นคนที่ 2
   - ผู้เล่นคนที่ 1: "Waiting for other player..."
   - ผู้เล่นคนที่ 2: เมื่อเชื่อมต่อเสร็จ, เซิร์ฟเวอร์จะส่ง "ready" signal
5. เมื่อได้รับสัญญาณ "ready" → **STATE_DIALOGUE** → **STATE_PLAYING**
6. **STATE_PLAYING** - เล่นเกมและ sync ตำแหน่ง

## Network Protocol

### Messages from Server

**Connection Response:**
```json
{
  "player_id": 1 or 2,
  "message": "connected"
}
```

**Ready Signal:**
```json
{
  "message": "ready"
}
```

**Position Update:**
```json
{
  "player_id": 1 or 2,
  "position": {
    "x": 100,
    "y": 200
  }
}
```

### Messages to Server

**Position Update:**
```json
{
  "x": 100,
  "y": 200
}
```

**Disconnect:**
```
"quit"
```

## Configuration

ใน `simple_2d_game.py`:

```python
SERVER_HOST = "localhost"  # เปลี่ยนเป็น IP ของ server หากเล่นข้ามเครื่อง
SERVER_PORT = 5555
```

## หมายเหตุ

- ต้องรันเซิร์ฟเวอร์ก่อนเริ่มเล่น
- ไม่สามารถเพิ่มผู้เล่นมากกว่า 2 คน
- หากผู้เล่นคนใด disconnect เซิร์ฟเวอร์จะปิด connection กับผู้เล่นคนนั้น
- ตำแหน่งของผู้เล่นจะถูกส่งทุก frame ขณะเล่นเกม

