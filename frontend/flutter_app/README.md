samples, guidance on mobile development, and a full API reference.
# Hướng dẫn sử dụng Flutter App

>Dành cho mọi thành viên, kể cả người mới bắt đầu.

---

## 1. Cài đặt môi trường Flutter

### Yêu cầu hệ thống
- Windows 7 SP1 trở lên (64-bit)
- Dung lượng ổ đĩa trống tối thiểu 2 GB
- Đã cài đặt Git for Windows

### Cài đặt Flutter SDK
1. Truy cập: https://docs.flutter.dev/get-started/install
2. Tải về Flutter SDK cho hệ điều hành của bạn.
3. Giải nén vào thư mục (ví dụ: `C:\src\flutter`).
4. Thêm `C:\src\flutter\bin` vào biến môi trường `PATH`.
5. Cài đặt Android Studio (hoặc VS Code) và plugin Flutter/Dart.

### Kiểm tra cài đặt
Mở Terminal/CMD và chạy:
```sh
flutter doctor
```
Làm theo hướng dẫn để hoàn thiện môi trường.

---

## 2. Chạy ứng dụng Flutter

### a. Cài dependencies
```sh
flutter pub get
```

### b. Chạy ứng dụng
Kết nối thiết bị thật (bật chế độ nhà phát triển & USB Debugging) hoặc mở Android/iOS emulator, sau đó:
```sh
flutter run
```

### c. Debug ứng dụng trên thiết bị thật
1. Bật chế độ nhà phát triển (Developer Options) và USB Debugging trên điện thoại Android.
2. Kết nối điện thoại với máy tính qua cáp USB.
3. Kiểm tra thiết bị đã nhận:
   ```sh
   flutter devices
   ```
   Nếu thấy tên thiết bị, tiếp tục bước sau.
4. Chạy debug:
   ```sh
   flutter run
   ```
   Ứng dụng sẽ cài lên điện thoại, bạn có thể đặt breakpoint, hot reload/hot restart từ IDE (Android Studio/VS Code).

### d. Build APK
```sh
flutter build apk
```
File APK sẽ nằm trong `build/app/outputs/flutter-apk/app-release.apk`.

---

### e. Build và chạy bản Web
Đảm bảo đã cài Chrome hoặc trình duyệt Chromium.

#### Build web:
```sh
flutter build web
```
Kết quả sẽ nằm trong thư mục `build/web/`.

#### Chạy thử bản web (dev server):
```sh
flutter run -d chrome
```
Hoặc:
```sh
flutter serve
```
Sau đó truy cập địa chỉ được in ra terminal (thường là http://localhost:8000 hoặc http://localhost:8080).

---

## 3. Cấu trúc thư mục chính

```
lib/
  main.dart                  // Điểm khởi động ứng dụng
  config/                    // Cấu hình môi trường
  models/                    // Định nghĩa model dữ liệu
  providers/                 // State management
  screens/                   // Các màn hình giao diện
  services/                  // Dịch vụ dịch, TTS, offline...
```

### Giải thích nhanh:
- **main.dart**: Khởi tạo app, điều hướng.
- **config/env.dart**: Cấu hình môi trường (API endpoint, v.v).
- **models/translation_history.dart**: Định nghĩa lịch sử dịch.
- **providers/translation_provider.dart**: Quản lý trạng thái dịch.
- **screens/**: Các màn hình chính như Trang chủ, Lịch sử, Yêu thích.
- **services/**: Tích hợp dịch máy, dịch offline, chuyển văn bản thành giọng nói.
