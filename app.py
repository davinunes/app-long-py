# (As importações iniciais permanecem as mesmas)
from flask import Flask, request, jsonify
from reportlab.lib.pagesizes import A4
# NOVO: Importando 'ImageReader' para obter dimensões da imagem sem Pillow
from reportlab.lib.utils import ImageReader 
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from datetime import datetime
import base64
from io import BytesIO
from flask_cors import CORS
import os
import traceback

# (O início do app e constantes permanecem os mesmos)
app = Flask(__name__)
CORS(app)
nomes_meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
COLOR_PRIMARY = colors.HexColor('#2c3e50')
COLOR_SECONDARY = colors.HexColor('#3498db')
COLOR_TEXT = colors.HexColor('#34495e')
COLOR_LIGHT_GRAY = colors.HexColor('#ecf0f1')

# (A função draw_header_footer permanece a mesma)
def draw_header_footer(canvas, doc):
    canvas.saveState()
    PAGE_WIDTH, PAGE_HEIGHT = doc.pagesize
    logo_path = 'logo.png'
    if os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=0.8*inch, height=0.8*inch)
            logo.hAlign = 'LEFT'
            logo.drawOn(canvas, doc.leftMargin, PAGE_HEIGHT - 1*inch)
        except Exception as e: print(f"Não foi possível carregar o logo: {e}")
    canvas.setFont('Helvetica-Bold', 14)
    canvas.setFillColor(COLOR_PRIMARY)
    canvas.drawRightString(doc.width + doc.leftMargin, PAGE_HEIGHT - 0.8*inch, "Notificação Condominial")
    canvas.setFont('Helvetica', 9)
    canvas.setFillColor(COLOR_TEXT)
    canvas.drawRightString(doc.width + doc.leftMargin, PAGE_HEIGHT - 1.0*inch, "Documento Oficial")
    canvas.setStrokeColor(COLOR_LIGHT_GRAY)
    canvas.setLineWidth(1)
    canvas.line(doc.leftMargin, PAGE_HEIGHT - 1.2*inch, doc.width + doc.leftMargin, PAGE_HEIGHT - 1.2*inch)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.grey)
    canvas.drawRightString(doc.width + doc.leftMargin, 0.5*inch, f"Página {doc.page}")
    canvas.drawString(doc.leftMargin, 0.5*inch, "Condomínio Miami Beach | E-mail: conselhofiscalmiami2025@gmail.com")
    canvas.restoreState()


def gerar_pdf_com_reportlab(dados):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=1*inch, rightMargin=1*inch,
                            topMargin=1.8*inch, bottomMargin=1*inch)
    
    # ... (Definição dos styles permanece a mesma) ...
    styles = getSampleStyleSheet()
    story = []
    titulo_style = ParagraphStyle('CustomTitle', parent=styles['h1'], fontSize=18, leading=22, spaceAfter=12, alignment=1, textColor=COLOR_PRIMARY)
    subtitulo_style = ParagraphStyle('CustomHeading', parent=styles['h2'], fontSize=12, leading=16, spaceBefore=12, spaceAfter=6, textColor=COLOR_PRIMARY, fontName='Helvetica-Bold')
    normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=10, leading=14, textColor=COLOR_TEXT, spaceAfter=6, alignment=4)

    # ... (Montagem do Título, Data, Dados... permanece a mesma até a seção de fatos) ...
    tipo_doc = dados.get('tipo_documento', 'NOTIFICAÇÃO').upper()
    numero = dados.get('numero_notificacao', '')
    story.append(Paragraph(f"{tipo_doc} N° {numero}", titulo_style))
    story.append(Spacer(1, 0.2*inch))
    data_formatada = formatar_data(dados.get('data_emissao'))
    cidade = dados.get('cidade', 'Taguatinga/DF')
    story.append(Paragraph(f"{cidade}, {data_formatada}", ParagraphStyle('DataStyle', parent=normal_style, alignment=2)))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("DADOS DA NOTIFICAÇÃO", subtitulo_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_LIGHT_GRAY, spaceAfter=5))
    dados_tabela = [
        [Paragraph('<b>Unidade Notificada:</b>', normal_style), Paragraph(dados.get('unidade', ''), normal_style)],
        [Paragraph('<b>Tipo:</b>', normal_style), Paragraph(dados.get('tipo_notificacao', 'N/A'), normal_style)],
        [Paragraph('<b>Assunto:</b>', normal_style), Paragraph(dados.get('assunto', ''), normal_style)],
    ]
    tabela = Table(dados_tabela, colWidths=[2.2*inch, None])
    tabela.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 8)]))
    story.append(tabela)
    story.append(Spacer(1, 0.2*inch))

    # 4. Fatos (Texto)
    if 'fatos' in dados and dados['fatos']:
        story.append(Paragraph("I. DOS FATOS", subtitulo_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_LIGHT_GRAY, spaceAfter=5))
        fatos = dados['fatos']
        if isinstance(fatos, list):
            for i, fato in enumerate(fatos, 1):
                story.append(Paragraph(f"{i}. {fato}", normal_style))
        else:
            story.append(Paragraph(fatos, normal_style))

    # --- NOVO: SEÇÃO PARA INSERIR IMAGENS DOS FATOS ---
    fotos_fatos_b64 = dados.get('fotos_fatos', [])
    if fotos_fatos_b64:
        story.append(Paragraph("EVIDÊNCIAS FOTOGRÁFICAS", subtitulo_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_LIGHT_GRAY, spaceAfter=5))

        # Define a largura máxima para as imagens (baseado na largura da página)
        max_img_width = (doc.width / 2) - 0.2*inch # Duas imagens por linha com um pequeno espaço

        image_row = []
        image_grid_data = []

        for b64_string in fotos_fatos_b64:
            try:
                # Decodifica a string base64 para bytes
                img_bytes = base64.b64decode(b64_string)
                img_file = BytesIO(img_bytes)
                
                # Usa ImageReader para obter as dimensões sem depender do Pillow diretamente aqui
                img_reader = ImageReader(img_file)
                iw, ih = img_reader.getSize()
                
                # Calcula a proporção para redimensionar
                aspect = ih / float(iw)
                new_height = max_img_width * aspect
                
                # Cria o objeto de imagem do ReportLab
                img = Image(img_file, width=max_img_width, height=new_height)
                image_row.append(img)
                
                # Se a linha tiver 2 imagens, adiciona à grade e começa uma nova linha
                if len(image_row) == 2:
                    image_grid_data.append(image_row)
                    image_row = []

            except Exception as e:
                print(f"Erro ao processar imagem: {e}")
                # Adiciona um placeholder caso a imagem falhe
                error_para = Paragraph(f"<i>Erro ao carregar imagem</i>", normal_style)
                image_row.append(error_para)
        
        # Adiciona a última linha se ela não estiver completa
        if image_row:
            image_grid_data.append(image_row)

        if image_grid_data:
            # Cria a tabela para organizar as imagens em um grid
            image_table = Table(image_grid_data, colWidths=[max_img_width + 0.1*inch, max_img_width + 0.1*inch])
            image_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ]))
            story.append(image_table)
    # --- FIM DA NOVA SEÇÃO DE IMAGENS ---

    # ... (O restante da montagem do documento continua normalmente) ...
    if 'fundamentacao_legal' in dados and dados['fundamentacao_legal']: story.append(Paragraph("II. DA FUNDAMENTAÇÃO LEGAL", subtitulo_style)); story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_LIGHT_GRAY, spaceAfter=5)); story.append(Paragraph(dados['fundamentacao_legal'], normal_style))
    if 'texto_descritivo' in dados and dados['texto_descritivo']: story.append(Paragraph(dados['texto_descritivo'], normal_style))
    if 'tipo_penalidade' in dados and dados['tipo_penalidade']:
        story.append(Paragraph("III. DA PENALIDADE", subtitulo_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_LIGHT_GRAY, spaceAfter=5))
        penalidade_texto = f"Aplicada <b>{dados['tipo_penalidade'].upper()}</b> conforme as disposições regimentais."
        if dados.get('valor_multa'): penalidade_texto += f" Valor: <b>{dados['valor_multa']}</b>"
        story.append(Paragraph(penalidade_texto, normal_style))
    if dados.get('incluir_recurso', True):
        story.append(Paragraph("IV. DO DIREITO AO CONTRADITÓRIO E AMPLA DEFESA", subtitulo_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_LIGHT_GRAY, spaceAfter=5))
        story.append(Paragraph(f"Fica assegurado o direito de apresentação de recurso... através do e-mail <b>{dados.get('email_contato', 'conselhofiscalmiami2025@gmail.com')}</b>...", normal_style))
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("Atenciosamente,", normal_style)); story.append(Spacer(1, 0.5*inch)); story.append(Paragraph("________________________________________", normal_style)); story.append(Paragraph(f"<b>{dados.get('nome_assinatura', 'Administração do Condomínio')}</b>", normal_style)); story.append(Paragraph(dados.get('cargo_assinatura', 'Síndico'), normal_style))

    doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
    buffer.seek(0)
    return buffer.getvalue()


# (As rotas /gerar_documento, /health, /teste_simples e a função formatar_data permanecem as mesmas)
# O código delas já é capaz de lidar com os novos dados, pois a lógica está toda na função gerar_pdf_com_reportlab.
def formatar_data(data_string):
    if data_string:
        try:
            data_obj = datetime.strptime(data_string, '%Y-%m-%d')
            return data_obj.strftime(f"%d de {nomes_meses[data_obj.month - 1]} de %Y")
        except: pass
    data_atual = datetime.now()
    return data_atual.strftime(f"%d de {nomes_meses[data_atual.month - 1]} de %Y")

@app.route('/gerar_documento', methods=['POST'])
def gerar_documento():
    try:
        dados = request.get_json()
        if not dados: return jsonify({'error': 'Nenhum JSON foi fornecido'}), 400
        pdf_bytes = gerar_pdf_com_reportlab(dados)
        return_as_base64 = request.args.get('base64', '').lower() == 'true'
        if return_as_base64:
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
            return jsonify({'pdf_base64': pdf_base64, 'mensagem': 'Documento gerado com sucesso'}), 200
        else:
            nome_arquivo = f"notificacao_{dados.get('numero_notificacao', 'doc')}.pdf"
            return pdf_bytes, 200, {'Content-Type': 'application/pdf', 'Content-Disposition': f'inline; filename={nome_arquivo}'}
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Erro ao gerar documento: {str(e)}'}), 500

# ... (Resto do código Flask)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)