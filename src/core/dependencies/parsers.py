from src.parsers.domrf import DomRfParser


def get_domrf_parser() -> DomRfParser:
    """
    Provide Dom.rf parser instance.

    :return: configured Dom.rf parser
    """

    return DomRfParser()
