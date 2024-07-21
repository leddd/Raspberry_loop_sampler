from pyo import *

inputs, outputs = pa_get_devices_infos()
print('- Inputs:')
for index in sorted(inputs.keys()):
     print('  Device index:', index)
     for key in ['name', 'host api index', 'default sr', 'latency']:
         print('    %s:' % key, inputs[index][key])
print('- Outputs:')
for index in sorted(outputs.keys()):
    print('  Device index:', index)
    for key in ['name', 'host api index', 'default sr', 'latency']:
        print('    %s:' % key, outputs[index][key])