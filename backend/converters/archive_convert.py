import os
import logging
from pathlib import Path
from typing import Optional

from .converter_interface import ConverterInterface


logger = logging.getLogger(__name__)

class ArchiveConverter(ConverterInterface):
    """
    Converter for repacking between archive formats like ZIP and TAR.GZ.
    """

    supported_input_formats: set = {
        'zip',
        'tar.gz',
        'tar.bz2',
        'tar.xz',
        'tar.zst',
    }
    supported_output_formats: set = {
        'zip',
        'tar.gz',
        'tar.bz2',
        'tar.xz',
        'tar.zst',
    }

    def __init__(self, input_file: str, output_dir: str, input_type: str, output_type: str):
        """
        Initialize Archive converter.

        Args:
            input_file: Path to the input archive file
            output_dir: Directory where the converted file will be saved
            input_type: Input file format (e.g., 'zip', 'tar.gz')
            output_type: Output file format (e.g., 'zip', 'tar.gz')
        """
        super().__init__(input_file, output_dir, input_type, output_type)
    
    @classmethod
    def can_register(cls) -> bool:
        """
        Check if the converter can be registered based on supported formats.

        Returns:
            True if the converter can be registered, False otherwise.
        """
        return False  # This converter is not registered in the registry and is only used for testing purposes

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
        return cls.supported_output_formats - {fmt}
    
    def convert(self, overwrite: bool = True, quality: Optional[str] = None) -> list[str]:
        """
        Convert the archive to the output format.

        Args:
            overwrite: Whether to overwrite existing output file (default: True)
            quality: Not applicable for archive conversion, ignored.

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

        logging.error("Archive conversion is not yet implemented.")
        raise NotImplementedError("Archive conversion is not yet implemented.")