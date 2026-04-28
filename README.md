# LMS Class Management System

Hệ thống quản lý lớp học MindX với bộ lọc đa dạng và giao diện chuyên nghiệp.

## Tính năng

### 1. Bộ lọc đa dạng
- **Cơ sở**: Lọc theo 4 cơ sở (Tên Lửa, Tây Thạnh, Lũy Bán Bích, Trường Chinh)
- **Ngày bắt đầu**: Lọc từ ngày X đến ngày Y
- **Ngày kết thúc**: Lọc từ ngày X đến ngày Y
- **Khóa học**: Lọc theo tên khóa học
- **Trạng thái**: New, Preparing, Running, Finished, v.v.
- **Comments**: Lọc theo % comments (100%, >50%, có comment, chưa có)
- **Mentor**: Lọc theo giáo viên

### 2. Chi tiết lớp học
Click vào card để xem:
- Thông tin cơ bản: tên, trạng thái, khóa học, cơ sở
- Số buổi học, số học viên
- Danh sách giáo viên (tên, role, email)
- Lịch học chi tiết (slots)
- % Comments đã hoàn thành

### 3. Giao diện
- Font chữ: **Exo 2** (chuyên nghiệp, hiện đại)
- Layout responsive với grid system
- Bộ lọc căn đều theo chiều ngang
- Modal chi tiết với animation mượt mà

## Cài đặt

### Yêu cầu
- Python 3.x + `requests`
- Node.js 18+ + npm

### Bước 1: Cài dependencies
```bash
npm install
pip install requests
```

### Bước 2: Cập nhật token
Mở `main.py` → cập nhật biến `TOKEN` với token mới từ web MindX

### Bước 3: Chạy
```bash
npm run dev
```

Script sẽ tự động:
1. Chạy `python main.py` → lấy data từ API
2. Khởi động Vite dev server

## Về tính năng Comments

### Độ khả thi: ✅ Khả thi 100%

API MindX trả về đầy đủ thông tin comments qua field `studentAttendance` trong mỗi slot:

```json
{
  "slots": [
    {
      "studentAttendance": [
        {
          "comment": "Học tốt",
          "sendCommentStatus": "SENT"
        }
      ]
    }
  ]
}
```

Hệ thống tính toán:
- **Total students with slots**: Tổng số học viên có attendance
- **Students with comments**: Số học viên đã có comment
- **Comment percentage**: % = (có comment / tổng) × 100

Bộ lọc comments:
- **100%**: Chỉ lớp đã comment đủ 100%
- **>50%**: Lớp đã comment trên 50%
- **Có comment**: Lớp có ít nhất 1 comment
- **Chưa có**: Lớp chưa có comment nào

## Cấu trúc dự án

```
├── main.py                 # Script Python lấy data
├── public/
│   └── classes.json        # Data được lưu
├── src/
│   ├── components/
│   │   ├── Sidebar.tsx
│   │   ├── ClassFilters.tsx
│   │   └── ClassDetail.tsx
│   ├── pages/
│   │   ├── ClassesPage.tsx
│   │   └── MentorsPage.tsx
│   ├── hooks/
│   │   └── useClasses.ts
│   ├── types/
│   │   └── index.ts
│   ├── App.tsx
│   ├── App.css
│   └── index.css
└── package.json
```

## Lưu ý

- Token JWT hết hạn sau 1 giờ → cần cập nhật thường xuyên
- Data được cache trong `public/classes.json`
- Giới hạn 500 lớp để tăng tốc độ load
