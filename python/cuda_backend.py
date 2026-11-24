"""CUDA backend for solve.py: the CUDA driver API and NVRTC through ctypes.

No pip packages are needed. The driver library ships with the NVIDIA driver;
NVRTC comes from a CUDA toolkit (CUDA_PATH), the nvidia-cuda-nvrtc-cu12 wheel,
or the system library path. The kernel source is the OpenCL kernel, translated
by opencl_to_cuda(), so both backends run the same search.
"""
import ctypes
import glob
import os
import re
import sys

CU_DEVICE_ATTRIBUTE_MAX_THREADS_PER_BLOCK = 1
CU_DEVICE_ATTRIBUTE_MAX_SHARED_MEMORY_PER_BLOCK = 8
CU_DEVICE_ATTRIBUTE_CLOCK_RATE = 13
CU_DEVICE_ATTRIBUTE_MULTIPROCESSOR_COUNT = 16
CU_DEVICE_ATTRIBUTE_COMPUTE_CAPABILITY_MAJOR = 75
CU_DEVICE_ATTRIBUTE_COMPUTE_CAPABILITY_MINOR = 76
CU_DEVICE_ATTRIBUTE_MAX_SHARED_MEMORY_PER_MULTIPROCESSOR = 81
CU_DEVICE_ATTRIBUTE_MAX_SHARED_MEMORY_PER_BLOCK_OPTIN = 97
CU_FUNC_ATTRIBUTE_SHARED_SIZE_BYTES = 1
CU_FUNC_ATTRIBUTE_NUM_REGS = 4
CU_FUNC_ATTRIBUTE_MAX_DYNAMIC_SHARED_SIZE_BYTES = 8
CU_FUNC_ATTRIBUTE_PREFERRED_SHARED_MEMORY_CARVEOUT = 9


class CudaError(RuntimeError):
    pass


def _load_driver():
    names = ['nvcuda.dll'] if sys.platform == 'win32' else ['libcuda.so.1', 'libcuda.so']
    for n in names:
        try:
            return ctypes.CDLL(n)
        except OSError:
            pass
    raise CudaError('CUDA driver library not found (is an NVIDIA driver installed?)')


def _load_nvrtc():
    if sys.platform == 'win32':
        pattern, dirs = 'nvrtc64_*.dll', []
        if os.environ.get('CUDA_PATH'):
            dirs.append(os.path.join(os.environ['CUDA_PATH'], 'bin'))
        dirs += sorted(glob.glob(r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.*\bin'), reverse=True)
    else:
        pattern, dirs = 'libnvrtc.so*', []
        if os.environ.get('CUDA_PATH'):
            dirs.append(os.path.join(os.environ['CUDA_PATH'], 'lib64'))
        dirs += ['/usr/local/cuda/lib64']
    try:   # pip install nvidia-cuda-nvrtc-cu12
        import nvidia.cuda_nvrtc
        base = list(nvidia.cuda_nvrtc.__path__)[0]
        dirs.insert(0, os.path.join(base, 'bin' if sys.platform == 'win32' else 'lib'))
    except ImportError:
        pass
    if getattr(sys, 'frozen', False):
        dirs.insert(0, sys._MEIPASS)
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(d, pattern))):
            if 'builtins' in f or f.endswith('.alt.dll'):
                continue
            if sys.platform == 'win32':
                os.add_dll_directory(d)    # nvrtc loads nvrtc-builtins from here
            try:
                return ctypes.CDLL(f)
            except OSError:
                pass
    for n in (['nvrtc64_120_0.dll'] if sys.platform == 'win32' else ['libnvrtc.so.12', 'libnvrtc.so']):
        try:
            return ctypes.CDLL(n)
        except OSError:
            pass
    raise CudaError('NVRTC not found: install a CUDA 12 toolkit or `pip install nvidia-cuda-nvrtc-cu12`')


_cu = None


def _check(res, what):
    if res != 0:
        s = ctypes.c_char_p()
        _cu.cuGetErrorString(res, ctypes.byref(s))
        raise CudaError(f'{what} failed: {res} {s.value.decode() if s.value else ""}')


def _init():
    global _cu
    if _cu is None:
        _cu = _load_driver()
        _check(_cu.cuInit(0), 'cuInit')
    return _cu


def device_count():
    cu = _init()
    n = ctypes.c_int()
    _check(cu.cuDeviceGetCount(ctypes.byref(n)), 'cuDeviceGetCount')
    return n.value


class Device:
    """The subset of pyopencl.Device that solve.py uses."""
    def __init__(self, index):
        cu = _init()
        self.handle = ctypes.c_int()
        _check(cu.cuDeviceGet(ctypes.byref(self.handle), index), 'cuDeviceGet')
        buf = ctypes.create_string_buffer(256)
        _check(cu.cuDeviceGetName(buf, 256, self.handle), 'cuDeviceGetName')
        self.name = buf.value.decode()
        mem = ctypes.c_size_t()
        _check(cu.cuDeviceTotalMem_v2(ctypes.byref(mem), self.handle), 'cuDeviceTotalMem')
        self.global_mem_size = mem.value
        self.max_compute_units = self.attr(CU_DEVICE_ATTRIBUTE_MULTIPROCESSOR_COUNT)
        self.max_work_group_size = self.attr(CU_DEVICE_ATTRIBUTE_MAX_THREADS_PER_BLOCK)
        self.max_work_item_sizes = [self.max_work_group_size, 1, 1]
        self.max_clock_frequency = self.attr(CU_DEVICE_ATTRIBUTE_CLOCK_RATE) // 1000
        # what OpenCL reports as local memory: the default 48 KB per block
        self.local_mem_size = self.attr(CU_DEVICE_ATTRIBUTE_MAX_SHARED_MEMORY_PER_BLOCK)
        self.local_mem_size_optin = self.attr(CU_DEVICE_ATTRIBUTE_MAX_SHARED_MEMORY_PER_BLOCK_OPTIN)
        self.local_mem_per_cu = self.attr(CU_DEVICE_ATTRIBUTE_MAX_SHARED_MEMORY_PER_MULTIPROCESSOR)
        self.compute_capability = (self.attr(CU_DEVICE_ATTRIBUTE_COMPUTE_CAPABILITY_MAJOR),
                                   self.attr(CU_DEVICE_ATTRIBUTE_COMPUTE_CAPABILITY_MINOR))

    def attr(self, a):
        v = ctypes.c_int()
        _check(_cu.cuDeviceGetAttribute(ctypes.byref(v), a, self.handle), 'cuDeviceGetAttribute')
        return v.value


class Platform:
    name = 'CUDA'
    vendor = 'NVIDIA'

    def get_devices(self):
        return [Device(i) for i in range(device_count())]


# OpenCL C -> CUDA C++. The kernel only uses a small part of OpenCL C, which
# maps onto CUDA with these definitions plus two edits in opencl_to_cuda().
PRELUDE = r'''
typedef unsigned long long ulong;
typedef unsigned int uint;
typedef unsigned char uchar;
#define __kernel extern "C" __global__
#define __global
#define __constant __constant__
#define __local __shared__
#define local      /* solve.py's KMEMTYPE: a pointer into shared memory needs no qualifier */
#define get_local_id(d) ((int)threadIdx.x)
#define get_global_id(d) ((int)(blockIdx.x*blockDim.x + threadIdx.x))
#define get_local_size(d) ((int)blockDim.x)
#define get_group_id(d) ((int)blockIdx.x)
#define barrier(f) __syncthreads()
#define atomic_inc(p) atomicAdd((p), 1)
'''


def opencl_to_cuda(src):
    src = '\n'.join(l for l in src.splitlines() if not l.startswith('#pragma OPENCL'))
    # the per-worker stacks become the block's dynamic shared memory
    m = re.search(r'__local (\w+) \*localbuf,', src)
    assert m, 'kernel has no __local localbuf argument'
    src = src.replace(m.group(0), '')
    src = f'extern __shared__ {m.group(1)} localbuf[];\n' + src
    # unsigned long is 32 bits on Windows; the used-piece masks need 64
    src = src.replace('1UL <<', '1ULL <<')
    return PRELUDE + src


class Gpu:
    """Context, kernel and buffers for one device: the operations solve.py's
    search loop needs, with the same meaning as its OpenCL code."""
    def __init__(self, device):
        cu = _init()
        self.device = device
        self.ctx = ctypes.c_void_p()
        _check(cu.cuDevicePrimaryCtxRetain(ctypes.byref(self.ctx), device.handle), 'cuDevicePrimaryCtxRetain')
        _check(cu.cuCtxSetCurrent(self.ctx), 'cuCtxSetCurrent')
        self.func = None

    def build(self, opencl_src, kernel_name='mykernel'):
        nvrtc = _load_nvrtc()
        src = opencl_to_cuda(opencl_src).encode()
        prog = ctypes.c_void_p()
        r = nvrtc.nvrtcCreateProgram(ctypes.byref(prog), src, b'kernel.cu', 0, None, None)
        if r:
            raise CudaError(f'nvrtcCreateProgram failed: {r}')
        major, minor = self.device.compute_capability
        # -lineinfo lets Nsight Compute map SASS to source lines; it doesn't change the code
        opts = [f'--gpu-architecture=sm_{major}{minor}'.encode(), b'-default-device', b'--std=c++14',
                b'-lineinfo']
        copts = (ctypes.c_char_p * len(opts))(*opts)
        r = nvrtc.nvrtcCompileProgram(prog, len(opts), copts)
        logsize = ctypes.c_size_t()
        nvrtc.nvrtcGetProgramLogSize(prog, ctypes.byref(logsize))
        log = ctypes.create_string_buffer(logsize.value)
        nvrtc.nvrtcGetProgramLog(prog, log)
        if r:
            raise CudaError('NVRTC compile failed:\n' + log.value.decode(errors='replace'))
        # SASS for this exact GPU: no PTX JIT, so an older driver isn't a problem
        size = ctypes.c_size_t()
        if nvrtc.nvrtcGetCUBINSize(prog, ctypes.byref(size)):
            raise CudaError('nvrtcGetCUBINSize failed')
        self.cubin = ctypes.create_string_buffer(size.value)
        nvrtc.nvrtcGetCUBIN(prog, self.cubin)
        nvrtc.nvrtcDestroyProgram(ctypes.byref(prog))
        self.module = ctypes.c_void_p()
        _check(_cu.cuModuleLoadData(ctypes.byref(self.module), self.cubin), 'cuModuleLoadData')
        self.func = ctypes.c_void_p()
        _check(_cu.cuModuleGetFunction(ctypes.byref(self.func), self.module, kernel_name.encode()),
               'cuModuleGetFunction')
        # allow dynamic shared memory up to the opt-in limit, and prefer shared
        # memory over L1 in the carveout
        self.static_local = self.func_attr(CU_FUNC_ATTRIBUTE_SHARED_SIZE_BYTES)
        _check(_cu.cuFuncSetAttribute(self.func, CU_FUNC_ATTRIBUTE_MAX_DYNAMIC_SHARED_SIZE_BYTES,
                                      self.device.local_mem_size_optin - self.static_local),
               'cuFuncSetAttribute(max dynamic shared)')
        _check(_cu.cuFuncSetAttribute(self.func, CU_FUNC_ATTRIBUTE_PREFERRED_SHARED_MEMORY_CARVEOUT, 100),
               'cuFuncSetAttribute(carveout)')
        self.num_regs = self.func_attr(CU_FUNC_ATTRIBUTE_NUM_REGS)

    def func_attr(self, a):
        v = ctypes.c_int()
        _check(_cu.cuFuncGetAttribute(ctypes.byref(v), a, self.func), 'cuFuncGetAttribute')
        return v.value

    def buffer(self, hostbuf=None, nbytes=None):
        nbytes = hostbuf.nbytes if hostbuf is not None else nbytes
        ptr = ctypes.c_uint64()
        _check(_cu.cuMemAlloc_v2(ctypes.byref(ptr), max(1, nbytes)), 'cuMemAlloc')
        if hostbuf is not None:
            self.write(ptr, hostbuf)
        return ptr

    def free(self, buf):
        _check(_cu.cuMemFree_v2(buf), 'cuMemFree')

    def write(self, buf, arr):
        _check(_cu.cuMemcpyHtoD_v2(buf, arr.ctypes.data_as(ctypes.c_void_p), ctypes.c_size_t(arr.nbytes)),
               'cuMemcpyHtoD')

    def read(self, buf, arr):
        _check(_cu.cuMemcpyDtoH_v2(arr.ctypes.data_as(ctypes.c_void_p), buf, ctypes.c_size_t(arr.nbytes)),
               'cuMemcpyDtoH')

    def launch(self, nglobal, nlocal, args, shared_bytes):
        """args: device buffers (from buffer()) and numpy int32 scalars, in order."""
        holders = []
        for a in args:
            holders.append(a if isinstance(a, ctypes.c_uint64) else ctypes.c_int32(int(a)))
        argv = (ctypes.c_void_p * len(holders))(*[ctypes.cast(ctypes.byref(h), ctypes.c_void_p) for h in holders])
        _check(_cu.cuLaunchKernel(self.func, nglobal // nlocal, 1, 1, nlocal, 1, 1,
                                  ctypes.c_uint(shared_bytes), None, argv, None), 'cuLaunchKernel')
