import os
import sys

def find_recovery_dir():
    if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]):
        return sys.argv[1]
    candidates = [
        "bootable/recovery",
        os.path.join(os.environ.get("ANDROID_BUILD_TOP", ""), "bootable/recovery"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../bootable/recovery")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../bootable/recovery")),
        "/tmp/willowpro_debug/ofox_rec"
    ]
    for c in candidates:
        if c and os.path.isdir(c) and os.path.isfile(os.path.join(c, "partition.cpp")):
            return c
    return None

rec_dir = find_recovery_dir()
if not rec_dir:
    print("[patch_fbe] Warning: bootable/recovery directory not found. Skipping patch.")
    sys.exit(0)

print(f"[patch_fbe] Target recovery directory: {rec_dir}")

# 1. Patch partition.cpp
part_path = os.path.join(rec_dir, "partition.cpp")
with open(part_path, "r", encoding="utf-8", errors="replace") as f:
    part_content = f.read()

target1 = """\t\tif (!Decrypt_FBE_DE() && strcmp(crypto_state, "error") != 0) {
\t\t\tif (is_device_fbe == 1) {
\t\t\t     // check whether the device is encrypted, and, if so, report decryption failure
\t\t\t     if (PartitionManager.Storage_Is_Encrypted() && DataManager::GetStrValue("fox_dfe_formatted") != "1")
\t\t\t\tLOGERR("Unable to decrypt FBE device\\n");
\t\t\t}
\t\t} else {
\t\t\tDataManager::SetValue(TW_IS_ENCRYPTED, 0);
\t\t\tif (datamedia)
\t\t\t\tSetup_Data_Media();
\t\t}"""

replacement1 = """\t\tif (!Decrypt_FBE_DE()) {
\t\t\tif (strcmp(crypto_state, "error") != 0) {
\t\t\t     if (is_device_fbe == 1) {
\t\t\t          if (PartitionManager.Storage_Is_Encrypted() && DataManager::GetStrValue("fox_dfe_formatted") != "1")
\t\t\t               LOGERR("Unable to decrypt FBE device\\n");
\t\t\t     }
\t\t\t} else {
\t\t\t     DataManager::SetValue(TW_IS_ENCRYPTED, 0);
\t\t\t     if (datamedia)
\t\t\t          Setup_Data_Media();
\t\t\t}
\t\t}"""

target2 = """\t\t\tDataManager::SetValue(TW_INTERNAL_PATH, Mount_Point + "/media/0");
\t\t\tUnMount(true);
\t\t}"""

replacement2 = """\t\t\tDataManager::SetValue(TW_INTERNAL_PATH, Mount_Point + "/media/0");
\t\t\tif (!Is_FBE)
\t\t\t\tUnMount(true);
\t\t}"""

if target1 in part_content:
    part_content = part_content.replace(target1, replacement1)
    print("[patch_fbe] partition.cpp: target1 patched successfully")
elif "if (!Decrypt_FBE_DE()) {" in part_content:
    print("[patch_fbe] partition.cpp: target1 already patched")
else:
    print("[patch_fbe] Warning: target1 pattern not found in partition.cpp")

if target2 in part_content:
    part_content = part_content.replace(target2, replacement2)
    print("[patch_fbe] partition.cpp: target2 patched successfully")
elif "if (!Is_FBE)\n\t\t\t\tUnMount(true);" in part_content or "if (!Is_FBE)" in part_content:
    print("[patch_fbe] partition.cpp: target2 already patched")
else:
    print("[patch_fbe] Warning: target2 pattern not found in partition.cpp")

with open(part_path, "w", encoding="utf-8") as f:
    f.write(part_content)

# 2. Patch partitionmanager.cpp
pm_path = os.path.join(rec_dir, "partitionmanager.cpp")
with open(pm_path, "r", encoding="utf-8", errors="replace") as f:
    pm_content = f.read()

target3 = """\t\tif (!Mount_By_Path("/data", true)) // /data has to be mounted for FBE
\t\t\treturn -1;

\t\tbool user_need_decrypt = false;"""

replacement3 = """\t\tif (!Mount_By_Path("/data", true)) // /data has to be mounted for FBE
\t\t\treturn -1;

\t\tif (!TWFunc::Path_Exists("/data/misc/vold/user_keys/ce/0/current")) {
\t\t\tLOGINFO("DE keys missing after mounting /data, reloading via Decrypt_DE...\\n");
\t\t\tDecrypt_DE();
\t\t}

\t\tbool user_need_decrypt = false;"""

if target3 in pm_content:
    pm_content = pm_content.replace(target3, replacement3)
    print("[patch_fbe] partitionmanager.cpp: target3 patched successfully")
elif "reloading via Decrypt_DE" in pm_content:
    print("[patch_fbe] partitionmanager.cpp: target3 already patched")
else:
    print("[patch_fbe] Warning: target3 pattern not found in partitionmanager.cpp")

target4 = """\t\tsleep(1); // Sleep for a bit so that the device will be ready
\t\tif (dat->Has_Data_Media && dat->Mount(false) && TWFunc::Path_Exists("/data/media/0")) {
\t\t\tdat->Storage_Path = "/data/media/0";
\t\t\tdat->Symlink_Path = dat->Storage_Path;
\t\t\tDataManager::SetValue("tw_storage_path", "/data/media/0");
\t\t\tDataManager::SetValue("tw_settings_path", "/data/media/0");
\t\t}
\t\tUpdate_System_Details();
\t\tOutput_Partition(dat);
\t\tif (!android::base::StartsWith(dat->Actual_Block_Device, "/dev/block/mmcblk")) {
\t\tif (!dat->Bind_Mount(false))
\t\t\tLOGERR("Unable to bind mount /sdcard to %s\\n", dat->Storage_Path.c_str());
\t\t}"""

replacement4 = """\t\tsleep(1); // Sleep for a bit so that the device will be ready
\t\tif (dat->Mount(false)) {
\t\t\tif (!dat->Has_Data_Media)
\t\t\t\tdat->Setup_Data_Media();
\t\t\tif (TWFunc::Path_Exists("/data/media/0")) {
\t\t\t\tdat->Storage_Path = "/data/media/0";
\t\t\t\tdat->Symlink_Path = dat->Storage_Path;
\t\t\t\tSetup_Settings_Storage_Partition(dat);
\t\t\t}
\t\t}
\t\tUpdate_System_Details();
\t\tOutput_Partition(dat);
\t\tif (!dat->Bind_Mount(false))
\t\t\tLOGERR("Unable to bind mount /sdcard to %s\\n", dat->Storage_Path.c_str());
\t\tif (dat->MTP_Storage_ID == 0)
\t\t\tdat->MTP_Storage_ID = 0x00010002;
\t\tAdd_MTP_Storage(dat->MTP_Storage_ID);"""

if target4 in pm_content:
    pm_content = pm_content.replace(target4, replacement4)
    print("[patch_fbe] partitionmanager.cpp: target4 patched successfully")
elif "dat->Setup_Data_Media();" in pm_content:
    print("[patch_fbe] partitionmanager.cpp: target4 already patched")
else:
    print("[patch_fbe] Warning: target4 pattern not found in partitionmanager.cpp")

with open(pm_path, "w", encoding="utf-8") as f:
    f.write(pm_content)

print("[patch_fbe] Done applying FBE 4.19 keyring patches.")
