#!/bin/sh

cp lvgl/lvgl/lv_conf_template.h lvgl/lv_conf.h

cd lvgl/lv_port_linux
cd ../..

gcc -E -std=c99 -Ifake_libc_include \
    -DLV_USE_OS=5 -DLV_USE_WINDOWS -DLV_USE_LINUX_FBDEV -DLV_USE_EVDEV \
    -DLV_USE_FLEX -DLV_USE_GRID \
    -DLV_USE_QRCODE \
    -DLV_USE_TINY_TTF -DLV_TINY_TTF_FILE_SUPPORT \
    -DLV_USE_LODEPNG \
    -DLV_USE_DRAW_SW_COMPLEX_GRADIENTS \
    -DPYCPARSER \
    lvgl/lvgl/lvgl.h > lvgl.h
