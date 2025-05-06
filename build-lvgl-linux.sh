#!/bin/sh -x

# From a Windows machine:
#   docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
#   docker run --platform=linux/arm/v7 --rm -it -v .\:/work ghcr.io/jbatonnet/armv7-uclibc /work/build-lvgl-linux.sh /work/lvgl-arm-linux-uclibc.so

CWD=$(pwd)
BUILD_PATH=/tmp/lvgl-python/build
TARGET_PATH=$1

mkdir -p $BUILD_PATH
rm -rf $BUILD_PATH/*
cd $BUILD_PATH


# Clone lvgl/lv_port_linux
git clone --single-branch --branch lvgl-python --depth 1 --recurse-submodules --shallow-submodules https://github.com/jbatonnet/lv_port_linux.git
cd lv_port_linux

# Build
make -j

# Retrieve output
cp -f build/bin/liblvgl.so $TARGET_PATH

# Generate header file
cd $CWD
gcc -E -std=c99 -Ifake_libc_include -DPYCPARSER $BUILD_PATH/lv_port_linux/lvgl/lvgl.h > $(dirname $TARGET_PATH)/lvgl.h
