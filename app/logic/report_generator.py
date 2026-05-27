from pathlib import Path
import datetime
import time
from collections import defaultdict
import jinja2
import shutil

# Shared insight mapping used by both HTML and PDF generators
_INSIGHT_MAPPING = {
    "Solidarité & Soin": "Votre profil montre un intérêt marqué pour l'aide et le soin aux autres, des qualités humaines très recherchées.",
    "Création artistique": "Vous avez une fibre créative. Les métiers qui permettent d'imaginer, de concevoir ou d'exprimer une vision artistique pourraient vous correspondre.",
    "Technologie": "Votre attrait pour la technologie et les nouveautés est un atout majeur dans un monde en pleine transformation numérique.",
    "Nature": "Vous semblez apprécier le plein air et la nature. Des carrières liées à l'environnement, l'agriculture ou le vivant pourraient vous intéresser.",
    "customer_facing": "Vous n'hésitez pas à aller vers les autres. Les métiers de contact, d'accueil et de service où le relationnel est clé sont une piste à explorer.",
    "teamwork": "Vous semblez apprécier le travail en équipe. Recherchez des environnements collaboratifs où vous pourrez partager vos idées.",
    "solo_work": "Vous êtes à l'aise en autonomie. Les postes qui offrent de l'indépendance et de la prise d'initiative pourraient vous convenir.",
    "rules_oriented": "Votre profil suggère que vous êtes à l'aise dans des environnements structurés où les règles et les procédures sont claires.",
    "Transmission": "Votre profil montre une volonté de transmettre vos connaissances et d'expliquer les choses, ce qui est une compétence pédagogique précieuse."
}

def _extract_user_tags(answers):
    user_tags = set()
    for answer_obj in answers.values():
        if isinstance(answer_obj, dict):
            for tag in answer_obj.get("tags", []):
                user_tags.add(tag.get("value"))
    return user_tags

def generate_html_report(user_profile, jobs_data, questions_data):
    """Generates an interactive HTML report from the user's profile using Jinja2 templates."""
    user_name = user_profile.get("name", "Utilisateur")
    # --- Build absolute paths from the project root ---
    project_root = Path(__file__).parent.parent.parent
    report_path = project_root / "orientation"
    report_path.mkdir(exist_ok=True)

    # --- Define template and destination paths ---
    template_folder = project_root / "app" / "templates"
    filename = report_path / f"profil_{user_name.lower().replace(' ','_')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    css_source_path = template_folder / "report_style.css"
    css_dest_path = report_path / "report_style.css"

    # --- Copy CSS file to the report destination ---
    try:
        shutil.copy(css_source_path, css_dest_path)
    except IOError as e:
        # It's not critical enough to stop the whole report generation
        print(f"Warning: Could not copy CSS file. {e}")

    # --- Prepare data for the template ---
    # Group answers by category for the report
    answers = user_profile.get("answers", {})
    questions_map = {q['id']: {'question': q['question'], 'category': q.get('category', 'Autre')} for q in questions_data.get('questions', [])}
    grouped_answers = defaultdict(list)
    
    if answers:
        for q_id, answer_obj in answers.items():
            if isinstance(answer_obj, dict) and q_id in questions_map:
                q_details = questions_map[q_id]
                category_title = q_details['category'].replace('_', ' ').capitalize()
                grouped_answers[category_title].append({
                    'question': q_details['question'],
                    'text': answer_obj.get('text', 'N/A')
                })

    # Assign unique IDs to jobs for JS interaction
    recommended_jobs = user_profile.get("recommended_jobs", [])

    # --- Generate Personalized Insights based on tags ---
    user_tags = _extract_user_tags(answers) if answers else set()
    personalized_insights = [
        insight for tag, insight in _INSIGHT_MAPPING.items() if tag in user_tags
    ]
    for i, job in enumerate(recommended_jobs):
        job['_id'] = f"job-{i}"

    # --- Jinja2 Template Rendering ---
    template_loader = jinja2.FileSystemLoader(searchpath=str(template_folder))
    template_env = jinja2.Environment(loader=template_loader)
    template = template_env.get_template("report_template.html")

    context = {
        "user_name": user_name,
        "generation_date": datetime.date.today().strftime('%d/%m/%Y'),
        "weak_match": user_profile.get("weak_match", False),
        "user_interests": user_profile.get("user_interests"),
        "user_skills": user_profile.get("user_skills"),
        "user_strengths": user_profile.get("user_strengths"),
        "recommended_subjects": user_profile.get("recommended_subjects", []),
        "recommended_jobs": recommended_jobs,
        "grouped_answers": dict(sorted(grouped_answers.items())),
        "personalized_insights": personalized_insights,
        "cache_buster": int(time.time())
    }

    html_content = template.render(context)

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        return str(filename.absolute())
    except IOError as e:
        raise IOError(f"Erreur lors de l'écriture du fichier : {e}")


def generate_pdf_report(user_profile, jobs_data, questions_data):
    """Generates a PDF report from the user's profile using reportlab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.colors import HexColor, white, grey
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak, KeepTogether
    )

    NAVY        = HexColor('#0d0221')
    GOLD        = HexColor('#ffd700')
    ORANGE      = HexColor('#ff9900')
    LIGHT_GRAY  = HexColor('#f5f5f5')
    MID_GRAY    = HexColor('#cccccc')
    DARK_GRAY   = HexColor('#333333')
    WARN_BG     = HexColor('#fff3cd')
    WARN_BORDER = HexColor('#ffc107')
    WARN_TEXT   = HexColor('#856404')

    def S(name, **kw):
        return ParagraphStyle(name, **kw)

    S_TITLE     = S('T',  fontSize=26, fontName='Helvetica-Bold',    textColor=NAVY,      alignment=1, spaceAfter=4)
    S_SUBTITLE  = S('ST', fontSize=12, fontName='Helvetica',         textColor=grey,      alignment=1, spaceAfter=16)
    S_SECTION   = S('SE', fontSize=14, fontName='Helvetica-Bold',    textColor=NAVY,      spaceBefore=12, spaceAfter=6)
    S_CARD_H    = S('CH', fontSize=11, fontName='Helvetica-Bold',    textColor=NAVY,      spaceAfter=3)
    S_BODY      = S('B',  fontSize=10, fontName='Helvetica',         textColor=DARK_GRAY, spaceAfter=3,  leading=14)
    S_ITALIC    = S('I',  fontSize=10, fontName='Helvetica-Oblique', textColor=grey,      spaceAfter=3,  leading=14)
    S_LABEL     = S('L',  fontSize=9,  fontName='Helvetica-Bold',    textColor=ORANGE,    spaceAfter=2,  spaceBefore=5)
    S_BULLET    = S('BU', fontSize=10, fontName='Helvetica',         textColor=DARK_GRAY, leftIndent=12, spaceAfter=2, leading=14)
    S_JOB_H     = S('JH', fontSize=12, fontName='Helvetica-Bold',    textColor=white)
    S_NUM       = S('N',  fontSize=10, fontName='Helvetica',         textColor=DARK_GRAY, spaceAfter=2,  leading=14)
    S_WARN      = S('W',  fontSize=10, fontName='Helvetica',         textColor=WARN_TEXT, leading=14)
    S_CAT       = S('CA', fontSize=11, fontName='Helvetica-Bold',    textColor=NAVY,      spaceAfter=4,  spaceBefore=8)
    S_Q         = S('Q',  fontSize=10, fontName='Helvetica-Bold',    textColor=DARK_GRAY, spaceAfter=1,  leading=13)
    S_ANS       = S('A',  fontSize=10, fontName='Helvetica-Oblique', textColor=grey,      spaceAfter=5,  leading=13)

    def divider(color=GOLD, thickness=2):
        return HRFlowable(width="100%", thickness=thickness, color=color, spaceAfter=8, spaceBefore=4)

    # --- Paths ---
    user_name = user_profile.get("name", "Utilisateur")
    project_root = Path(__file__).parent.parent.parent
    report_path = project_root / "orientation"
    report_path.mkdir(exist_ok=True)
    filename = report_path / f"profil_{user_name.lower().replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    W, _ = A4
    content_w = W - 4 * cm
    col_w = (content_w - 0.4 * cm) / 2

    doc = SimpleDocTemplate(
        str(filename), pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm, topMargin=2.5*cm, bottomMargin=2*cm,
        title=f"Rapport d'Orientation - {user_name}",
    )

    # --- Prepare data (mirrors generate_html_report) ---
    answers = user_profile.get("answers", {})
    questions_map = {
        q['id']: {'question': q['question'], 'category': q.get('category', 'Autre')}
        for q in questions_data.get('questions', [])
    }
    grouped_answers = defaultdict(list)
    for q_id, answer_obj in answers.items():
        if isinstance(answer_obj, dict) and q_id in questions_map:
            q_info = questions_map[q_id]
            cat = q_info['category'].replace('_', ' ').capitalize()
            grouped_answers[cat].append({'question': q_info['question'], 'text': answer_obj.get('text', 'N/A')})

    recommended_jobs = user_profile.get("recommended_jobs", [])
    user_tags = _extract_user_tags(answers) if answers else set()
    insights = [insight for tag, insight in _INSIGHT_MAPPING.items() if tag in user_tags]

    story = []

    # ── HEADER ──────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph("Rapport d'Orientation", S_TITLE))
    story.append(Paragraph(
        f"Profil de <b>{user_name}</b> — Généré le {datetime.date.today().strftime('%d/%m/%Y')}",
        S_SUBTITLE
    ))
    story.append(divider())
    story.append(Spacer(1, 0.2 * cm))

    if user_profile.get("weak_match"):
        warn_t = Table([[Paragraph(
            "<b>Avertissement :</b> Vos réponses ne permettent pas de dégager un profil très marqué. "
            "Les suggestions ci-dessous sont des pistes générales à explorer.",
            S_WARN
        )]], colWidths=[content_w])
        warn_t.setStyle(TableStyle([
            ('BACKGROUND',   (0,0), (-1,-1), WARN_BG),
            ('BOX',          (0,0), (-1,-1), 1, WARN_BORDER),
            ('LEFTPADDING',  (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING',   (0,0), (-1,-1), 8),
            ('BOTTOMPADDING',(0,0), (-1,-1), 8),
        ]))
        story.append(warn_t)
        story.append(Spacer(1, 0.3 * cm))

    # ── SECTION 1: PROFILE ───────────────────────────────────────────────────
    story.append(Paragraph("Votre profil en un coup d’œil", S_SECTION))

    card_data = []
    if user_profile.get("user_interests"):
        card_data.append(("Vos centres d’intérêt", user_profile["user_interests"]))
    if user_profile.get("user_skills"):
        card_data.append(("Vos compétences clés", user_profile["user_skills"]))
    if user_profile.get("user_strengths"):
        card_data.append(("Vos qualités personnelles", user_profile["user_strengths"]))
    subjects = user_profile.get("recommended_subjects", [])
    if subjects:
        card_data.append(("Matières à privilégier", ", ".join(subjects)))

    if card_data:
        rows = []
        for i in range(0, len(card_data), 2):
            title_l, text_l = card_data[i]
            left_cell  = [Paragraph(title_l, S_CARD_H), Paragraph(text_l or "—", S_BODY)]
            if i + 1 < len(card_data):
                title_r, text_r = card_data[i + 1]
                right_cell = [Paragraph(title_r, S_CARD_H), Paragraph(text_r or "—", S_BODY)]
            else:
                right_cell = [Paragraph("", S_BODY)]
            rows.append([left_cell, right_cell])

        cards_t = Table(rows, colWidths=[col_w, col_w])
        cards_t.setStyle(TableStyle([
            ('VALIGN',       (0,0), (-1,-1), 'TOP'),
            ('BACKGROUND',   (0,0), (-1,-1), LIGHT_GRAY),
            ('INNERGRID',    (0,0), (-1,-1), 0.5, MID_GRAY),
            ('BOX',          (0,0), (-1,-1), 0.5, MID_GRAY),
            ('LEFTPADDING',  (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING',   (0,0), (-1,-1), 8),
            ('BOTTOMPADDING',(0,0), (-1,-1), 8),
        ]))
        story.append(cards_t)
        story.append(Spacer(1, 0.3 * cm))

    # ── SECTION 2: INSIGHTS ──────────────────────────────────────────────────
    if insights:
        story.append(Paragraph("Nos observations personnalisées", S_SECTION))
        for insight in insights:
            story.append(Paragraph(f"• {insight}", S_BULLET))
        story.append(Spacer(1, 0.2 * cm))

    # ── SECTION 3: JOBS ──────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Métiers suggérés", S_SECTION))
    story.append(divider())

    if recommended_jobs:
        story.append(Paragraph("Liste complète des suggestions", S_LABEL))
        for i, job in enumerate(recommended_jobs, 1):
            story.append(Paragraph(f"{i}. {job.get('name', 'N/A')}", S_NUM))
        story.append(Spacer(1, 0.5 * cm))

        story.append(Paragraph("Détail des 10 premiers métiers", S_SECTION))

        for job in recommended_jobs[:10]:
            title_t = Table(
                [[Paragraph(job.get('name', 'N/A'), S_JOB_H)]],
                colWidths=[content_w]
            )
            title_t.setStyle(TableStyle([
                ('BACKGROUND',   (0,0), (-1,-1), NAVY),
                ('LEFTPADDING',  (0,0), (-1,-1), 10),
                ('RIGHTPADDING', (0,0), (-1,-1), 10),
                ('TOPPADDING',   (0,0), (-1,-1), 8),
                ('BOTTOMPADDING',(0,0), (-1,-1), 8),
            ]))

            elements = [title_t]

            description = job.get('description', 'Description non disponible.')
            elements.append(Paragraph("Description", S_LABEL))
            elements.append(Paragraph(description, S_ITALIC))

            access = job.get('studies_access', 'Non spécifié.')
            elements.append(Paragraph("Accès au métier", S_LABEL))
            elements.append(Paragraph(access, S_BODY))

            skills = job.get('skills', [])
            if skills:
                core  = [s['libelle'] for s in skills if s.get('is_core')]
                other = [s['libelle'] for s in skills if not s.get('is_core')]
                elements.append(Paragraph("Compétences clés", S_LABEL))
                if core:
                    elements.append(Paragraph("<b>Cœur de métier :</b> " + ", ".join(core[:6]), S_BODY))
                if other:
                    elements.append(Paragraph("<b>Autres :</b> " + ", ".join(other[:6]), S_BODY))

            qualities = job.get('qualities', [])
            if qualities:
                elements.append(Paragraph("Qualités professionnelles", S_LABEL))
                elements.append(Paragraph(", ".join(q.get('libelle', '') for q in qualities[:6]), S_BODY))

            sectors = job.get('secteurs_activite', [])
            if sectors:
                elements.append(Paragraph("Secteurs d’activité", S_LABEL))
                elements.append(Paragraph(", ".join(sectors[:5]), S_BODY))

            elements.append(divider(MID_GRAY, 0.5))

            story.append(KeepTogether(elements[:4]))
            for el in elements[4:]:
                story.append(el)

    # ── SECTION 4: ANSWER SYNTHESIS ──────────────────────────────────────────
    if grouped_answers:
        story.append(PageBreak())
        story.append(Paragraph("Synthèse de vos réponses", S_SECTION))
        story.append(divider())

        for category, answer_list in sorted(grouped_answers.items()):
            story.append(Paragraph(category, S_CAT))
            for item in answer_list:
                story.append(Paragraph(item['question'], S_Q))
                story.append(Paragraph(f"Votre réponse : {item['text']}", S_ANS))

    try:
        doc.build(story)
        return str(filename.absolute())
    except Exception as e:
        raise IOError(f"Erreur lors de la génération du PDF : {e}")