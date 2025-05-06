#!/bin/sh

gcc -E -P -std=c99 -Ifake_libc_include \
    -DLV_USE_OS=5 -DLV_USE_WINDOWS -DLV_USE_LINUX_FBDEV -DLV_USE_EVDEV \
    -DLV_USE_FLEX -DLV_USE_GRID \
    -DLV_USE_QRCODE \
    -DLV_USE_TINY_TTF -DLV_TINY_TTF_FILE_SUPPORT \
    -DLV_USE_LODEPNG \
    -DLV_USE_DRAW_SW_COMPLEX_GRADIENTS \
    -DPYCPARSER \
    lvgl/lv_port_linux/lvgl/lvgl.h > lvgl.h

gcc -E -P -std=c99 -Ifake_libc_include \
    -DLV_USE_OS=5 -DLV_USE_WINDOWS -DLV_USE_LINUX_FBDEV -DLV_USE_EVDEV \
    -DLV_USE_FLEX -DLV_USE_GRID \
    -DLV_USE_QRCODE \
    -DLV_USE_TINY_TTF -DLV_TINY_TTF_FILE_SUPPORT \
    -DLV_USE_LODEPNG \
    -DLV_USE_DRAW_SW_COMPLEX_GRADIENTS \
    -DPYCPARSER \
    lvgl/lvgl/lvgl.h > lvgl.h
