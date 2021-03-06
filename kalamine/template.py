#!/usr/bin/env python3
from .utils import load_data, LAYER_KEYS, LAFAYETTE_KEY


##
# Helpers
#

KEY_CODES = load_data('key_codes.yaml')
XKB_KEY_SYM = load_data('key_sym.yaml')


def hex_ord(char):
    return hex(ord(char))[2:].zfill(4)


def xml_proof(char):
    if char not in '<&"\u00a0>':
        return char
    else:
        return '&#x{0};'.format(hex_ord(char))


##
# GNU/Linux: XKB
# - standalone xkb file to be used by `setxkbcomp` (Xorg only)
# - system-wide installer script for Xorg & Wayland
#


def xkb_keymap(layout, eight_levels):
    """ Linux layout. """

    showDescription = True
    maxLength = 16  # `ISO_Level3_Latch` should be the longest symbol name

    output = []
    for keyName in LAYER_KEYS:
        if keyName.startswith('-'):  # separator
            if len(output):
                output.append('')
            output.append('//' + keyName[1:])
            continue

        symbols = []
        description = ' //'
        for layer in layout.layers:
            if keyName in layer:
                symbol = layer[keyName]
                desc = symbol
                if symbol in layout.dead_keys:
                    dk = layout.dead_keys[symbol]
                    desc = dk['alt_self']
                    if dk['char'] == LAFAYETTE_KEY:
                        symbol = 'ISO_Level3_Latch'
                    else:
                        symbol = 'dead_' + dk['name']
                elif symbol in XKB_KEY_SYM \
                        and len(XKB_KEY_SYM[symbol]) <= maxLength:
                    symbol = XKB_KEY_SYM[symbol]
                else:
                    symbol = 'U' + hex_ord(symbol).upper()
            else:
                desc = ' '
                symbol = 'VoidSymbol'

            description += ' ' + desc
            symbols.append(symbol.ljust(maxLength))

        s = 'key <{}> {{[ {}, {}, {}, {}]}};'  # 4-level layout by default
        if layout.has_altgr and layout.has_1dk:
            """ 6 layers are needed: they won't fit on the 4-level format.
            System XKB files require a Neo-like eight-level solution.
            Standalone XKB files work best with a dual-group solution:
            one 4-level group for base+1dk, one two-level group for AltGr.
            """
            if eight_levels:  # system XKB file (patch)
                s = 'key <{}> {{[ {}, {}, {}, {}, {}, {}, {}, {}]}};'
                symbols.append('VoidSymbol'.ljust(maxLength))
                symbols.append('VoidSymbol'.ljust(maxLength))
            else:  # user-space XKB file (standalone)
                s = 'key <{}> {{[ {}, {}, {}, {}],[ {}, {}]}};'
        elif layout.has_altgr:
            del symbols[3]
            del symbols[2]

        line = s.format(* [keyName.upper()] + symbols)
        if showDescription:
            line += description.rstrip()
            if line.endswith('\\'):
                line += ' '  # escape trailing backslash
        output.append(line)

    return output


###
# Windows: KLC
# To be used by the MS Keyboard Layout Creator to generate an installer.
# https://www.microsoft.com/en-us/download/details.aspx?id=22339
# https://levicki.net/articles/2006/09/29/HOWTO_Build_keyboard_layouts_for_Windows_x64.php
# Also supported by KbdEdit: http://www.kbdedit.com/ (non-free).
#


def klc_keymap(layout):
    """ Windows layout, main part. """

    supportedSymbols = \
        '1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'

    output = []
    for keyName in LAYER_KEYS:
        if keyName.startswith('-'):
            if len(output):
                output.append('')
            output.append('//' + keyName[1:])
            continue

        symbols = []
        description = '//'
        alpha = False

        for i in [0, 1, 4, 5]:
            layer = layout.layers[i]

            if keyName in layer:
                symbol = layer[keyName]
                desc = symbol
                if symbol in layout.dead_keys:
                    desc = layout.dead_keys[symbol]['alt_space']
                    symbol = hex_ord(desc) + '@'
                else:
                    if i == 0:
                        alpha = symbol.upper() != symbol
                    if symbol not in supportedSymbols:
                        symbol = hex_ord(symbol)
                symbols.append(symbol)
            else:
                desc = ' '
                symbols.append('-1')
            description += ' ' + desc

        if (layout.has_altgr):
            output.append('\t'.join([
                KEY_CODES['klc'][keyName],     # scan code & virtual key
                '1' if alpha else '0',         # affected by CapsLock?
                symbols[0], symbols[1], '-1',  # base layer
                symbols[2], symbols[3],        # altgr layer
                description.strip()
            ]))
        else:
            output.append('\t'.join([
                KEY_CODES['klc'][keyName],     # scan code & virtual key
                '1' if alpha else '0',         # affected by CapsLock?
                symbols[0], symbols[1], '-1',  # base layer
                description.strip()
            ]))

    return output


def klc_deadkeys(layout):
    """ Windows layout, dead keys. """

    output = []

    def appendLine(base, alt):
        s = '{0}\t{1}\t// {2} -> {3}'
        output.append(s.format(hex_ord(base), hex_ord(alt), base, alt))

    for k in layout.dk_index:
        dk = layout.dead_keys[k]

        output.append('// DEADKEY: ' + dk['name'].upper() + ' //{{{')
        output.append('DEADKEY\t' + hex_ord(dk['alt_space']))
        output.append('')

        if k == LAFAYETTE_KEY:
            output.extend(klc_dk_lafayette(layout))
        else:
            for i in range(len(dk['base'])):
                appendLine(dk['base'][i], dk['alt'][i])

        output.append('')
        output.append('// Space bar')
        appendLine('\u00a0', dk['alt_space'])
        appendLine('\u0020', dk['alt_space'])

        output.append('//}}}')
        output.append('')

    return output[:-1]


def klc_dk_index(layout):
    """ Windows layout, dead key index. """

    output = []
    for k in layout.dk_index:
        dk = layout.dead_keys[k]
        output.append('{0}\t"{1}"'.format(hex_ord(dk['alt_space']),
                                          dk['name'].upper()))
    return output


def klc_dk_lafayette(layout):
    """ Windows layout, Lafayette key. """

    output = []
    for i in [0, 1]:
        baseLayer = layout.layers[i]
        extLayer = layout.layers[i + 2]

        for keyName in LAYER_KEYS:
            if keyName.startswith('- Space') or keyName == 'spce':
                continue
            if keyName.startswith('-'):
                if len(output):
                    output.append('')
                output.append('//' + keyName[1:])
                continue
            elif keyName in extLayer:
                base = baseLayer[keyName]
                if base in layout.dead_keys:
                    base = layout.dead_keys[base]['alt_space']
                ext = extLayer[keyName]
                if (ext in layout.dead_keys):
                    ext = layout.dead_keys[ext]['alt_space']
                    lafayette = hex_ord(ext) + '@'
                else:
                    lafayette = hex_ord(ext)

                output.append('\t'.join([
                    hex_ord(base), lafayette, '// ' + base + ' -> ' + ext
                ]))

    return output


###
# MacOS X: keylayout
# https://developer.apple.com/library/content/technotes/tn2056/_index.html
#


def osx_keymap(layout):
    """ Mac OSX layout, main part. """

    str = []
    for index in range(5):
        layer = layout.layers[[0, 1, 0, 4, 5][index]]
        caps = index == 2

        def has_dead_keys(letter):
            for k in layout.dead_keys:
                if letter in layout.dead_keys[k]['base']:
                    return True
            return False

        output = []
        for keyName in LAYER_KEYS:
            if keyName.startswith('-'):
                if len(output):
                    output.append('')
                output.append('<!--' + keyName[1:] + ' -->')
                continue

            symbol = '&#x0010;'
            finalKey = True

            if keyName in layer:
                key = layer[keyName]
                if key in layout.dead_keys:
                    symbol = 'dead_' + layout.dead_keys[key]['name']
                    finalKey = False
                else:
                    symbol = xml_proof(key.upper() if caps else key)
                    finalKey = not has_dead_keys(key)

            c = 'code="{0}"'.format(KEY_CODES['osx'][keyName]).ljust(10)
            a = '{0}="{1}"'.format('output' if finalKey
                                   else 'action', symbol)
            output.append('<key {0} {1} />'.format(c, a))

        str.append(output)
    return str


def osx_actions(layout):
    """ Mac OSX layout, dead key actions. """

    output = []
    deadKeys = []
    dkIndex = []

    def when(state, action):
        s = 'state="{0}"'.format(state).ljust(18)
        if action in layout.dead_keys:
            a = 'next="{0}"'.format(layout.dead_keys[action]['name'])
        elif action.startswith('dead_'):
            a = 'next="{0}"'.format(action[5:])
        else:
            a = 'output="{0}"'.format(xml_proof(action))
        return '  <when {0} {1} />'.format(s, a)

    # spacebar actions
    output.append('<!-- Spacebar -->')
    output.append('<action id="space">')
    output.append(when('none', ' '))
    for k in layout.dk_index:
        dk = layout.dead_keys[k]
        output.append(when(dk['name'], dk['alt_space']))
    output.append('</action>')
    output.append('<action id="nbsp">')
    output.append(when('none', '&#x00a0;'))
    for k in layout.dk_index:
        dk = layout.dead_keys[k]
        output.append(when(dk['name'], dk['alt_space']))
    output.append('</action>')

    # all other actions
    for keyName in LAYER_KEYS:
        if keyName.startswith('-'):
            output.append('')
            output.append('<!--' + keyName[1:] + ' -->')
            continue

        for i in [0, 1]:
            if keyName not in layout.layers[i]:
                continue

            key = layout.layers[i][keyName]
            if i and key == layout.layers[0][keyName]:
                continue
            if key in layout.dead_keys:
                symbol = 'dead_' + layout.dead_keys[key]['name']
            else:
                symbol = xml_proof(key)

            action = []
            for k in layout.dk_index:
                dk = layout.dead_keys[k]
                if key in dk['base']:
                    idx = dk['base'].index(key)
                    action.append(when(dk['name'], dk['alt'][idx]))

            if key in layout.dead_keys:
                deadKeys.append('<action id="{0}">'.format(symbol))
                deadKeys.append(when('none', symbol))
                deadKeys.extend(action)
                deadKeys.append('</action>')
                dkIndex.append(symbol)
            elif len(action):
                output.append('<action id="{0}">'.format(symbol))
                output.append(when('none', symbol))
                output.extend(action)
                output.append('</action>')

        for i in [2, 3, 4, 5]:
            if keyName not in layout.layers[i]:
                continue
            key = layout.layers[i][keyName]
            if key not in layout.dead_keys:
                continue
            symbol = 'dead_' + layout.dead_keys[key]['name']
            if symbol in dkIndex:
                continue
            deadKeys.append('<action id="{0}">'.format(symbol))
            deadKeys.append(when('none', symbol))
            deadKeys.extend(action)
            deadKeys.append('</action>')
            dkIndex.append(symbol)

    return deadKeys + [''] + output


def osx_terminators(layout):
    """ Mac OSX layout, dead key terminators. """

    output = []
    for k in layout.dk_index:
        dk = layout.dead_keys[k]
        s = 'state="{0}"'.format(dk['name']).ljust(18)
        o = 'output="{0}"'.format(xml_proof(dk['alt_self']))
        output.append(' <when {0} {1} />'.format(s, o))
    return output
