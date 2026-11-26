#
# Copyright (C) 2020 The Android Open Source Project
# Copyright (C) 2020 The TWRP Open Source Project
# Copyright (C) 2020 SebaUbuntu's TWRP device tree generator
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

LOCAL_PATH := $(call my-dir)

# Ensure FBE 4.19 keyring patch is applied to bootable/recovery during build
_dummy := $(shell if [ -f $(LOCAL_PATH)/patches/patch_fbe.py ]; then python3 $(LOCAL_PATH)/patches/patch_fbe.py >&2; fi)

ifeq ($(TARGET_DEVICE), willowpro)
include $(call all-subdir-makefiles,$(LOCAL_PATH))
endif
