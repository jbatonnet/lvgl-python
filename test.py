import time
import lvgl as lv

# Load required imports
if lv.helpers.is_micropython():
    import uasyncio as asyncio
else:
    import asyncio


def init():
    lv.init()

    if lv.helpers.is_windows():
        disp = lv.windows_create_display('Rinkhals', 272, 480, 100, False, True)
        touch = lv.windows_acquire_pointer_indev(disp)
        touch.set_display(disp)

    elif lv.helpers.is_linux():
        disp = lv.linux_fbdev_create()
        lv.linux_fbdev_set_file(disp, '/dev/fb0')

        rot = lv.DISPLAY_ROTATION._270
        disp.set_rotation(rot)

        touch = lv.evdev_create(lv.INDEV_TYPE.POINTER, '/dev/input/event0')
        touch.set_display(disp)

        # TODO Fine-tune calibration
        TOUCH_MAX_X = 460
        TOUCH_MAX_Y = 25
        TOUCH_MIN_X = 25
        TOUCH_MIN_Y = 235

        lv.evdev_set_calibration(touch, TOUCH_MIN_X, TOUCH_MIN_Y, TOUCH_MAX_X, TOUCH_MAX_Y)

def layout():
    def event_callback(event):
        pass

    scr = lv.obj(None)

    style = lv.style()
    style.init()
    style.set_bg_color(lv.palette_lighten(lv.PALETTE.GREY, 1))

    btn = lv.button(scr)
    btn.add_style(style, 0)
    btn.align(lv.ALIGN.CENTER, 0, 0)
    btn.add_event_cb(event_callback, lv.EVENT_CODE.ALL, None)
    label = lv.label(btn)
    label.set_text('Hello Rinkhals!')

    minbtn = lv.button(scr)
    minbtn.align(lv.ALIGN.TOP_LEFT, 0, 0)
    minp = lv.label(minbtn)
    minp.set_text('0,0')

    maxbtn = lv.button(scr)
    maxbtn.align(lv.ALIGN.BOTTOM_RIGHT, 0, 0)
    maxp = lv.label(maxbtn)
    maxp.set_text('272,480')

    lv.screen_load(scr)
    
    while True:
        lv.tick_inc(20)
        lv.timer_handler()
        time.sleep(0.02)


def main():
    init()
    layout()

    while True:
        lv.tick_inc(20)
        lv.timer_handler()
        time.sleep(0.02)

if __name__ == "__main__":
    main()
