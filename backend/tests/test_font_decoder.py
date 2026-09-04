from pathlib import Path

from app.adapters.font_decoder import FontDecoder, _extract_font_base64


def test_font_data_is_extracted_from_secret_style():
    html = '<style id="cxSecretStyle">@font-face{src:url(data:font/ttf;base64,QUJD)}</style>'
    assert _extract_font_base64(html) == "QUJD"


def test_font_decoder_degrades_when_mapping_resource_is_missing(tmp_path: Path):
    decoder = FontDecoder(tmp_path / "missing.json")
    assert decoder.set_html_content('<style id="cxSecretStyle">x</style>') is False
    assert decoder.decode("\ue000") == "\ue000"
