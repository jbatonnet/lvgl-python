#!/bin/sh -x

# From a Windows machine:
#   docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
#   docker run --platform=linux/arm/v7 --rm -it -v .\:/work ghcr.io/jbatonnet/armv7-uclibc /work/build-lvgl-linux.sh /work/lvgl-arm-linux-uclibc.so

mkdir -p /tmp/lvgl
cd /tmp/lvgl

# Clone lvgl/lv_port_linux
git clone --single-branch --branch lvgl-python --depth 1 --recurse-submodules --shallow-submodules https://github.com/jbatonnet/lv_port_linux.git
cd lv_port_linux

# Build
make -j

# Retrieve output
cp -f /tmp/lvgl/lv_port_linux/build/bin/lvgl.so $1
