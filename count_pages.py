import PyPDF2

def print_page_text():
    r = PyPDF2.PdfReader('report/iclr2026 2/iclr2026_conference.pdf')
    for i, p in enumerate(r.pages):
        text = p.extract_text()
        if "References" in text or "REFERENCES" in text:
            print(f"'References' found on page {i+1}")
            break

print_page_text()
