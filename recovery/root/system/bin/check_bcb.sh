#!/system/bin/sh
# Smart BCB handler for willowpro (MT6765)
# Ensures fastbootd triggers correctly for adb reboot fastboot and UI Reboot Fastboot,
# while preventing recovery bootloops on normal boot-recovery.

PARA_DEV="/dev/block/platform/bootdevice/by-name/para"
[ -b "$PARA_DEV" ] || PARA_DEV="/dev/block/by-name/para"
[ -b "$PARA_DEV" ] || exit 0

# Read 32-byte command field (offset 0) and 64 bytes of recovery field (offset 64)
CMD=$(dd if="$PARA_DEV" bs=1 count=32 2>/dev/null | tr -d '\0')
REC=$(dd if="$PARA_DEV" bs=1 skip=64 count=64 2>/dev/null | tr -d '\0')

IS_FASTBOOT=0
case "$CMD" in
    boot-fastboot*)
        IS_FASTBOOT=1
        ;;
esac

case "$REC" in
    *fastboot*)
        IS_FASTBOOT=1
        ;;
esac

if [ "$IS_FASTBOOT" -eq 1 ]; then
    # 1. Set runtime property for early init listeners
    setprop ro.boot.fastboot 1

    # 2. Preserve/reinforce boot-fastboot in BCB command (offset 0)
    printf 'boot-fastboot\0' | dd of="$PARA_DEV" bs=1 seek=0 count=14 conv=notrunc 2>/dev/null

    # 3. Inject 'recovery\n--fastboot\n\0' into BCB recovery field (offset 64)
    #    so TWRP/OrangeFox get_args() parses --fastboot and launches fastbootd
    printf 'recovery\n--fastboot\n\0' | dd of="$PARA_DEV" bs=1 seek=64 count=21 conv=notrunc 2>/dev/null
    sync

    # 4. Fallback: Also write --fastboot into /cache/recovery/command
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
fi

# Normal recovery boot handling: clear BCB only on boot-recovery to prevent bootloop
case "$CMD" in
    boot-recovery*)
        dd if=/dev/zero of="$PARA_DEV" bs=1024 count=2 conv=notrunc 2>/dev/null
        sync
        exit 0
        ;;
esac

exit 0
