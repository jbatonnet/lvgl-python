import os
import sys
import subprocess
from setuptools import setup, Extension, find_packages
from setuptools.command.build_ext import build_ext  # Import build_ext
from setuptools.command.install import install  # Import install
from distutils.spawn import find_executable
import shutil
from pathlib import Path
import logging  # Import the logging module


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Source paths
if sys.platform.startswith("linux"):
    SOURCE_DIR = os.path.join(ROOT_DIR, 'lvgl', 'lv_port_linux')
    LVGL_SOURCE_DIR = os.path.join(SOURCE_DIR, 'lvgl')
elif sys.platform.startswith("win"):
    SOURCE_DIR = os.path.join(ROOT_DIR, 'lvgl', 'lv_port_pc_visual_studio')
    LVGL_SOURCE_DIR = os.path.join(SOURCE_DIR, 'LvglPlatform', 'lvgl')

LVGL_HEADER_PATH = os.path.join(LVGL_SOURCE_DIR, 'lvgl.h')

# Build paths
if sys.platform.startswith("linux"):
    BUILD_COMMAND = [ 'make', '-j' ]
    LIBRARY_NAME = 'liblvgl.so'
    BUILD_OUTPUT = os.path.join(SOURCE_DIR, 'build', 'bin', LIBRARY_NAME)
elif sys.platform.startswith("win"):
    BUILD_COMMAND = [ 'BuildAllTargets.cmd' ]
    LIBRARY_NAME = 'LvglWindows.dll'
    BUILD_OUTPUT = os.path.join(SOURCE_DIR, 'Output', 'Binaries', 'Release', 'Win32' if sys.maxsize <= 2**32 else 'x64', LIBRARY_NAME)

BUILD_DIR = os.path.join(ROOT_DIR, 'build')
PREPROCESSED_HEADER_FILE = os.path.join(BUILD_DIR, 'lvgl_preprocessed.h')
DUMMY_C_FILE = os.path.join(BUILD_DIR, 'dummy.c')

# Package paths
PACKAGE_DIR = os.path.join(BUILD_DIR, 'lvgl_python')

PACKAGE_PYTHON_PATH = os.path.join(PACKAGE_DIR, 'lvgl.py')

if sys.platform.startswith("linux"):
    PACKAGE_LIBRARY_PATH = os.path.join(PACKAGE_DIR, 'liblvgl.so')
elif sys.platform.startswith("win"):
    PACKAGE_LIBRARY_PATH = os.path.join(PACKAGE_DIR, 'lvgl.dll')

# Dist paths
DIST_DIR = os.path.join(ROOT_DIR, 'dist')




LYGL_PYTHON_FILE = os.path.join(BUILD_DIR, 'lvgl.py')
GENERATE_PYTHON_FILE = os.path.join(ROOT_DIR, 'generate-python.py')

os.makedirs(BUILD_DIR, exist_ok=True)
os.makedirs(DIST_DIR, exist_ok=True)
os.makedirs(PACKAGE_DIR, exist_ok=True)




# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        # logging.FileHandler("setup.log"),
    ],
)
logger = logging.getLogger(__name__)


def check_executable(executable):
    """Checks if an executable is in the system's PATH."""
    if not find_executable(executable):
        raise RuntimeError(f"{executable} is required to build this package, but is not in PATH")

def build_lvgl_library():
    subprocess.run(BUILD_COMMAND, cwd=SOURCE_DIR, check=True, shell=True)

    if not os.path.exists(BUILD_OUTPUT):
        raise RuntimeError(f"Error: Could not find the library file at {BUILD_OUTPUT}.  Check your Makefile and build process.  Expected output: {LIBRARY_NAME}")

def preprocess_lvgl_header():
    if not os.path.exists(LVGL_HEADER_PATH):
        raise RuntimeError(f"Header file not found at {LVGL_HEADER_PATH}")

    logger.info(f"Preprocessing LVGL header: {LVGL_HEADER_PATH} -> {PREPROCESSED_HEADER_FILE}")
    try:
        if sys.platform.startswith("linux"):
            subprocess.run(
            ["gcc", "-E", "-P", '-std=c99', "-DPYCPARSER", "-Ifake_libc_include", LVGL_HEADER_PATH, "-o", PREPROCESSED_HEADER_FILE],
            check=True,
            )
        # elif sys.platform.startswith("win"):
        #     subprocess.run(
        #     ["cl", "/EP", "/DPYCPARSER", f"/I{os.path.join(ROOT_DIR, 'fake_libc_include')}", LVGL_HEADER_PATH, f"/Fo{PREPROCESSED_HEADER_FILE}"],
        #     check=True,
        #     shell=True,
        #     )
    except subprocess.CalledProcessError as e:
        logger.error(f"Error preprocessing LVGL header: {e}")
        raise RuntimeError(f"Error preprocessing LVGL header: {e}")
    
    if not os.path.exists(PREPROCESSED_HEADER_FILE):
        raise RuntimeError(f"Error: Could not find the .h file at {PREPROCESSED_HEADER_FILE}")

def generate_python_wrapper():
    if not os.path.exists(PREPROCESSED_HEADER_FILE):
        raise RuntimeError(f"Preprocessed header file not found at {PREPROCESSED_HEADER_FILE}")
    if not os.path.exists(GENERATE_PYTHON_FILE):
        raise RuntimeError(f"generate-python.py script not found at {GENERATE_PYTHON_FILE}")

    try:
        #  Execute the generate-python.py script.
        subprocess.run([sys.executable, GENERATE_PYTHON_FILE, PREPROCESSED_HEADER_FILE, LYGL_PYTHON_FILE], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error generating Python wrapper: {e}")
        raise RuntimeError(f"Error generating Python wrapper: {e}")
    
    if not os.path.exists(LYGL_PYTHON_FILE):
        raise RuntimeError(f"Error: Could not find the .py file at {LYGL_PYTHON_FILE}")


class CustomBuildExt(build_ext):

    def run(self):
        # Check for required executables
        if sys.platform.startswith("linux"):
            check_executable("make")
            check_executable("gcc")

        try:
            # 1. Build the LVGL library using the Makefile.
            logger.info("Step 1: Building LVGL library with Makefile...")
            #build_lvgl_library()
            logger.info(f"LVGL library built successfully: {BUILD_OUTPUT}")

            # 2.  Preprocess the LVGL header.
            logger.info("Step 2: Preprocessing LVGL header...")
            preprocess_lvgl_header()
            logger.info(f"LVGL header preprocessing complete: {PREPROCESSED_HEADER_FILE}")

            # 3. Generate the Python wrapper.
            logger.info("Step 3: Generating Python wrapper...")
            generate_python_wrapper()
            logger.info("Python wrapper generation complete.")

            # 4. Preparing the package directory.
            logger.info("Step 4: Preparing the package directory...")
            shutil.copy(BUILD_OUTPUT, PACKAGE_LIBRARY_PATH)
            shutil.copy(LYGL_PYTHON_FILE, PACKAGE_PYTHON_PATH)
            logger.info("Package directory preparation complete.")

            # 5. Create a dummy extension.
            logger.info("Step 5: Creating a dummy extension...")
            if not os.path.exists(DUMMY_C_FILE):
                with open(DUMMY_C_FILE, 'w') as f:
                    f.write('void dummy(void){}')
            self.extensions = [
                Extension(
                    "lvgl_python._native",  # Extension name
                    [DUMMY_C_FILE],  # Source file
                    libraries=['lvgl'],
                )
            ]

            # self.extensions = [
            #     Extension(
            #         "lvgl_python._native",
            #         sources=[os.path.join(ROOT_DIR, "dummy.c")],
            #         include_dirs=[PACKAGE_DIR],
            #         library_dirs=[PACKAGE_DIR],
            #         libraries=['lvgl'],
            #         extra_compile_args=["-fPIC"],
            #     )
            # ]

            self.swig_opts = ""

            super().finalize_options()
            super().run()
            logger.info("Dummy extension creation and build_ext execution complete.")

        except Exception as e:
            logger.error(f"Exception during build process: {e}")
            raise

    def copy_extensions_to_source(self):
        """This is a workaround."""
        return



class CustomInstall(install):
    """Custom install command."""

    def run(self):
        super().run()
        logger.info("Running post-installation steps...")
        logger.info("Installation complete!")



def read_long_description(filename="README.md"):
    """Reads the contents of a README file."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""



# Setup
setup(
    name="lvgl_python",
    version="0.1.0",
    author="Julien Batonnet",
    author_email="julien.batonnet@gmail.com",
    description="Python bindings for the LVGL graphics library",
    long_description=read_long_description(),
    long_description_content_type="text/markdown",
    url="https://github.com/jbatonnet/lvgl-python",
    packages=find_packages(),
    include_package_data=True,
    package_data={"my_package": ["*.so"], },
    ext_modules=[],
    install_requires=[
        "cffi",
    ],
    cmdclass={  # Use the imported classes here
        "build_ext": CustomBuildExt,
        "install": CustomInstall,
    },
    zip_safe=False,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: C++",
    ],
)
