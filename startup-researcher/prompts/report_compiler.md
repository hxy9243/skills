# Report Compiler

Your goal is to assemble the category-level market analyses and the individual company profiles into a single, cohesive, professional Markdown document (`final_draft.md`).

## Assembly Workflow
1. **Title Page/Headering:** Insert a main heading for the report.
2. **Table of Contents (ToC):** Generate a Markdown ToC linking to each category and subsequent company profiles.
3. **Category Sections:** For each category:
   - Insert the category heading.
   - Insert the **Macro-Overview**, explicitly formatting it with "Macro Trends", "Capital Concentration", "Key Risks", and "Customer Adoption" paragraphs.
   - Insert the **Pros/Cons Matrix** (from `market_analysis.md`).
   - Insert the individual company profiles (from `company_research.md`) belonging to this category. Ensure a page break (`<div style="page-break-after: always;"></div>`) separates major sections/categories if aesthetically pleasing.

## Footer Injection
At the very end of `final_draft.md`, append this exact HTML block to create the document footer:
<footer>
  <span style="font-size: 8px; color: #666;">
    Generated with <a href="https://github.com/hxy9243/skills/tree/main/startup-researcher">startup researcher</a>, [Current Date]
  </span>
</footer>

## Metadata & Styling
The document must be styled using the accompanying `style.css` file to enforce:
- Font: Times New Roman (10pt/11pt).
- Color Scheme: Slate Grey & Navy Blue.
- Structured, striped tables.

## PDF Generation
Generate the PDF using WeasyPrint:
```bash
python3 -m markdown final_draft.md > final_draft.html
weasyprint final_draft.html final_draft.pdf -s style.css
```