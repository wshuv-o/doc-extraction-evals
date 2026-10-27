from extract_eval.extractors import RulesExtractor, load_text
from extract_eval.pdfgen import write_pdf


def test_generated_pdf_is_readable(tmp_path):
    path = tmp_path / "t.pdf"
    write_pdf(path, ["Borrower: Oak (Texas) Owner LLC", "Loan Amount: $1,000,000"])
    text = load_text(path)
    assert "Oak (Texas) Owner LLC" in text
    assert RulesExtractor().extract(text)["loan_amount"] == "$1,000,000"
