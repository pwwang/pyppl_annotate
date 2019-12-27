"""Add annotation to PyPPL processes"""
import re
import textwrap
from diot import OrderedDiot, Diot
from pyppl.plugin import hookimpl
from pyppl.utils import always_list

__version__ = "0.0.2"

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
	OrderedDiot(infile = Diot(type = 'file', desc = 'description', default = ...))
	```
	"""
	ret = OrderedDiot()
	name = None
	for line in text.splitlines():
		if line[:1] in (' ', '\t') and not name:
			raise ValueError('Unexpected indention found at line: %s' % line)

		if line[:1] not in (' ', '\t'):
			try:
				name, rest = re.split(r'[\s:]', line, maxsplit = 1)
			except ValueError:
				name, rest = line.strip(), ''
			rest = rest.strip()
			rtype = default = ''
			if rest[:1] == '(' and '):' in rest:
				rtype, rest = rest[1:].split('):', 1)
			if 'Default:' in rest:
				rest, default = rest.split('Default:', 1)
			rest = rest.strip() + '\n'
			default = default.strip()
			ret[name] = Diot(type = rtype, desc = rest, default = default)
		else:
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
			options[ikey] = Diot(type = itype, desc = '', default = '')
		else:
			options[ikey].update(type = itype)
	return options

def _output_formatter(text, proc):
	options = _options_parser(text)
	# parse output types and defaults
	# {outkey => (outtype, template)}
	for outkey, outinfo in proc.output.items():
		if outkey not in options:
			options[outkey] = Diot(type = outinfo[0], default = outinfo[1].source, desc = '')
		else:
			options[outkey].update(type = outinfo[0], default = outinfo[1].source)
	return options

def _args_formatter(text, proc):
	options = _options_parser(text)
	for key, val in proc.args.items():
		if key not in options:
			options[key] = Diot(type = type(val).__name__, desc = '', default = val)
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

class Annotate: # pylint: disable=too-few-public-methods
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
		anno             = textwrap.dedent(anno.lstrip('\n'))
		self.proc        = proc
		self.sections    = _sections_parser(anno)
		self.description = self.section('description')
		self.input       = self.section('input', _input_formatter)
		self.output      = self.section('output', _output_formatter)
		self.args        = self.section('args', _args_formatter)
		self.config      = self.section('config', _config_formatter)

	def section(self, name, formatter = None):
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
	proc.add_config('annotate',
		default   = '',
		runtime   = 'ignore',
		converter = lambda annotate: annotate if isinstance(annotate, Annotate) \
			else Annotate(annotate, proc = proc))
