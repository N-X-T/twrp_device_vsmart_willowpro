#!/system/bin/sh
# Smart BCB handler for willowpro (MT6765)
# Clears BCB only on boot-recovery to prevent recovery bootloop,
# but preserves boot-fastboot so the device can enter fastbootd.

PARA_DEV="/dev/block/platform/bootdevice/by-name/para"
[ -b "$PARA_DEV" ] || exit 0

CMD=$(head -c 32 "$PARA_DEV" | tr -d '\0')

if [ "$CMD" = "boot-fastboot" ]; then
    # Keep BCB intact for recovery to enter fastbootd
    exit 0
fi

if [ "$CMD" = "boot-recovery" ]; then
    # Clear boot-recovery flag to prevent bootloop
    dd if=/dev/zero of="$PARA_DEV" bs=1024 count=2 conv=notrunc
    exit 0
fi
