from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
from io import BytesIO

from docx import Document
from docx.table import Table
from pypdf import PdfReader


def _word_lines(container):
    for block in container.iter_inner_content():
        if isinstance(block, Table):
            seen_cells = set()
            for row in block.rows:
                cells = []
                for cell in row.cells:
                    if cell._tc in seen_cells:
                        continue
                    seen_cells.add(cell._tc)
                    text = " / ".join(_word_lines(cell))
                    if text:
                        cells.append(text)
                if cells:
                    yield " | ".join(cells)
        elif block.text.strip():
            yield block.text.strip()


class _HTMLText(HTMLParser):
    blocks = {"br", "p", "div", "li", "tr", "table", "section", "blockquote",
              "h1", "h2", "h3", "h4", "h5", "h6"}
    hidden = {"script", "style", "head", "template"}

    def __init__(self):
        super().__init__()
        self.fragments = []
        self.hidden_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.hidden:
            self.hidden_depth += 1
        elif not self.hidden_depth and tag in self.blocks:
            self.fragments.append("\n")

    def handle_endtag(self, tag):
        if tag in self.hidden:
            self.hidden_depth = max(0, self.hidden_depth - 1)
        elif not self.hidden_depth and tag in self.blocks:
            self.fragments.append("\n")
        elif not self.hidden_depth and tag == "td":
            self.fragments.append(" ")

    def handle_data(self, data):
        if not self.hidden_depth:
            self.fragments.append(data)


def _email_text(content: bytes) -> str:
    message = BytesParser(policy=policy.default).parsebytes(content)
    headers = [
        f"{name}: {message[name]}"
        for name in ("Subject", "From", "To", "Cc", "Date")
        if message[name]
    ]
    part = message.get_body(preferencelist=("plain", "html"))
    body = ""
    if part is not None:
        try:
            body = part.get_content()
        except LookupError:
            body = part.get_payload(decode=True).decode("utf-8", errors="replace")
        if part.get_content_subtype() == "html":
            parser = _HTMLText()
            parser.feed(body)
            parser.close()
            body = "\n".join(
                " ".join(line.split())
                for line in "".join(parser.fragments).splitlines()
                if line.strip()
            )
    return "\n\n".join(filter(None, ("\n".join(headers), body.strip())))


def extract_document_text(extension: str, content: bytes) -> str:
    if extension == "pdf":
        return "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(content)).pages).strip()
    if extension == "docx":
        return "\n".join(_word_lines(Document(BytesIO(content)))).strip()
    if extension == "eml":
        return _email_text(content)
    return content.decode("utf-8-sig", errors="replace").strip()
