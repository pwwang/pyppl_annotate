"""Add annotation to PyPPL processes"""
import re
import textwrap
from diot import OrderedDiot, Diot
from pyppl.plugin import hookimpl
from pyppl.utils import always_list

__version__ = "0.0.4"


def _sections_parser(text):
    ret = OrderedDiot()
    section = None
    for line in text.splitlines():
        if line.startswith("@"):
            section = line.strip('@: \t')
            ret[section] = ''
            continue
        if not section:
            section = 'description'
            ret[section] = line + '\n'
        else:
            ret[section] += line + '\n'
    for section, content in ret.items():
        ret[section] = textwrap.dedent(content)
    return ret


def _options_parser(text):
    """
    Parse option-like annotations. For example, this will be parsed to
    ```
    infile (file): description. Default: ...
    ```
    ```
    OrderedDiot(infile=Diot(type='file', desc='description', default=...))
    ```
    """
    ret = OrderedDiot()
    name = None
    for line in text.splitlines():
        if line[:1] in (' ', '\t') and not name:
            raise ValueError('Unexpected indention found at line: %s' % line)

        if line[:1] not in (' ', '\t'):
            # tool:
            # tool: blah
            # `tool`: blah
            # tool(type): blah
            # tool(type): blah. Default: xxx
            # `tool:type`: blah
            # `tool (type)` : blah
            matches = re.match(
                r'^(`?)([\w_.-]+)[\s:(]*([\w_.|-]*)?\)?'
                r'\1\s*:\s*(.*?)\s*(?:Default:\s*(.+))?$', line)
            if not matches:
                raise ValueError('Cannot recognize item format, expect: '
                                 '"name (type): description. Default: xxx" '
                                 'but get "%s"' % line)
            name = matches.group(2)
            ret[name] = Diot(type=matches.group(3),
                             desc=matches.group(4) + '\n',
                             default=matches.group(5))
        else:
            line_notab = line.lstrip('\t')
            ntabs = len(line) - len(line_notab)
            line = '  ' * ntabs + line_notab
            ret[name].desc += line + '\n'
    return ret


def _input_formatter(text, proc):
    options = _options_parser(text)
    # parse input types
    inkeys = proc._input
    if isinstance(proc._input, dict):
        inkeys = ','.join(proc._input.keys())
    inkeys = always_list(inkeys)
    for inkey in inkeys:
        if ':' in inkey:
            ikey, itype = inkey.split(':', 1)
        else:
            ikey, itype = inkey, 'var'
        if ikey not in options:
            options[ikey] = Diot(type=itype, desc='', default='')
        else:
            options[ikey].update(type=itype)
    return options


def _output_formatter(text, proc):
    options = _options_parser(text)
    # parse output types and defaults
    # {outkey => (outtype, template)}
    for outkey, outinfo in proc.output.items():
        if outkey not in options:
            options[outkey] = Diot(type=outinfo[0],
                                   default=outinfo[1].source,
                                   desc='')
        else:
            options[outkey].update(type=outinfo[0], default=outinfo[1].source)
    return options


def _args_formatter(text, proc):
    options = _options_parser(text)
    for key, val in proc.args.items():
        if key not in options:
            options[key] = Diot(type=type(val).__name__, desc='', default=val)
        if not options[key].default:
            options[key].default = val
        if not options[key].type:
            options[key].type = type(val).__name__
    return options


def _config_formatter(text, proc):
    options = _options_parser(text)
    for key, val in proc.config.items():
        if key not in options:
            # there might be many config items, we
            # only put those annotated
            continue
        if not options[key].type:
            options[key].type = type(val).__name__
        if not options[key].default:
            options[key].default = val
    return options


class Annotate:  # pylint: disable=too-few-public-methods
    """@API
    The annotate for process
    """
    def __init__(self, anno, proc):
        """@API
        Construct
        @params:
            anno (str): The annotation
        """
        # remove first empty lines
        anno = textwrap.dedent(anno.lstrip('\n'))
        self.proc = proc
        self.sections = _sections_parser(anno)

    @property
    def description(self):
        """Description section"""
        return self.section('description')

    @property
    def input(self):
        """Input section"""
        return self.section('input', _input_formatter)

    @property
    def output(self):
        """Output section"""
        return self.section('output', _output_formatter)

    @property
    def args(self):
        """Args section"""
        return self.section('args', _args_formatter)

    @property
    def config(self):
        """Config section"""
        return self.section('config', _config_formatter)

    def section(self, name, formatter=None):
        """@API
        Get the section
        @params:
            name (str): The name of the section
            formatter (callable): The formatter
        @returns:
            (OrderedDiot): The information of the section
        """
        if name not in self.sections:
            return None
        if formatter:
            try:
                return formatter(self.sections[name], self.proc)
            except TypeError:
                return formatter(self.sections[name])
        return self.sections[name]


@hookimpl
def proc_init(proc):
    """Add the config"""
    # it's process-specific, we should be let runtime_config override it
    proc.add_config(
        'annotate',
        default='',
        runtime='ignore',
        converter=lambda annotate: (annotate
                                    if isinstance(annotate, Annotate)
                                    else Annotate(annotate, proc=proc))
    )
