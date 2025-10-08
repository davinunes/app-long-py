from flask import Flask, request, jsonify
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from datetime import datetime
import base64
from io import BytesIO
from flask_cors import CORS
import os
import traceback

app = Flask(__name__)
CORS(app)

# --- Constantes e Configurações Globais ---
nomes_meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
COLOR_PRIMARY = colors.HexColor('#2c3e50')
COLOR_TEXT = colors.HexColor('#34495e')
COLOR_LIGHT_GRAY = colors.HexColor('#ecf0f1')

# --- Funções Auxiliares ---

def draw_footer(canvas, doc):
    canvas.saveState()
    PAGE_WIDTH, PAGE_HEIGHT = doc.pagesize
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.grey)
    canvas.setStrokeColor(COLOR_LIGHT_GRAY)
    canvas.setLineWidth(0.5)
    canvas.line(doc.leftMargin, 0.7 * inch, doc.width + doc.leftMargin, 0.7 * inch)
    canvas.drawRightString(doc.width + doc.leftMargin, 0.5 * inch, f"Página {doc.page}")
    canvas.drawString(doc.leftMargin, 0.5 * inch, "Condomínio Miami Beach - Documento Oficial")
    canvas.restoreState()

def formatar_data(data_string):
    if not data_string:
        data_atual = datetime.now()
    else:
        try:
            data_atual = datetime.strptime(data_string, '%Y-%m-%d')
        except (ValueError, TypeError):
            data_atual = datetime.now()
    return data_atual.strftime(f"%d de {nomes_meses[data_atual.month - 1]} de %Y")

def criar_cabecalho(dados, styles):
    logo_path = 'logo.png'
    logo_content = []
    if os.path.exists(logo_path):
        try:
            img = ImageReader(logo_path)
            img_width, img_height = img.getSize()
            aspect = img_height / float(img_width)
            logo_width = 1.5 * inch
            logo_content.append(Image(logo_path, width=logo_width, height=(logo_width * aspect)))
        except Exception:
            logo_content.append(Paragraph("Condomínio Miami Beach", styles['h2']))
    else:
        logo_content.append(Paragraph("Condomínio Miami Beach", styles['h2']))

    unidade_completa = f"{dados.get('bloco', '')}{dados.get('unidade', '')}"
    data_formatada = formatar_data(dados.get('data_emissao'))
    
    info_data = [
        [Paragraph('<b>Documento N°:</b>', styles['Normal']), Paragraph(dados.get('numero', ''), styles['Normal'])],
        [Paragraph('<b>Data de Emissão:</b>', styles['Normal']), Paragraph(data_formatada, styles['Normal'])],
        [Paragraph('<b>Unidade Notificada:</b>', styles['Normal']), Paragraph(unidade_completa, styles['Normal'])],
        [Paragraph('<b>Tipo:</b>', styles['Normal']), Paragraph(dados.get('tipo_notificacao', 'N/A'), styles['Normal'])],
        [Paragraph('<b>Assunto:</b>', styles['Normal']), Paragraph(dados.get('assunto', ''), styles['Normal'])],
    ]
    info_table = Table(info_data, colWidths=[1.5*inch, None], style=[('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 4)])

    main_header_table = Table([[logo_content, info_table]], colWidths=[1.8*inch, None], style=[('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0,0), (0,0), 0)])
    
    return main_header_table

# --- Função Principal de Geração de PDF ---

def gerar_pdf_com_reportlab(dados):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1*inch, rightMargin=1*inch, topMargin=0.8*inch, bottomMargin=1*inch)
    
    styles = getSampleStyleSheet()
    story = []
    
    subtitulo_style = ParagraphStyle('CustomHeading', parent=styles['h2'], fontSize=12, spaceBefore=18, spaceAfter=6, textColor=COLOR_PRIMARY, fontName='Helvetica-Bold')
    normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=10, leading=14, textColor=COLOR_TEXT, alignment=4)

    # Criação do cabeçalho unificado
    cabecalho_tabela = criar_cabecalho(dados, styles)
    story.append(cabecalho_tabela)
    story.append(Spacer(1, 0.3 * inch))

    # Fatos
    if dados.get('fatos'):
        story.append(Paragraph("I. DOS FATOS", subtitulo_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_LIGHT_GRAY, spaceAfter=5))
        for i, fato in enumerate(dados.get('fatos', []), 1):
            story.append(Paragraph(f"{i}. {fato}", normal_style))
    
    # --- BLOCO DE CÓDIGO DAS IMAGENS (AGORA CORRETO E COMPLETO) ---
    fotos_b64 = dados.get('fotos_fatos', [])
    if fotos_b64 and isinstance(fotos_b64, list):
        story.append(Paragraph("EVIDÊNCIAS FOTOGRÁFICAS", subtitulo_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_LIGHT_GRAY, spaceAfter=5))

        max_img_width = (doc.width / 2) - 0.2 * inch
        image_grid_data = []
        image_row = []

        for b64_string in fotos_b64:
            try:
                img_bytes = base64.b64decode(b64_string)
                img_file = BytesIO(img_bytes)
                img_reader = ImageReader(img_file)
                iw, ih = img_reader.getSize()
                aspect = ih / float(iw) if iw > 0 else 0
                new_height = max_img_width * aspect
                img = Image(img_file, width=max_img_width, height=new_height)
                image_row.append(img)
                if len(image_row) == 2:
                    image_grid_data.append(image_row)
                    image_row = []
            except Exception as e:
                print(f"Erro ao processar imagem para o PDF: {e}")
        
        if image_row:
            image_grid_data.append(image_row)

        if image_grid_data:
            image_table = Table(image_grid_data, colWidths=[max_img_width + 0.1 * inch, max_img_width + 0.1 * inch])
            image_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('BOTTOMPADDING', (0, 0), (-1, -1), 10)]))
            story.append(image_table)
    # --- FIM DO BLOCO DE IMAGENS ---

    # Fundamentação
    if dados.get('fundamentacao_legal'):
        story.append(Paragraph("II. DA FUNDAMENTAÇÃO LEGAL", subtitulo_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_LIGHT_GRAY, spaceAfter=5))
        story.append(Paragraph(dados['fundamentacao_legal'], normal_style))
    
    # Direito ao Recurso
    url_recurso = dados.get('url_recurso', '#')
    prazo_recurso = dados.get('prazo_recurso', 5)
    texto_recurso = f"""Fica assegurado o direito de apresentação de recurso. Para tanto, concede-se o prazo de <b>{prazo_recurso} dias úteis</b> para apresentação do instrumento de defesa, que deve ser submetido através do seguinte endereço: <b><a href="{url_recurso}" color="blue">{url_recurso}</a></b>."""
    story.append(Paragraph("IV. DO DIREITO AO CONTRADITÓRIO E AMPLA DEFESA", subtitulo_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_LIGHT_GRAY, spaceAfter=5))
    story.append(Paragraph(texto_recurso, normal_style))

    # Assinatura
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph("Atenciosamente,", normal_style))
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph("________________________________________", normal_style))
    story.append(Paragraph(f"<b>{dados.get('nome_assinatura', 'Administração do Condomínio')}</b>", normal_style))
    story.append(Paragraph(dados.get('cargo_assinatura', 'Síndico'), normal_style))
    
    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    buffer.seek(0)
    return buffer.getvalue()

# --- Rotas da API ---
@app.route('/gerar_documento', methods=['POST'])
def gerar_documento():
    try:
        dados = request.get_json()
        if not dados:
            return jsonify({'error': 'Nenhum JSON foi fornecido'}), 400
        
        pdf_bytes = gerar_pdf_com_reportlab(dados)
        
        nome_arquivo = f"notificacao_{dados.get('numero', 'doc').replace('/', '-')}.pdf"
        
        return pdf_bytes, 200, {
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'inline; filename={nome_arquivo}'
        }
    except Exception as e:
        print("!!!!!! OCORREU UM ERRO INTERNO AO GERAR O PDF !!!!!!")
        traceback.print_exc()
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        return jsonify({'error': f'Erro interno ao gerar documento: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)