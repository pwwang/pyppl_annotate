# pyppl_annotate

Adding long description/annotation for PyPPL processes.

## Installation
```shell
pip install pyppl_annotate
```

## Usage

```python
p = Proc(
	config = {
		'annotate': """
			An awesome process
			@input:
				infile: The input file
			@output:
				outfile: The output file
			@config:
				report_template: The report template file
			@custome_section:
				blah
			""",
		'report_template': '/path/to/report_template'}
	input = 'infile:file',
	output = 'outfile:file:output.txt',
	args = {'a': 1}
)

p.config.annotate.description == 'An awesome process\n'
p.config.annotate.input = {
	'infile': {'type': 'file', 'desc': 'The input file\n', 'default': ''}}
p.config.annotate.output = {
	'outfile': {'type': 'file', 'desc': 'The output file\n', 'default': 'output.txt'}}
}
p.config.annotate.args = {
	'a': {'type': 'int', 'desc': '', 'default': 1}
}
p.config.annotate.config = {
	'report_template': {'type': 'str', 'desc': 'The report template file\n',
	'default': '/path/to/report_template'}
}
p.config.annotate.section('nonexist') is None
p.config.annotate.section('custome_section') == 'blan\n'
p.config.annotate.section('custome_section',
	formatter = lambda value, proc: proc.id + ':' + value) == 'p: blan\n'
```
