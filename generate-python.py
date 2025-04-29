import re
import cffi

import pycparser
from pycparser.c_ast import *
import sys

def main():

    # Pregenerate CFFI backend
    ffibuilder = cffi.FFI()
    ffibuilder.set_source('lvgl_ffi', None)
    
    if __debug__:
        #sys.argv.append('build/lvgl_preprocessed.h')
        #sys.argv.append('build/lvgl_python/lvgl.py')
        sys.argv.append('lvgl.h')
        sys.argv.append('lvgl.py')

    if len(sys.argv) < 3:
        print('Usage: python generate-python.py <path_to_lvgl.h> <path_to_generated_lvgl.py>')
        sys.exit(1)

    lvgl_header_path = sys.argv[1]
    with open(lvgl_header_path, 'r') as l:
        lvgl_header = l.read()

    lvgl_header = re.sub('[\r\n]+(inline )?static[\S\s]*?[\r\n]+\{[\S\s]*?[\r\n]+\}', '\n', lvgl_header)
    lvgl_header = re.sub(',\s*\n+', ',', lvgl_header)
    lvgl_header = lvgl_header.replace('void lv_span_set_text_static(lv_span_t * span, const char * text);', '', 1)

    lvgl_header_lines = lvgl_header.splitlines()
    lvgl_header_lines = [ l for l in lvgl_header_lines if l.strip() and not l.startswith('#') ]
    lvgl_header_lines = [ l for l in lvgl_header_lines if not l.startswith('typedef int ') and not 'va_list' in l and not '...' in l ]

    lvgl_header = '\n'.join(lvgl_header_lines)

    ffibuilder.cdef(lvgl_header)
    ffiBackendFile = ffibuilder.compile()

    with open(ffiBackendFile, 'r') as ffiBackend:
        content = ffiBackend.read()
        content = content.replace('# auto-generated file', '')
        content = content.replace('import _cffi_backend', '')
        content = content.replace('\n', ' ')
        content = content.replace('ffi = ', '')
        ffiBackendContent = content.strip()

    ast = pycparser.parse_file('lvgl.h')
    #ast.show(showcoord=True)

    insertTimingLog = False

    # Deny lists
    enumsDenyList = [
    ]
    functionsDenyList = [
        # Func pointer
        'lv_ll_*',
        'lv_utils_bsearch',
        'lv_thread_*',

        # Useless
        'lv_snprintf',
        'lv_vsnprintf',
        'lv_str*',
        'lv_mem*',
        'lv_free', 'lv_free_core',
        'lv_*alloc*',
        'lv_fs_*',
        'lv_trigo_*',
        'lv_delay_*',
        'lv_sqr', 'lv_map', 'lv_pow', 'lv_sqrt32', 'lv_sqrt', 'lv_atan2',
        'lv_rand*',
    ]
    structsDenyList = [
        'lv_color*_t'
    ]
    callbackDenyList = [
    ]

    # Extract all the interesting nodes
    all = [ n for n in ast.ext if 'fake_libc_include' not in n.coord.file or 'fake_libc_include/..' in n.coord.file ]

    def inList(name, allowList):
        return any(re.match(f'^{n.replace("*", ".*")}$', name) for n in allowList)

    enumNodes1 = [ [ '', n.type ] for n in all if isinstance(n, Decl) and isinstance(n.type, Enum) ]
    enumNodes2 = [ [ n.type.declname, n.type.type ] for n in all if isinstance(n, Typedef) and isinstance(n.type.type, Enum) ]
    enumNodes = enumNodes1 + enumNodes2
    enumNodes = [ n for n in enumNodes if not inList(n[0], enumsDenyList) ]

    functionNodes1 = [ [ n.name, n.type ] for n in all if isinstance(n, Decl) and isinstance(n.type, FuncDecl) ]
    functionNodes2 = [ [ n.decl.name, n.decl.type ] for n in all if isinstance(n, FuncDef) ]
    functionNodes = functionNodes1 + functionNodes2
    functionNodes = [ n for n in functionNodes if not inList(n[0], functionsDenyList) ]
    functionNodes = dict(functionNodes)

    structNodes = [ [ n.type.declname, n.type.type ] for n in all if isinstance(n, Typedef) and isinstance(n.type.type, Struct) ]
    structNodes = [ n for n in structNodes if not inList(n[0], structsDenyList) ]
    structNodes.sort(reverse=True, key=lambda n: n[0][:-2] if n[0] != 'lv_obj_t' else 'zzz')
    structNodes = dict(structNodes)

    callbackNodes = [ n for n in all if isinstance(n, Typedef) and isinstance(n.type, PtrDecl) and isinstance(n.type.type, FuncDecl) ]
    callbackNodes = { n.name: n for n in callbackNodes if not inList(n.name, callbackDenyList) }

    typeDefs = { s.name: n for n, s in structNodes.items() if s.name }
    typeDefs['lv_style_selector_t'] = 'lv_state_t'

    # Helper functions
    def getNodeName(node):
        if isinstance(node, TypeDecl):
            return node.declname
        if isinstance(node, IdentifierType):
            return node.names[0]
        if isinstance(node, PtrDecl):
            return getNodeName(node.type)
        if isinstance(node, Struct):
            return node.name
        return None
    def getNodeType(node):
        if isinstance(node, str):
            if node == 'void':
                return 'None'
            if node == 'char' or node == 'wchar_t':
                return 'str'
            if node == 'uint8_t' or node == 'int8_t' or node == 'uint16_t' or node == 'int16_t' or node == 'uint32_t' or node == 'int32_t':
                return 'int'
            return typeDefs.get(node) or node
        if isinstance(node, IdentifierType):
            return getNodeType(node.names[0])
        if isinstance(node, TypeDecl):
            return getNodeType(node.type)
        if isinstance(node, PtrDecl):
            return getNodeType(node.type)
        if isinstance(node, Struct):
            return typeDefs.get(node.name, node.name)
        if isinstance(node, ArrayDecl):
            return getNodeType(node.type)
        return None
    def getParams(params):
        results = []

        usedNames = []

        for param in params:
            p = lambda: None
            p.name = param.name
            p.c_type = getCNodeType(param.type)
            p.python_type = getNodeType(param.type)
            p.type_hint = p.python_type
            p.lines = ''

            if not p.name and p.c_type == 'void':
                continue

            if not param.name:
                baseName = p.python_type.replace('lv_', '')[0]
                for i in range(0, 99):
                    if baseName + str(i) not in usedNames:
                        p.name = baseName + str(i)
                        break

            usedNames.append(p.name)

            if p.name == 'user_data' and p.c_type == 'void*':
                p.type_hint = 'str'
                p.lines += 'if user_data is not None:\n'
                p.lines += '    user_data = user_data.encode(\'utf-8\') + b\'\\x00\'\n'
                p.lines += '    user_data = ffi.from_buffer(user_data)\n'
                p.lines += '    self._user_data.append(user_data)\n'
                p.usage = 'ffi.NULL if user_data is None else user_data'
            elif p.c_type[-1:] == '*' and p.c_type[:-1] in structNodes:
                p.usage = f'{p.name}._pointer if {p.name} else ffi.NULL'
                p.type_hint = p.type_hint[3:-2]
            elif p.c_type in [ n[0] for n in enumNodes ]:
                p.usage = f'{p.name}.value if {p.name} and isinstance({p.name}, Enum) else ({p.name} or 0)'
                p.type_hint = p.type_hint[3:-2].upper()
            elif p.c_type in callbackNodes:
                callbackNode = callbackNodes[p.c_type]
                callbackReturnType = getCNodeType(callbackNode.type.type.type)
                callbackParams = getParams(callbackNode.type.type.args.params)
                returnKeyword = '' if callbackReturnType == 'void' else 'return '

                p.lines += f'def wrap_{p.name}(original_{p.name}):\n'
                p.lines += f'    def {p.name}({", ".join(["_" + cp.name for cp in callbackParams])}):\n'
                for cp in callbackParams:
                    if cp.c_type[-1:] == '*' and cp.c_type[:-1] in structNodes:
                        p.lines += f'        {cp.name} = {cp.python_type[3:-2]}.__new__({cp.python_type[3:-2]})\n'
                        p.lines += f'        {cp.name}._pointer = _{cp.name}\n'
                    else:
                        p.lines += f'        {cp.name} = _{cp.name}\n'
                p.lines += f'        {returnKeyword}original_{p.name}({", ".join([cp.name for cp in callbackParams])})\n'
                p.lines += f'    return ffi.callback(\'{callbackReturnType} (*)({", ".join([cp.c_type for cp in callbackParams])})\', {p.name})\n'
                p.lines += f'if isinstance({p.name}, ffi.CData):\n'
                p.lines += f'    {p.name}_wrapper = {p.name}\n'
                p.lines += f'else:\n'
                p.lines += f'    {p.name}_wrapper = self._callbacks.get({p.name})\n'
                p.lines += f'if not {p.name}_wrapper:\n'
                p.lines += f'    {p.name}_wrapper = wrap_{p.name}({p.name})\n'
                p.lines += f'    self._callbacks[{p.name}] = {p.name}_wrapper\n'

                p.usage = f'{p.name}_wrapper'
            elif p.c_type == 'char*':# or p.c_type == 'wchar_t*':
                p.usage = f'{p.name}.encode(\'utf-8\')'
            elif p.c_type[-1:] == '*' or p.c_type[-2:] == '[]':
                p.usage = f'ffi.NULL if {p.name} is None else {p.name}'
            else:
                p.usage = p.name

            results.append(p)

        return results
    def getReturnInfo(node):
        result = lambda: None
        result.c_type = getCNodeType(node)
        result.python_type = getNodeType(node)
        result.type_hint = p.python_type
        result.lines = None
        
        if result.c_type == 'char*':
            p.lines = 'result.decode(\'utf-8\')'
        
        return result
    def getCNodeType(node):
        if isinstance(node, str):
            if node == 'HWND':
                return 'void*'
            return typeDefs.get(node) or node
        if isinstance(node, IdentifierType):
            return getCNodeType(node.names[0])
        if isinstance(node, TypeDecl):
            return getCNodeType(node.type)
        if isinstance(node, PtrDecl):
            return getCNodeType(node.type) + '*'
        if isinstance(node, Struct):
            return typeDefs.get(node.name, node.name)
        if isinstance(node, ArrayDecl):
            return getCNodeType(node.type) + '[]'
        return None

    # Prepare output file
    lvgl_python_path = sys.argv[2]
    with open(lvgl_python_path, 'w') as out:

        # Write template and imports
        with open('lvgl_template.py', 'r') as template:
            out.write(template.read())
            out.write('\n')

        if insertTimingLog:
            out.write('import time\n')
            out.write('start = time.time()\n')
            out.write('\n')

        out.write('# Load the library\n')
        out.write('if _is_micropython:\n')
        out.write('    import ffi\n')
        out.write('    _lvgl = ffi.open(_library_path)\n')
        out.write('else:\n')
        out.write('    import _cffi_backend\n')
        out.write('    ffi = eval("' + ffiBackendContent.replace('\\', '\\\\') + '")\n')
        #out.write('    ffi = ' + ffiBackendContent + '\n')
        out.write('    _lvgl = ffi.dlopen(_library_path)\n')
        out.write('\n')

        if insertTimingLog:
            out.write('print(f"CFFI backend: {time.time() - start:.2f}s")\n')
            out.write('\n')

        # Enums
        out.write('\n')
        out.write('################\n')
        out.write('# Enums\n')
        out.write('\n')
        out.write('from enum import Enum\n')
        out.write('\n')

        if insertTimingLog:
            out.write('start = time.time()\n')
            out.write('\n')

        enumValues = {}
        def getEnumValue(value):
            if isinstance(value, Constant):
                return eval(value.value.strip('LU'))
            if isinstance(value, ID):
                return enumValues.get(value.name, value.name)
            if isinstance(value, BinaryOp):
                return eval(f'\n{getEnumValue(value.left)} {value.op} {getEnumValue(value.right)}')
            raise Exception('Unsupported enum value')
        
        enumValuePrefixes = [
            'LV_EVENT_',
            'LV_SCR_LOAD_ANIM_',
            'LV_OBJ_TREE_WALK_',
            'LV_FS_SEEK_',
            'LV_INDEV_GESTURE_',
            'LV_FONT_FMT_TXT_CMAP_',
            'LV_FONT_FMT_',
            'LV_MENU_HEADER_',
            'LV_MENU_ROOT_BACK_BUTTON_'
        ]

        enumClassPrefixes = [
            'LV_OPA',
            'LV_STATE',
            'LV_PART',
            'LV_STYLE',
            'LV_STR_SYMBOL',
            'LV_TREE_WALK',
        ]

        for enumNode in enumNodes:
            enumName = enumNode[0]
            enum = enumNode[1]

            for prefix in enumClassPrefixes:
                if not enumName and list(enum.values)[0].name.startswith(prefix):
                    enumName = prefix.lower() + '_t'
                    break

            if enumName:
                out.write(f'class {enumName[3:-2].upper()}(Enum):\n')

            last_value = -1
            for v in enum.values:
                if v.value:
                    last_value = getEnumValue(v.value)
                else:
                    last_value = last_value + 1

                enumValues[v.name] = last_value

                name = v.name
                if enumName:
                    name = name.replace(enumName[:-2].upper() + '_', '')
                else:
                    name = name[3:]
                if name[0].isdigit():
                    name = '_' + name
                for p in enumValuePrefixes:
                    name = name.replace(p, '')

                if enumName:
                    out.write('    ')
                out.write(f'{name} = {last_value}\n')

            out.write(f'\n')

        for prefix in enumClassPrefixes:
            enumNodes.append([prefix.lower() + '_t', None])

        LV_COORD_TYPE_SHIFT = 29
        LV_COORD_MAX = (1 << LV_COORD_TYPE_SHIFT) - 1
        LV_COORD_TYPE_SPEC = 1 << LV_COORD_TYPE_SHIFT
        LV_SIZE_CONTENT = LV_COORD_MAX | LV_COORD_TYPE_SPEC

        out.write(f'SIZE_CONTENT = {LV_SIZE_CONTENT}\n')
        out.write(f'\n')

        if insertTimingLog:
            out.write('print(f"Enums: {time.time() - start:.2f}s")\n')
            out.write('\n')

        # Structures
        out.write('\n')
        out.write('################\n')
        out.write('# Structures\n')
        out.write('\n')
        out.write('_objects = {}')
        out.write('\n')

        if insertTimingLog:
            out.write('start = time.time()\n')
            out.write('\n')

        classMethodNodes = {}

        for structName, structNode in structNodes.items():
            if structName.startswith('lv_color'):
                continue

            memberPrefix = structName[:-1]
            
            if structName == 'lv_grad_dsc_t':
                memberPrefix = 'lv_grad_'

            memberNodes = [ [ n, f ] for n, f in functionNodes.items() if n.startswith(memberPrefix) and n not in classMethodNodes ]
            memberNodes = [ [ n, f ] for n, f in memberNodes if isinstance(f.args.params[0].type, PtrDecl) ]
            memberNodes = dict(memberNodes)

            if structName == 'lv_theme_t':
                memberNodes = { n: m for n, m in memberNodes.items() if not n.startswith('lv_theme_default') }
                memberNodes = { n: m for n, m in memberNodes.items() if not n.startswith('lv_theme_mono') }
                memberNodes = { n: m for n, m in memberNodes.items() if not n.startswith('lv_theme_simple') }
                del memberNodes['lv_theme_get_from_obj']

            if structName == 'lv_anim_t':
                memberNodes = { n: m for n, m in memberNodes.items() if not n.startswith('lv_anim_path_') }
                
            for memberName, memberNode in memberNodes.items(): 
                classMethodNodes[memberName] = memberNode

            ctor = memberNodes.get(f'{structName[:-1]}create')
            ctorType = getCNodeType(ctor.type).strip('*') if ctor else None

            init = memberNodes.get(f'{structName[:-1]}init')

            if ctorType and ctorType != structName:
                out.write(f'class {structName[3:-2]}({ctorType[3:-2]}):\n')
            else:
                out.write(f'class {structName[3:-2]}:\n')

            out.write(f'    _pointer = None\n')
            out.write(f'    _callbacks = {{}}\n')
            out.write(f'    _user_data = []\n')
            out.write(f'\n')

            if structName == 'lv_style_t':
                out.write(f'    def set_size(self, width, height):\n')
                out.write(f'        self.set_width(width)\n')
                out.write(f'        self.set_height(height)\n')
                out.write(f'    def set_pad_all(self, value):\n')
                out.write(f'        self.set_pad_left(value)\n')
                out.write(f'        self.set_pad_right(value)\n')
                out.write(f'        self.set_pad_top(value)\n')
                out.write(f'        self.set_pad_bottom(value)\n')
                out.write(f'    def set_pad_hor(self, value):\n')
                out.write(f'        self.set_pad_left(value)\n')
                out.write(f'        self.set_pad_right(value)\n')
                out.write(f'    def set_pad_ver(self, value):\n')
                out.write(f'        self.set_pad_top(value)\n')
                out.write(f'        self.set_pad_bottom(value)\n')
                out.write(f'    def set_pad_gap(self, value):\n')
                out.write(f'        self.set_pad_row(value)\n')
                out.write(f'        self.set_pad_column(value)\n')
                out.write(f'    def set_margin_hor(self, value):\n')
                out.write(f'        self.set_margin_left(value)\n')
                out.write(f'        self.set_margin_right(value)\n')
                out.write(f'    def set_margin_ver(self, value):\n')
                out.write(f'        self.set_margin_top(value)\n')
                out.write(f'        self.set_margin_bottom(value)\n')
                out.write(f'    def set_margin_all(self, value):\n')
                out.write(f'        self.set_margin_left(value)\n')
                out.write(f'        self.set_margin_right(value)\n')
                out.write(f'        self.set_margin_top(value)\n')
                out.write(f'        self.set_margin_bottom(value)\n')
                out.write(f'    def set_transform_scale(self, value):\n')
                out.write(f'        self.set_transform_scale_x(value)\n')
                out.write(f'        self.set_transform_scale_y(value)\n')

                del memberNodes['lv_style_set_size']
                del memberNodes['lv_style_set_pad_all']
                del memberNodes['lv_style_set_pad_hor']
                del memberNodes['lv_style_set_pad_ver']
                del memberNodes['lv_style_set_pad_gap']
                del memberNodes['lv_style_set_margin_hor']
                del memberNodes['lv_style_set_margin_ver']
                del memberNodes['lv_style_set_margin_all']
                del memberNodes['lv_style_set_transform_scale']
            if structName == 'lv_obj_t':
                out.write(f'    def move_foreground(self):\n')
                out.write(f'        parent = self.get_parent()\n')
                out.write(f'        self.move_to_index(parent.get_child_count() - 1)\n')
                out.write(f'    def move_background(self):\n')
                out.write(f'        self.move_to_index(0)\n')
                out.write(f'    def set_style_size(self, width, height, selector):\n')
                out.write(f'        self.set_style_width(width, selector)\n')
                out.write(f'        self.set_style_height(height, selector)\n')
                out.write(f'    def set_style_pad_all(self, value, selector):\n')
                out.write(f'        self.set_style_pad_left(value, selector)\n')
                out.write(f'        self.set_style_pad_right(value, selector)\n')
                out.write(f'        self.set_style_pad_top(value, selector)\n')
                out.write(f'        self.set_style_pad_bottom(value, selector)\n')
                out.write(f'    def set_style_pad_hor(self, value, selector):\n')
                out.write(f'        self.set_style_pad_left(value, selector)\n')
                out.write(f'        self.set_style_pad_right(value, selector)\n')
                out.write(f'    def set_style_pad_ver(self, value, selector):\n')
                out.write(f'        self.set_style_pad_top(value, selector)\n')
                out.write(f'        self.set_style_pad_bottom(value, selector)\n')
                out.write(f'    def set_style_pad_gap(self, value, selector):\n')
                out.write(f'        self.set_style_pad_row(value, selector)\n')
                out.write(f'        self.set_style_pad_column(value, selector)\n')
                out.write(f'    def set_style_margin_hor(self, value, selector):\n')
                out.write(f'        self.set_style_margin_left(value, selector)\n')
                out.write(f'        self.set_style_margin_right(value, selector)\n')
                out.write(f'    def set_style_margin_ver(self, value, selector):\n')
                out.write(f'        self.set_style_margin_top(value, selector)\n')
                out.write(f'        self.set_style_margin_bottom(value, selector)\n')
                out.write(f'    def set_style_margin_all(self, value, selector):\n')
                out.write(f'        self.set_style_margin_left(value, selector)\n')
                out.write(f'        self.set_style_margin_right(value, selector)\n')
                out.write(f'        self.set_style_margin_top(value, selector)\n')
                out.write(f'        self.set_style_margin_bottom(value, selector)\n')
                out.write(f'    def set_style_transform_scale(self, value, selector):\n')
                out.write(f'        self.set_style_transform_scale_x(value, selector)\n')
                out.write(f'        self.set_style_transform_scale_y(value, selector)\n')

                del memberNodes['lv_obj_move_foreground']
                del memberNodes['lv_obj_move_background']
                del memberNodes['lv_obj_set_style_size']
                del memberNodes['lv_obj_set_style_pad_all']
                del memberNodes['lv_obj_set_style_pad_hor']
                del memberNodes['lv_obj_set_style_pad_ver']
                del memberNodes['lv_obj_set_style_pad_gap']
                del memberNodes['lv_obj_set_style_margin_hor']
                del memberNodes['lv_obj_set_style_margin_ver']
                del memberNodes['lv_obj_set_style_margin_all']
                del memberNodes['lv_obj_set_style_transform_scale']

            if ctor:
                del memberNodes[f'{structName[:-1]}create']

                params = getParams(ctor.args.params)
                out.write(f'    def __init__({", ".join([ "self" ] + [ p.name for p in params ])}):\n')
                for p in params:
                    if p.lines:
                        out.write('\n'.join([ '        ' + l for l in p.lines.splitlines() ]) + '\n')
                out.write(f'        self._pointer = _lvgl.{structName[:-1]}create({", ".join([ p.usage for p in params ])})\n')
                out.write(f'        _objects[self._pointer] = self\n')

            elif init:
                del memberNodes[f'{structName[:-1]}init']

                out.write(f'    def __init__(self):\n')
                out.write(f'        self._pointer = ffi.new(\'{structName}[2]\')\n') # We overallocate to compensate for a bug in CFFI new on ARMv7 (most likely an struct packing issue)
                out.write(f'        _lvgl.{structName[:-1]}init(self._pointer)\n')
                out.write(f'        _objects[self._pointer] = self\n')

            else:
                out.write(f'    def __init__(self):\n')
                out.write(f'        self._pointer = ffi.new(\'{structName}[2]\')\n') # We overallocate to compensate for a bug in CFFI new on ARMv7 (most likely an struct packing issue)
                out.write(f'        _objects[self._pointer] = self\n')

            for memberName, memberNode in memberNodes.items():
                if memberName == 'lv_grad_init_stops':
                    pass
                params = getParams(memberNode.args.params[1:])

                if memberName == 'lv_image_set_src':
                    params[0].usage = 'src.encode(\'utf-8\')'

                if memberName == 'lv_qrcode_update':
                    out.write(f'    def update(self, data: \'str\'):\n')
                    out.write(f'        return _lvgl.lv_qrcode_update(self._pointer, data.encode(\'utf-8\'), len(data))\n')
                    continue

                returnType = getNodeType(memberNode.type)
                if memberName.replace(memberPrefix[:-1], "").startswith('_get_') and memberName.endswith('_user_data'):
                    returnType = 'str'

                out.write(f'    def {memberName.replace(memberPrefix[:-1], "")[1:]}(')
                out.write(', '.join([ 'self' ] + [ f'{p.name}: \'{p.type_hint}\'' for p in params ]))
                out.write(') -> \'')
                out.write(returnType[3:-2] if returnType in structNodes else returnType)
                out.write('\':\n')

                for p in params:
                    if p.lines:
                        out.write('\n'.join([ '        ' + l for l in p.lines.splitlines() ]) + '\n')

                if returnType in structNodes:
                    out.write(f'        _pointer = _lvgl.{memberName}({", ".join([ "self._pointer" ] + [ p.usage for p in params ])})\n')
                    out.write(f'        if _pointer == ffi.NULL:\n')
                    out.write(f'            return None\n')
                    out.write(f'        result = _objects.get(_pointer)\n')
                    out.write(f'        if not result:\n')
                    out.write(f'            result = {returnType[3:-2]}.__new__({returnType[3:-2]})\n')
                    out.write(f'            result._pointer = _lvgl.{memberName}({", ".join([ "self._pointer" ] + [ p.usage for p in params ])})\n')
                    out.write(f'        return result\n')
                elif returnType == 'str':
                    out.write(f'        result = _lvgl.{memberName}({", ".join([ "self._pointer" ] + [ p.usage for p in params ])})\n')
                    out.write(f'        if result == ffi.NULL:\n')
                    out.write(f'            return None\n')
                    out.write(f'        result = ffi.cast(\'char*\', result)\n')
                    out.write(f'        result = ffi.string(result)\n')
                    out.write(f'        return result.decode(\'utf-8\')\n')
                else:
                    out.write(f'        return _lvgl.{memberName}({", ".join([ "self._pointer" ] + [ p.usage for p in params ])})\n')
            
            out.write(f'\n')

        if insertTimingLog:
            out.write('print(f"Structures: {time.time() - start:.2f}s")\n')
            out.write('\n')

        # Functions
        out.write('\n')
        out.write('################\n')
        out.write('# Functions\n')
        out.write('\n')
        out.write('_callbacks = {}\n')
        out.write('_user_data = []\n')
        out.write('\n')

        if insertTimingLog:
            out.write('start = time.time()\n')
            out.write('\n')

        for functionName, functionNode in functionNodes.items():
            if functionName in classMethodNodes:
                continue

            returnType = getNodeType(functionNode.type)
            params = getParams(functionNode.args.params)

            out.write(f'def {functionName[3:]}(')
            out.write(', '.join([ f'{p.name}: \'{p.type_hint}\'' for p in params]))
            out.write(') -> \'')
            out.write(returnType[3:-2] if returnType in structNodes else returnType)
            out.write('\':\n')

            for p in params:
                if p.lines:
                    out.write('\n'.join([ '    ' + l for l in p.lines.replace('self.', '').splitlines() ]) + '\n')

            if functionName == 'lv_windows_create_display':
                pass

            if returnType in structNodes:
                out.write(f'    result = {returnType[3:-2]}.__new__({returnType[3:-2]})\n')
                out.write(f'    result._pointer = _lvgl.{functionName}({", ".join([p.usage for p in params])})\n')
                out.write(f'    return result if result._pointer else None\n')
            elif returnType == 'str':
                out.write(f'        result = _lvgl.{functionName}({", ".join([p.usage for p in params])})\n')
                out.write(f'        result = ffi.cast(\'char*\', result)\n')
                out.write(f'        result = ffi.string(result)\n')
                out.write(f'        return result.decode(\'utf-8\')\n')
            else:
                out.write(f'    return _lvgl.{functionName}({", ".join([p.usage for p in params])})\n')

        if insertTimingLog:
            out.write('\n')
            out.write('print(f"Functions: {time.time() - start:.2f}s")\n')


if __name__ == "__main__":
    main()