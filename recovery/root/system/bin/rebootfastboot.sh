#!/system/bin/sh
# Handler executed by TWRP/OrangeFox GUI when selecting "Reboot Fastboot"

PARA_DEV="/dev/block/platform/bootdevice/by-name/para"
[ -b "$PARA_DEV" ] || PARA_DEV="/dev/block/by-name/para"

if [ -b "$PARA_DEV" ]; then
    # Write boot-fastboot into boot.command (offset 0)
    printf 'boot-fastboot\0' | dd of="$PARA_DEV" bs=1 seek=0 count=14 conv=notrunc 2>/dev/null
    # Write recovery\n--fastboot\n\0 into boot.recovery (offset 64)
    printf 'recovery\n--fastboot\n\0' | dd of="$PARA_DEV" bs=1 seek=64 count=21 conv=notrunc 2>/dev/null
    sync
fi

CACHE_DEV="/dev/block/platform/bootdevice/by-name/cache"
[ -b "$CACHE_DEV" ] || CACHE_DEV="/dev/block/by-name/cache"
if [ -b "$CACHE_DEV" ]; then
    mkdir -p /cache
    mount -t ext4 "$CACHE_DEV" /cache 2>/dev/null
    if [ $? -eq 0 ]; then
        mkdir -p /cache/recovery
        echo "--fastboot" > /cache/recovery/command
        sync
        umount /cache 2>/dev/null
    fi
fi

exit 0
