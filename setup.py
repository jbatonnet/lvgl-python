from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
import subprocess
import os
import platform

class CustomBuildExt(build_ext):
    def run(self):
        # Check if the platform is armv7
        if platform.machine() != "armv7l":
            raise RuntimeError("This build process is only supported on armv7 platforms.")
        
        # Check if the platform is Windows
        if platform.system() == "Windows":
            build_script = os.path.join(os.getcwd(), "build-lvgl-windows.bat")
            output_path = os.path.join(os.getcwd(), "lvgl-windows.dll")
            subprocess.check_call([build_script, output_path])
            return
        
        # Run the Docker command from the shell script
        build_script = os.path.join(os.getcwd(), "build-lvgl-linux.sh")
        output_path = os.path.join(os.getcwd(), "lvgl-arm-linux-uclibc.so")
        subprocess.check_call([build_script, output_path])

        # Run the generate-header.sh script to produce lvgl.h
        generate_header_script = os.path.join(os.getcwd(), "generate-header.sh")
        subprocess.check_call(["sh", generate_header_script])

        # Run the generate-python.py script to produce the Python wrapper
        generate_python_script = os.path.join(os.getcwd(), "generate-python.py")
        subprocess.check_call(["python", generate_python_script])

        super().run()

# Define the C extension
lvgl_extension = Extension(
    "lvgl",  # Module name
    sources=[],  # No direct sources; built via the Docker process
    libraries=[],  # Add any required libraries here
)

# Setup configuration
setup(
    name="lvgl-python",
    version="0.1.0",
    description="Python bindings for LVGL with prebuilt C library",
    author="Julien Batonnet",
    author_email="julien.batonnet@gmail.com",
    url="https://github.com/jbatonnet/lvgl-python",
    ext_modules=[lvgl_extension],
    cmdclass={"build_ext": CustomBuildExt},
    packages=["lvgl_python"],  # Replace with your actual Python package(s)
    package_data={
        "lvgl_python": ["lvgl-arm-linux-uclibc.so", "lvgl.py"],  # Include the shared library and generated Python file
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Other OS",  # Indicate non-standard OS/platform
        "Environment :: Embedded Systems",  # Optional: Indicate embedded systems
    ],
    python_requires=">=3.6",
    install_requires=[
        "cffi",  # Required for loading the shared library
    ],
)