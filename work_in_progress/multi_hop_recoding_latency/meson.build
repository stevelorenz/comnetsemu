project('recoder_vnf', 'cpp',
  version : '0.1',
  default_options : ['warning_level=2', 'cpp_std=c++17'])

host_system = host_machine.system()

cppc = meson.get_compiler('cpp')

cpp_flags = [
    '-Wlogical-op',
    '-Werror=missing-include-dirs',
    '-Werror=pointer-arith',
    '-Werror=init-self',
    '-Wfloat-equal',
    '-Wsuggest-attribute=noreturn',
    '-Werror=return-type',
    '-Werror=format=2',
    '-Wimplicit-fallthrough=5',
    '-Wendif-labels',
    '-Wstrict-aliasing=3',
    '-Wwrite-strings',
    '-Werror=overflow',
    '-Werror=shift-count-overflow',
    '-Werror=shift-overflow=2',
    '-Wdate-time',
    '-Wunused',
    '-Wduplicated-branches',
    '-Wmisleading-indentation',

    '-Wno-sign-compare',
    '-Wno-unused-parameter',

    '-ffast-math',
    '-fdiagnostics-show-option',
    '-fstack-protector',
    '-fstack-protector-strong',
    '--param=ssp-buffer-size=4',

    '-Wno-deprecated-declarations',
    '-Wno-unused-value',
    '-Wno-unused-variable',
    '-Wno-unused-but-set-variable',
]

add_project_arguments(
    cpp_flags,
    language: 'cpp',
)


math_dep = cppc.find_library('m', required: true)

bpf_dep = dependency('libbpf', required: true)
dpdk_dep = dependency('libdpdk', required: true)
json_dep = dependency('jansson', required: true)
zmq_dep = dependency('libzmq', required: true)
ffpp_dep = dependency('libffpp', required: true)
kodo_rlnc_dep = dependency('libkodo_rlnc', required: true)

dep_list = [
  bpf_dep,
  dpdk_dep,
  json_dep,
  math_dep,
  zmq_dep,
  ffpp_dep,
  kodo_rlnc_dep,
]

all_deps = declare_dependency(
  dependencies: dep_list,
)


executable('client',
           'client.cpp',
           dependencies:all_deps,
           install : false)

executable('server',
           'server.cpp',
           dependencies:all_deps,
           install : false)

executable('recoder_vnf',
           'recoder_vnf.cpp',
           dependencies:all_deps,
           install : false)

executable('test_client',
           'test_client.cpp',
           dependencies:all_deps,
           install : false)

executable('test_server',
           'test_server.cpp',
           dependencies:all_deps,
           install : false)





message('\n'.join([
  '',
  '        Host system:                  ' + host_system,
  '        Source code location:         ' + meson.source_root(),
  '        CPP compiler:                 ' + cppc.get_id(),
  '        Debugging support:            ' + get_option('buildtype'),
  '',
]))
