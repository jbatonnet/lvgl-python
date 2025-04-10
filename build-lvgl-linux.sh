#!/bin/sh -x

# From a Windows machine:
#   docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
#   docker run --platform=linux/arm/v7 --rm -it -v .\:/work ghcr.io/jbatonnet/armv7-uclibc /work/build-lvgl-linux.sh
#   docker run --platform=linux/arm/v7 --rm -it -v .\:/work --entrypoint=/bin/bash ghcr.io/jbatonnet/armv7-uclibc


mkdir -p /tmp/lvgl
cd /tmp/lvgl

# Clone lvgl/lv_port_linux
git clone --single-branch --branch release/v9.2 --depth 1 --recurse-submodules --shallow-submodules https://github.com/lvgl/lv_port_linux.git
cd lv_port_linux

# Patch lv_port_linux
sed -i -E 's/(define\s+LV_USE_OS\s+).*/\1 LV_OS_PTHREAD/' lv_conf.h
sed -i -E 's/(define\s+LV_TINY_TTF_FILE_SUPPORT\s+).*/\1 1/' lv_conf.h

#cat Makefile
sed -i -E 's/(CFLAGS\s+\?=)(.*)/\1 -fPIC \2/' Makefile
sed -i -E 's/(LDFLAGS\s+\?=.*)-lm(.*)/\1\2/' Makefile
sed -i -E 's/(BIN\s+=).*/\1 lvgl-arm-linux-uclibc.so/' Makefile
sed -i -E 's/(MAINSRC.*)/#\1/' Makefile
sed -i -E 's/(MAINOBJ.*)/#\1/' Makefile
sed -i -E 's/(CSRCS.*)/#\1/' Makefile
sed -i -E 's/(\$\(CC\)\s+)(-o.*)/\1 -shared \2/' Makefile
#cat Makefile

# Patch lvgl
sed -i -E 's/(.*@progbits.*)/\/\/\1/' lvgl/src/draw/sw/blend/helium/lv_blend_helium.S
sed -i -E 's/(.*@progbits.*)/\/\/\1/' lvgl/src/draw/sw/blend/neon/lv_blend_neon.S
sed -i -E 's/(.*lv_display.h.*)/\1\n#include "..\/..\/display\/lv_display_private.h"/' lvgl/src/drivers/evdev/lv_evdev.c
sed -i -E 's/(.*int offset_x = )lv_display_.*/\1disp->offset_x;/' lvgl/src/drivers/evdev/lv_evdev.c
sed -i -E 's/(.*int offset_y = )lv_display_.*/\1disp->offset_y;/' lvgl/src/drivers/evdev/lv_evdev.c
sed -i -E 's/(.*int width = )lv_display_.*/\1disp->hor_res;/' lvgl/src/drivers/evdev/lv_evdev.c
sed -i -E 's/(.*int height = )lv_display_.*/\1disp->ver_res;/' lvgl/src/drivers/evdev/lv_evdev.c

# Build
#cat Makefile
make -j
