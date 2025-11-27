from app.parsers.domrf import DomRfParser


def get_domrf_parser() -> DomRfParser:
    """
    Provide Dom.rf parser instance.

    :return: Dom.rf parser
    """

    return DomRfParser()
