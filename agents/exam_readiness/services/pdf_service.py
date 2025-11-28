from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Preformatted
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib import colors
from typing import Dict, Any, List
from datetime import datetime
import re
import json


def _escape_html(text: str) -> str:
    """Escape HTML special characters but preserve ReportLab tags"""
    # Don't escape if text contains ReportLab tags
    if any(tag in text for tag in ['<b>', '<i>', '<u>', '<font', '<code>']):
        return text
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _format_text_with_markdown(text: str) -> str:
    """Convert markdown-style formatting to ReportLab HTML tags"""
    if not text:
        return ""
    
    # Escape HTML first
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    # Convert **bold** to <b>bold</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    
    # Convert *italic* to <i>italic</i>
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    
    # Convert `code` to monospace font
    text = re.sub(r'`([^`]+?)`', r'<font name="Courier" size="9" color="darkred">\1</font>', text)
    
    # Convert triple backticks code blocks (preserve them for special handling)
    text = re.sub(r'```(\w*)\n(.+?)\n```', r'[CODE_BLOCK:\1]\2[/CODE_BLOCK]', text, flags=re.DOTALL)
    
    return text


def _extract_code_blocks(text: str) -> List[tuple]:
    """Extract code blocks from text, returns list of (language, code, is_json)"""
    code_blocks = []
    pattern = r'\[CODE_BLOCK:(\w*)\](.+?)\[/CODE_BLOCK\]'
    
    for match in re.finditer(pattern, text, re.DOTALL):
        lang = match.group(1) or 'text'
        code = match.group(2).strip()
        
        # Check if it's JSON
        is_json = lang.lower() in ['json', 'javascript'] or _is_valid_json(code)
        
        code_blocks.append((lang, code, is_json))
    
    return code_blocks


def _is_valid_json(text: str) -> bool:
    """Check if text is valid JSON"""
    try:
        json.loads(text)
        return True
    except:
        return False


def _create_code_block_table(code: str, is_json: bool = False, language: str = 'text') -> Table:
    """Create a formatted table for code blocks"""
    if is_json:
        try:
            # Pretty print JSON
            parsed = json.loads(code)
            code = json.dumps(parsed, indent=2)
        except:
            pass
    
    # Create a preformatted text block
    code_style = ParagraphStyle(
        'CodeBlock',
        fontName='Courier',
        fontSize=8,
        leading=10,
        leftIndent=10,
        rightIndent=10,
        spaceBefore=6,
        spaceAfter=6,
        textColor=colors.HexColor('#1a1a1a'),
        backColor=colors.HexColor('#f5f5f5')
    )
    
    # Add language label if provided
    if language:
        header = f"[{language.upper()}]"
        code = f"{header}\n{code}"
    
    data = [[Preformatted(code, code_style)]]
    
    table = Table(data, colWidths=[6.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
        ('BOX', (0, 0), (-1, -1), 1, colors.grey),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    return table


def generate_assessment_pdf(assessment_data: Dict[str, Any], output_path: str) -> None:
    """Generate a well-formatted PDF document from assessment data with markdown support"""
    
    doc = SimpleDocTemplate(
        output_path, 
        pagesize=letter,
        leftMargin=0.75*inch,
        rightMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a237e'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.grey,
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Oblique'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=colors.HexColor('#1976d2'),
        spaceAfter=10,
        spaceBefore=15,
        fontName='Helvetica-Bold',
        borderPadding=(5, 5, 5, 5),
        backColor=colors.HexColor('#e3f2fd'),
        borderWidth=0,
        borderRadius=3
    )
    
    question_style = ParagraphStyle(
        'Question',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=8,
        leading=14,
        alignment=TA_JUSTIFY,
        fontName='Helvetica'
    )
    
    option_style = ParagraphStyle(
        'Option',
        parent=styles['Normal'],
        fontSize=10,
        leftIndent=20,
        spaceAfter=4,
        leading=13,
        fontName='Helvetica'
    )
    
    metadata_style = ParagraphStyle(
        'Metadata',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=4,
        fontName='Helvetica'
    )
    
    # Header section with title
    story.append(Paragraph(assessment_data['title'], title_style))
    
    # Subtitle/description
    if assessment_data.get('description'):
        story.append(Paragraph(assessment_data['description'], subtitle_style))
    else:
        story.append(Spacer(1, 0.15*inch))
    
    # Metadata table
    metadata = [
        ['Subject:', assessment_data['subject']],
        ['Assessment Type:', assessment_data['assessment_type'].capitalize()],
        ['Difficulty Level:', assessment_data['difficulty'].capitalize()],
        ['Total Questions:', str(assessment_data['total_questions'])],
        ['Generated:', datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')]
    ]
    
    metadata_table = Table(metadata, colWidths=[1.5*inch, 5*inch])
    metadata_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#424242')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#616161')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(metadata_table)
    story.append(Spacer(1, 0.4*inch))
    
    # Divider line
    divider = Table([['']], colWidths=[6.5*inch], rowHeights=[2])
    divider.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, -1), 2, colors.HexColor('#1976d2')),
    ]))
    story.append(divider)
    story.append(Spacer(1, 0.3*inch))
    
    # Questions
    for idx, question in enumerate(assessment_data['questions'], 1):
        # Question header with number, marks, and difficulty
        header_text = f"Question {idx}"
        marks_text = f"[{question.get('marks', question.get('points', 'N/A'))} marks]"
        difficulty_text = f"({question.get('difficulty', 'N/A')})"
        
        story.append(Paragraph(
            f"<b>{header_text}</b> {marks_text} <i>{difficulty_text}</i>", 
            heading_style
        ))
        story.append(Spacer(1, 0.1*inch))
        
        # Format and process question text
        question_text = question.get('question_text', '')
        formatted_question = _format_text_with_markdown(question_text)
        
        # Check for code blocks
        code_blocks = _extract_code_blocks(formatted_question)
        
        if code_blocks:
            # Split text by code blocks and render separately
            parts = re.split(r'\[CODE_BLOCK:\w*\].+?\[/CODE_BLOCK\]', formatted_question, flags=re.DOTALL)
            
            for i, part in enumerate(parts):
                if part.strip():
                    story.append(Paragraph(part, question_style))
                    story.append(Spacer(1, 0.05*inch))
                
                # Add code block if exists
                if i < len(code_blocks):
                    lang, code, is_json = code_blocks[i]
                    story.append(_create_code_block_table(code, is_json, lang))
                    story.append(Spacer(1, 0.1*inch))
        else:
            # No code blocks, render as normal
            story.append(Paragraph(formatted_question, question_style))
            story.append(Spacer(1, 0.15*inch))
        
        # Options for MCQ
        if question.get('question_type') == 'mcq' and question.get('options'):
            for opt_idx, option in enumerate(question['options'], 1):
                letter_label = chr(64 + opt_idx)  # A, B, C, D
                formatted_option = _format_text_with_markdown(option)
                
                # Check if option contains code
                if '[CODE_BLOCK:' in formatted_option:
                    code_blocks_opt = _extract_code_blocks(formatted_option)
                    parts = re.split(r'\[CODE_BLOCK:\w*\].+?\[/CODE_BLOCK\]', formatted_option, flags=re.DOTALL)
                    
                    story.append(Paragraph(f"<b>{letter_label}.</b> {parts[0] if parts else ''}", option_style))
                    if code_blocks_opt:
                        lang, code, is_json = code_blocks_opt[0]
                        story.append(Spacer(1, 0.05*inch))
                        code_table = _create_code_block_table(code, is_json, lang)
                        # Indent the code block for options
                        story.append(Spacer(1, 0.05*inch))
                        story.append(code_table)
                else:
                    story.append(Paragraph(f"<b>{letter_label}.</b> {formatted_option}", option_style))
                
                story.append(Spacer(1, 0.05*inch))
        
        # Add extra space between questions
        story.append(Spacer(1, 0.35*inch))
        
        # Page break after every 3-4 questions for better readability
        if idx % 4 == 0 and idx < len(assessment_data['questions']):
            story.append(PageBreak())
    
    # Build PDF
    doc.build(story)