import os
import re
import tempfile
import pypandoc
from pathlib import Path
from typing import Optional

from .converter_interface import ConverterInterface


class PyPandocConverter(ConverterInterface):
    """
    Converter for document formats using pypandoc (a Python wrapper for Pandoc).
    Supports conversions between markdown, HTML, plain text, Word documents,
    reStructuredText, LaTeX, EPUB, and other document formats.
    """

    supported_input_formats: set = {
        'md',
        'html',
        'txt',
        'docx',
        'rst',
        'tex',
        'tex',
        'epub',
        'odt',
        'rtf',
        'org',
        'textile',
        'mediawiki',
        'adoc',
        'ipynb',
        'fb2',
        'muse',
        'opml',
        'dbk',
    }
    supported_output_formats: set = {
        'md',
        'html',
        'txt',
        'docx',
        'rst',
        'tex',
        'tex',
        'epub',
        'odt',
        'rtf',
        'org',
        'adoc',
        'pdf',
        'ipynb',
        'textile',
        'mediawiki',
        'pptx',
        'dbk',
        'muse',
        'opml',
    }

    # PDF engine to use for PDF output (weasyprint is installed as a Python
    # dependency and its system libraries are included in the Docker image).
    _pdf_engine = 'weasyprint'

    # Pandoc reader and writer format identifiers are not fully symmetric.
    # In particular, `plain` is a writer but not a valid reader in Pandoc 3.x,
    # so `.txt` inputs use the permissive markdown reader instead.
    _pandoc_input_format_map = {
        'md': 'gfm',
        'html': 'html',
        'txt': 'markdown',
        'docx': 'docx',
        'rst': 'rst',
        'tex': 'latex',
        'tex': 'latex',
        'epub': 'epub',
        'odt': 'odt',
        'rtf': 'rtf',
        'org': 'org',
        'textile': 'textile',
        'mediawiki': 'mediawiki',
        'adoc': 'asciidoc',
        'pdf': 'pdf',
        'ipynb': 'ipynb',
        'fb2': 'fb2',
        'muse': 'muse',
        'opml': 'opml',
        'dbk': 'docbook',
    }
    _pandoc_output_format_map = {
        'md': 'gfm',
        'html': 'html',
        'txt': 'plain',
        'docx': 'docx',
        'rst': 'rst',
        'tex': 'latex',
        'tex': 'latex',
        'epub': 'epub',
        'odt': 'odt',
        'rtf': 'rtf',
        'org': 'org',
        'textile': 'textile',
        'mediawiki': 'mediawiki',
        'adoc': 'asciidoc',
        'pdf': 'pdf',
        'ipynb': 'ipynb',
        'fb2': 'fb2',
        'muse': 'muse',
        'opml': 'opml',
        'dbk': 'docbook',
        'pptx': 'pptx',
    }

    def __init__(self, input_file: str, output_dir: str, input_type: str, output_type: str):
        """
        Initialize PyPandoc converter.

        Args:
            input_file: Path to the input document file
            output_dir: Directory where the converted file will be saved
            input_type: Input file format (e.g., 'md', 'docx', 'html')
            output_type: Output file format (e.g., 'md', 'docx', 'html')
        """
        super().__init__(input_file, output_dir, input_type, output_type)

    def can_convert(self) -> bool:
        """
        Check if the input file can be converted to the output format.

        Returns:
            True if conversion is possible, False otherwise.
        """
        input_fmt = self.input_type.lower()
        output_fmt = self.output_type.lower()

        if input_fmt not in self.supported_input_formats:
            return False
        if output_fmt not in self.supported_output_formats:
            return False

        return True

    @classmethod
    def get_formats_compatible_with(cls, format_type: str) -> set:
        """
        Get the set of compatible output formats for a given input format.

        Args:
            format_type: The input format to check compatibility for.

        Returns:
            Set of compatible output formats.
        """
        fmt = format_type.lower()
        if fmt not in cls.supported_input_formats:
            return set()
        formats = cls.supported_output_formats - {fmt}
        return formats

    def _get_pandoc_input_format(self, fmt: str) -> str:
        """
        Map our input format name to a Pandoc reader identifier.

        Args:
            fmt: Our internal format name.

        Returns:
            The Pandoc format string.
        """
        return self._pandoc_input_format_map.get(fmt.lower(), fmt.lower())

    def _get_pandoc_output_format(self, fmt: str) -> str:
        """
        Map our output format name to a Pandoc writer identifier.

        Args:
            fmt: Our internal format name.

        Returns:
            The Pandoc format string.
        """
        return self._pandoc_output_format_map.get(fmt.lower(), fmt.lower())

    def _build_extra_args(self) -> list[str]:
        extra_args: list[str] = []
        input_dir = str(Path(self.input_file).resolve().parent)

        # Resolve relative resources such as linked images from the source file's directory.
        extra_args.append(f'--resource-path={input_dir}')

        # Org files often contain export options Pandoc does not understand.
        # They are non-fatal and produce noisy stderr, so keep this path quiet.
        if self.input_type.lower() == 'org':
            extra_args.append('--quiet')

        if self.output_type.lower() == 'pdf':
            extra_args.append(f'--pdf-engine={self._pdf_engine}')
            if self._pdf_engine == 'weasyprint':
                extra_args.append('--pdf-engine-opt=--quiet')

        if self.output_type.lower() in ('html', 'revealjs', 'slidy', 's5', 'dzslides'):
            extra_args.append('--standalone')

        return extra_args

    def _is_remote_resource(self, target: str) -> bool:
        return target.startswith(('http://', 'https://'))

    def _resource_exists(self, target: str, input_dir: Path) -> bool:
        if self._is_remote_resource(target):
            return False
        return (input_dir / target).exists()

    def _sanitize_rst_content(self, content: str, input_dir: Path) -> str:
        lines = content.splitlines()
        sanitized: list[str] = []
        index = 0

        while index < len(lines):
            line = lines[index]
            match = re.match(r'^(\s*\.\.\s+image::\s+)(\S+)\s*$', line)
            if not match:
                sanitized.append(line)
                index += 1
                continue

            target = match.group(2)
            if self._resource_exists(target, input_dir):
                sanitized.append(line)
                index += 1
                continue

            index += 1
            while index < len(lines):
                next_line = lines[index]
                if next_line.startswith('   :') or next_line.startswith('      '):
                    index += 1
                    continue
                break

        return '\n'.join(sanitized) + ('\n' if content.endswith('\n') else '')

    def _sanitize_org_content(self, content: str, input_dir: Path) -> str:
        def replace_file_link(match: re.Match[str]) -> str:
            target = match.group(1)
            if self._resource_exists(target, input_dir):
                return match.group(0)
            return ''

        return re.sub(r'\[\[file:([^\]]+)\]\]', replace_file_link, content)

    def _sanitize_muse_content(self, content: str, input_dir: Path) -> str:
        def replace_link(match: re.Match[str]) -> str:
            target = match.group(1)
            label = match.group(2)
            if self._resource_exists(target, input_dir):
                return match.group(0)
            return label or ''

        content = re.sub(r'\[\[(?!URL:)([^\]\[]+?\.(?:png|jpe?g|gif|svg))\]\[([^\]]*)\]\]', replace_link, content, flags=re.IGNORECASE)
        content = re.sub(r'\[\[URL:(https?://[^\]]+\.(?:png|jpe?g|gif|svg))\]\]', '', content, flags=re.IGNORECASE)
        return content

    def _prepare_input_file(self) -> tuple[str, Optional[str]]:
        input_path = Path(self.input_file).resolve()
        input_dir = input_path.parent

        if self.input_type.lower() not in {'rst', 'org', 'muse'}:
            return self.input_file, None

        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if self.input_type.lower() == 'rst':
            sanitized = self._sanitize_rst_content(content, input_dir)
        elif self.input_type.lower() == 'org':
            sanitized = self._sanitize_org_content(content, input_dir)
        else:
            sanitized = self._sanitize_muse_content(content, input_dir)

        if sanitized == content:
            return self.input_file, None

        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            encoding='utf-8',
            suffix=input_path.suffix,
            delete=False,
        )
        with temp_file:
            temp_file.write(sanitized)

        return temp_file.name, temp_file.name

    def convert(self, overwrite: bool = True, quality: Optional[str] = None) -> list[str]:
        """
        Convert the input document to the output format using pypandoc.

        Args:
            overwrite: Whether to overwrite existing output file (default: True)
            quality: Not applicable for document formats, ignored.

        Returns:
            List containing the path to the converted output file.

        Raises:
            FileNotFoundError: If input file doesn't exist.
            ValueError: If the conversion is not supported.
            RuntimeError: If conversion fails.
        """
        if not self.can_convert():
            raise ValueError(
                f"Conversion from {self.input_type} to {self.output_type} is not supported."
            )

        if not os.path.isfile(self.input_file):
            raise FileNotFoundError(f"Input file not found: {self.input_file}")

        # Generate output filename
        input_filename = Path(self.input_file).stem
        output_file = os.path.join(
            self.output_dir, f"{input_filename}.{self.output_type}"
        )

        # Check if output file exists and overwrite is False
        if not overwrite and os.path.exists(output_file):
            return [output_file]

        temp_input_file = None

        try:
            input_pandoc_fmt = self._get_pandoc_input_format(self.input_type)
            output_pandoc_fmt = self._get_pandoc_output_format(self.output_type)
            extra_args = self._build_extra_args()
            conversion_input_file, temp_input_file = self._prepare_input_file()

            pypandoc.convert_file(
                conversion_input_file,
                output_pandoc_fmt,
                format=input_pandoc_fmt,
                outputfile=output_file,
                extra_args=extra_args,
            )

            if not os.path.exists(output_file):
                raise RuntimeError(
                    f"Output file was not created: {output_file}"
                )

            return [output_file]

        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Document conversion failed: {str(e)}")
        finally:
            if temp_input_file and os.path.exists(temp_input_file):
                os.unlink(temp_input_file)