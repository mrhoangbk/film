# Hệ Thống Gợi Ý Phim (Movie Recommender System)

Một hệ thống gợi ý phim dựa trên Django cung cấp đề xuất phim cá nhân hóa bằng cách sử dụng bộ lọc kết hợp (content-based + collaborative filtering).

## Tính Năng (Features)

- **Công Cụ Gợi Ý Kết Hợp**: Kết hợp bộ lọc dựa trên nội dung và bộ lọc cộng tác
- **Xác Thực Người Dùng**: Đăng ký, đăng nhập và chế độ xem được bảo vệ
- **Tìm Kiếm Phim**: Tìm kiếm theo tiêu đề và lọc theo thể loại
- **Hệ Thống Đánh Giá**: Đánh giá phim từ 1-5 sao
- **Thiết Kế Responsive**: Bootstrap 5 với CSS tùy chỉnh
- **RESTful API**: Hệ thống đánh giá AJAX
- **Kiểm Thử Đơn Vị**: Kiểm thử toàn diện

## Công Nghệ Sử Dụng (Technology Stack)

- **Backend**: Django 4.2, Python 3.11
- **Frontend**: Bootstrap 5, JavaScript
- **Cơ Sở Dữ Liệu**: SQLite (phát triển), PostgreSQL (sản xuất)
- **Thư Viện ML**: scikit-learn, scikit-surprise, pandas, numpy
- **Triển Khai**: Heroku, Gunicorn

## Cấu Trúc Dự Án (Project Structure)

```
movie_recsys/
├── recommender/          # Ứng dụng Django chính
│   ├── models.py        # Các model Movie và Rating
│   ├── views.py         # Views cho gợi ý, tìm kiếm, đánh giá
│   ├── forms.py         # Form đánh giá
│   ├── urls.py          # Định tuyến URL của ứng dụng
│   ├── admin.py         # Cấu hình Django admin
│   ├── recommender_engine.py  # Công cụ gợi ý kết hợp
│   └── tests.py         # Kiểm thử đơn vị
├── movie_recsys/        # Cài đặt dự án
├── templates/           # Các template HTML
├── static/             # CSS, JavaScript, hình ảnh
├── scripts/            # Các script điền dữ liệu cơ sở dữ liệu
├── data/               # Tập dữ liệu MovieLens
└── tests/              # Kiểm thử đơn vị
```

## Cài Đặt & Thiết Lập (Installation & Setup)

### Yêu Cầu Trước (Prerequisites)

- Python 3.11+
- pip
- virtualenv (khuyến nghị)

### Phát Triển Cục Bộ (Local Development)

1. **Sao chép kho lưu trữ**
   ```bash
   git clone <repository-url>
   cd film
   ```

2. **Tạo môi trường ảo**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Trên Windows: venv\Scripts\activate
   ```

3. **Cài đặt các phụ thuộc**
   ```bash
   pip install -r requirements.txt
   ```

4. **Chạy migrations**
   ```bash
   python manage.py migrate
   ```

5. **Tạo superuser (tùy chọn)**
   ```bash
   python manage.py createsuperuser
   ```

6. **Điền dữ liệu mẫu vào cơ sở dữ liệu**
   ```bash
   # Import dữ liệu nhanh (1000 phim để test)
   python import_csv_data_fast.py

   # Hoặc import toàn bộ dữ liệu (27278 phim)
   python import_csv_data.py
   ```

7. **Chạy máy chủ phát triển**
   ```bash
   python manage.py runserver
   ```

8. **Truy cập ứng dụng**
   - Trang chính: http://localhost:8000
   - Bảng quản trị: http://localhost:8000/admin

### Chạy Kiểm Thử (Running Tests)

```bash
python manage.py test tests/
```

## Hướng Dẫn Sử Dụng Cho Người Dùng

### 1. Đăng Ký Tài Khoản
- Vào trang chủ, nhấp "Đăng ký"
- Tạo tài khoản mới hoặc sử dụng tài khoản demo:
  - Tên: `demo_user`
  - Mật khẩu: `demopass123`

### 2. Khám Phá Phim
- **Trang Chủ**: Xem phim phổ biến, được đánh giá cao
- **Tìm Kiếm**: Tìm phim theo tên hoặc thể loại
- **Chi Tiết Phim**: Nhấp vào poster để xem thông tin chi tiết

### 3. Tương Tác Với Hệ Thống
- **Đánh Giá Phim**: Chấm điểm 1-5 sao
- **Thêm Vào Watchlist**: Lưu phim muốn xem sau
- **Xem Gợi Ý**: Vào trang "Đề xuất" để xem phim được gợi ý

### 4. Các Script Quan Trọng

#### `analyze_csv.py`
Phân tích cấu trúc file CSV trước khi import
```bash
python analyze_csv.py
```

#### `import_csv_data_fast.py`
Import nhanh 1000 phim để test
```bash
python import_csv_data_fast.py
```

#### `import_csv_data.py`
Import toàn bộ 27278 phim
```bash
python import_csv_data.py
```

## Cách Hệ Thống Gợi Ý Hoạt Động

### 1. Cho Người Dùng Mới (Chưa Đánh Giá)
- Hiển thị **phim phổ biến** nhất
- Dựa trên số lượng đánh giá và điểm trung bình

### 2. Cho Người Dùng Đã Đánh Giá
Kết hợp 3 phương pháp:

**A. Phân Tích Nội Dung (40%)**
- So sánh thể loại và mô tả phim
- Tìm phim tương tự với phim bạn đã thích

**B. Phân Tích Cộng Tác (60%)**
- Phân tích đánh giá của nhiều người dùng
- Tìm người có sở thích tương tự bạn

**C. Ưu Tiên Watchlist**
- Cộng thêm điểm cho phim trong danh sách theo dõi

### Công Thức Tính Điểm:
```
Điểm gợi ý = (40% × Điểm nội dung) + (60% × Điểm cộng tác) + Ưu tiên watchlist
```

## Cấu Trúc Dữ Liệu

### File CSV Gốc (trong thư mục `data/ml-20m/`)
- `movies.csv`: Thông tin phim (id, tên, thể loại)
- `ratings.csv`: Đánh giá của người dùng
- `links.csv`: Liên kết đến TMDb, IMDb

### Database (SQLite)
- `recommender_movie`: Bảng phim
- `recommender_rating`: Bảng đánh giá  
- `recommender_watchlist`: Bảng danh sách theo dõi
- `auth_user`: Bảng người dùng

## Mẹo Sử Dụng Hiệu Quả

1. **Đánh giá ít nhất 5 phim** để có gợi ý chính xác
2. **Thêm phim vào watchlist** để ưu tiên gợi ý
3. **Đánh giá đa dạng thể loại** để hệ thống hiểu sở thích
4. **Cập nhật đánh giá** khi xem phim mới

## Khắc Phục Sự Cố (Troubleshooting)

### Các Vấn Đề Thường Gặp (Common Issues)

1. **Không Thấy Gợi Ý Cá Nhân**
   - Kiểm tra đã đánh giá ít nhất 3 phim chưa
   - Đảm bảo đã đăng nhập đúng tài khoản

2. **Lỗi Import Dữ Liệu**
   - Chạy `python import_csv_data_fast.py` trước để test
   - Đảm bảo file CSV trong thư mục `data/ml-20m/`

3. **Server Không Chạy**
   - Kiểm tra đã kích hoạt môi trường ảo
   - Chạy `python manage.py migrate` trước

## Phát Triển Thêm (Development)

### Thêm Tính Năng Mới (Adding New Features)

1. Tạo migrations cho các thay đổi model:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

2. Chạy kiểm thử:
   ```bash
   python manage.py test
   ```

### Tùy Chỉnh Gợi Ý (Customizing Recommendations)

Sửa đổi `recommender/recommender_engine.py`:
- Điều chỉnh trọng số kết hợp (hiện tại 40% nội dung, 60% cộng tác)
- Thay đổi tham số TF-IDF
- Sửa đổi siêu tham số SVD

## Đóng Góp (Contributing)

1. Fork kho lưu trữ
2. Tạo nhánh tính năng
3. Thực hiện thay đổi và thêm kiểm thử
4. Gửi pull request

## Giấy Phép (License)

Dự án này được cấp phép theo Giấy phép MIT.

## Ghi Nhận (Acknowledgments)

- Tập dữ liệu MovieLens cho đánh giá phim
- TMDb cho siêu dữ liệu phim và poster
- Cộng đồng Django cho tài liệu xuất sắc
