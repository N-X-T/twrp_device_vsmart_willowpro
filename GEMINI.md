# Hướng dẫn & Quy tắc phát triển Recovery (Vsmart Willow Pro / MT6765)

Dự án này là Recovery Device Tree (TWRP / OrangeFox) dành cho Vsmart Star 4 (`willowpro` / `V341A`, chip MTK MT6765 Helio P35, Android 10 SAR, Dynamic Partitions).

Khi chỉnh sửa mã nguồn trong thư mục này, luôn tuân thủ các quy tắc sau:

## 1. Màn hình & Tỷ lệ hiển thị (OrangeFox & TWRP)
- Độ phân giải vật lý của máy là 720x1560 (19.5:9, 320 DPI).
- Trong `vendorsetup.sh`: `OF_SCREEN_H` PHẢI đặt theo tỷ lệ ảo 1080p:
  `export OF_SCREEN_H=2340` (1080 * 1560 / 720 = 2340). Tuyệt đối không đặt bằng 1560.
- Trong `BoardConfig.mk`: Giữ `TW_Y_OFFSET := 0` và `TW_H_OFFSET := 0` vì OrangeFox đã tự quản lý notch thông qua `OF_STATUS_H=60` và `OF_HIDE_NOTCH=1`.

## 2. Bootloader Message (BCB) & Cơ chế kích hoạt Fastbootd
- Phân vùng chứa BCB trên MT6765 là `para` (`/dev/block/platform/bootdevice/by-name/para`).
- Không đổi tên phân vùng trong recovery fstab; luôn map symlink sang `misc`.
- TWRP/OrangeFox `get_args()` chỉ đọc tham số từ trường `recovery` (offset 64) và file `/cache/recovery/command`, bỏ qua cờ `boot-fastboot` ở trường `command` (offset 0) do Android OS / reboot ghi ra.
- Trong `init.recovery.mt6765.rc`, duy trì script thông minh `/system/bin/check_bcb.sh` ở `on post-fs`:
  - Khi phát hiện `boot-fastboot`: đặt `setprop ro.boot.fastboot 1`, tiêm `recovery\n--fastboot\n\0` vào offset 64 của `para`, và ghi dự phòng `--fastboot` vào `/cache/recovery/command`.
  - Chỉ xóa `para` khi cờ là `boot-recovery` (chống recovery bootloop).
  ```init
  exec u:r:recovery:s0 -- /system/bin/check_bcb.sh
  ```
- Luôn duy trì script `/system/bin/rebootfastboot.sh` và symlink `/sbin/rebootfastboot.sh` để xử lý khi chọn "Reboot Fastboot" trong GUI TWRP/OrangeFox trước khi thiết bị reboot.

## 3. Cấu hình USB & MTP
- MT6765 sử dụng kernel driver `/dev/mtp_usb` kết hợp ConfigFS `musb-hdrc`.
- Trong `BoardConfig.mk`: Phải có `TW_HAS_MTP := true` và `TW_MTP_DEVICE := /dev/mtp_usb`.
- Trong `init.recovery.usb.rc`:
  - Vendor ID cho MTP/ADB là MediaTek `0x0e8d`.
  - Vendor ID / Product ID cho `fastbootd` là Google chuẩn `0x18d1:0x4ee0` (để tương thích driver Windows/Linux).
  - Khởi động mặc định phải là `mtp,adb`.
  - Tuyệt đối không dùng trigger `on property:hwservicemanager.ready=true` để gán lại USB config vì sẽ làm ngắt (stop) daemon `fastbootd`.
  - Không ghi vào `/sys/class/android_usb/android0` vì kernel dùng ConfigFS.

## 4. OrangeFox Startup Script trên Android 10+
- Luôn duy trì file script thực thi [recovery/root/system/bin/foxstart.sh](file:///root/twrp_device_vsmart_willowpro/recovery/root/system/bin/foxstart.sh) và symlink `/sbin/foxstart.sh` trong init rc để tránh lỗi `ERROR: 127` khi recovery khởi chạy.

## 5. Khai báo phân vùng lưu trữ
- Không khai báo mountpoint `auto` với cờ `voldmanaged` trong `recovery.fstab`.
- Khai báo thẻ nhớ ngoài và OTG độc quyền trong `twrp.flags` dưới dạng `/external_sd` và `/usb-otg`.

## 6. Giải mã /data (FBE v1, Kernel 4.19 & Beanpod Keymaster 4.0)
- Thiết bị sử dụng FBE v1 kết hợp Microtrust Beanpod TEE (`teei_daemon`, Keymaster 4.0, Gatekeeper 1.0).
- Kernel 4.19 quản lý khóa fscrypt gắn liền với superblock của `/data` (`FS_IOC_ADD_ENCRYPTION_KEY`). Tuyệt đối không unmount `/data` sau khi nạp khóa DE vì sẽ xóa sạch keyring trong kernel.
- Bản vá tự động cho `bootable/recovery` nằm tại `patches/patch_fbe.py` và `patches/fbe_4.19_keyring.patch`.
- Trong `Android.mk`, lệnh gọi script vá bắt buộc phải gán vào biến dummy và xuất log ra stderr:
  `_dummy := $(shell if [ -f $(LOCAL_PATH)/patches/patch_fbe.py ]; then python3 $(LOCAL_PATH)/patches/patch_fbe.py >&2; fi)`
- Sau khi User 0 giải mã thành công trong `Post_Decrypt()`, recovery phải tự động:
  - Khởi tạo `Setup_Data_Media()` gán `tw_has_internal=1` và `Storage_Name = "Internal Storage"`.
  - Bind-mount `/data/media/0` vào `/sdcard` (không chặn thiết bị eMMC `mmcblk`).
  - Gửi tín hiệu `Add_MTP_Storage` nạp bộ nhớ trong vào MTP daemon.
- Phân vùng `persist` (`/dev/block/platform/bootdevice/by-name/persist`) bắt buộc phải được mount vào CẢ HAI đường dẫn `/mnt/vendor/persist` và `/persist` ngay tại trigger `on fs` trong `init.recovery.teei_daemon.rc` trước khi gọi `start teei_daemon`. Tuyệt đối không tạo thư mục tạm `/persist/rpmb` trên ramdisk vì `teei_daemon` sẽ ưu tiên đọc ramdisk rỗng thay vì dữ liệu RPMB thật của máy, gây lỗi Gatekeeper `search uid failed` khi mở khóa bằng mã PIN.
- Node phần cứng RPMB `/dev/mmcblk0rpmb` phải được phân quyền `chmod 0660` và `chown root system`, kèm symlink `/dev/mmcblk0rpmb -> /dev/emmcrpmb0` để TEE HAL và Gatekeeper TA truy cập được bộ nhớ bảo mật.
