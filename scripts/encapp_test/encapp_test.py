""" Abstraction for encapp operations """
from abc import ABC, abstractmethod


class EncappTest(ABC):
    """Encapp operations"""

    @abstractmethod
    def remove_encapp_gen_files(self, debug=0):
        pass

    @abstractmethod
    def list_codecs(self, debug=0):
        pass

    @abstractmethod
    def codec_test(self, settings):
        pass

    @abstractmethod
    def install_app(self, debug):
        pass

    @abstractmethod
    def uninstall_app(self, debug):
        pass

    @abstractmethod
    def install_ok(self, debug):
        pass
