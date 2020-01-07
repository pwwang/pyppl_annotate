import pytest
from diot import Diot
import pyppl_annotate as pan
from pyppl.proc import Proc

@pytest.mark.parametrize('text,expect', [
	("""\
desc1
desc2
@section1:
	sec1
		subsec
	sec2
""", dict(description = """\
desc1
desc2
""", section1 = """\
sec1
	subsec
sec2
""")),
	("""\
@description:
desc1
desc2
@section1:
	sec1
	 subsec
	sec2
""", dict(description = """\
desc1
desc2
""", section1 = """\
sec1
 subsec
sec2
"""))
])
def test_parse_sections(text, expect):
	assert pan._sections_parser(text) == expect

@pytest.mark.parametrize('text, expect', [
	("""\
infile (file): description. Default: 123
	- subdesc1
	- subdesc2
infile2: someother description
""", {
		'infile': {'type': 'file', 'desc': 'description.\n  - subdesc1\n  - subdesc2\n', 'default': '123'},
		'infile2': {'type': '', 'desc': 'someother description\n', 'default': None}
	})
])
def test_options_parser(text, expect):
	assert pan._options_parser(text) == expect

def test_options_parser_error():
	with pytest.raises(ValueError):
		pan._options_parser("""\
		abc""")

	pan._options_parser("""abc: """) == {'abc': dict(type = '', default = '', desc = '')}

	with pytest.raises(ValueError):
		pan._options_parser("a")

@pytest.mark.parametrize('text, proc, expect', [
	("infile: abc", Proc(input = 'infile:file'), {'infile': {'type': 'file', 'default': None, 'desc': 'abc\n'}}),
	("infile: abc", Proc(input = {'infile:file': [1]}), {'infile': {'type': 'file', 'default': None, 'desc': 'abc\n'}}),
	("invar: abc", Proc(input = {'invar': [1]}), {'invar': {'type': 'var', 'default': None, 'desc': 'abc\n'}}),
	("", Proc(input = {'invar': [1]}), {'invar': {'type': 'var', 'default': '', 'desc': ''}})
])
def test_input_formatter(text, proc, expect):
	assert pan._input_formatter(text, proc) == expect

@pytest.mark.parametrize('text,proc,expect', [
	('outfile (var): a', Proc(output = 'outfile:file:abc'), {'outfile': {'type': 'file', 'default': 'abc', 'desc': 'a\n'}}),
	('', Proc(output = 'outfile:file:abc'), {'outfile': {'type': 'file', 'default': 'abc', 'desc': ''}}),
])
def test_output_formatter(text, proc, expect):
	assert pan._output_formatter(text, proc) == expect

@pytest.mark.parametrize('text,proc,expect', [
	('params (Diot): ddd', Proc(args = Diot(params = {'a': 1})), {'params': {'type': 'Diot', 'desc': 'ddd\n', 'default': {'a': 1}}}),
	('', Proc(args = Diot(params = {'a': 1})), {'params': {'type': 'Diot', 'desc': '', 'default': {'a': 1}}}),
	('params: ddd', Proc(args = Diot(params = {'a': 1})), {'params': {'type': 'Diot', 'desc': 'ddd\n', 'default': {'a': 1}}}),
])
def test_args_formatter(text, proc, expect):
	assert pan._args_formatter(text, proc) == expect

def test_config_formatter():
	p = Proc()
	p.config.report_template = 'abc'
	assert pan._config_formatter('', p) == {}
	assert pan._config_formatter('report_template:', p) == {'report_template': {'type': 'str', 'desc': '\n', 'default': 'abc'}}

def test_annotate():
	anno = pan.Annotate("""
	@description:
		desc1
		desc2
	@sec1:
		sec1
			- subsec1
	""", Proc(id = 'pAnnotate'))
	assert anno.description == "desc1\ndesc2\n"
	assert anno.section('sec') is None
	assert anno.section('sec1') == "sec1\n\t- subsec1\n"
	assert anno.section('sec1', lambda x: x.splitlines()) == ["sec1", "\t- subsec1"]

def test_hook():
	pHook = Proc(config = Diot(annotate = """
	abc
	"""))
	pan.proc_init(pHook)
	assert pHook.config.annotate.description == 'abc\n'

def test_input():
	pInput = Proc()
	pan.proc_init(pInput)
	pInput.config.annotate = 'x\n@input:\n@output:\n@config:\n@args:'
	pInput.input = {'a': [1]}
	assert pInput.config.annotate.description == 'x\n'
	assert pInput.config.annotate.input == {'a': {'default': '',
       'desc': '',
       'type': 'var'}}
	assert pInput.config.annotate.output == {}
	assert pInput.config.annotate.config == {}
	assert pInput.config.annotate.args == {}
