# Synthetic extraction fixture

`synthetic_form16_extraction.json` contains artificial values for exercising
the mocked extraction contract. It contains no real taxpayer identity or
document content. Integration tests generate an in-memory signature-only PNG
and mock the Gemini response from this fixture.
