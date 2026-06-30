import os
import io
import json
import zipfile

from flask import (render_template, request, send_file,
                   jsonify, after_this_request, current_app)
from werkzeug.utils import secure_filename
from PIL import Image
import pikepdf
from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject

from app.services import merge_pdfs, parse_pages_to_remove, compress_pdf
from app.metrics import log_usage


def init_routes(app):

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/find')
    def find():
        return render_template('find.html')

    @app.route('/merge', methods=['POST'])
    def merge():
        upload = current_app.config['UPLOAD_FOLDER']
        if 'base_pdf' not in request.files:
            return jsonify({'error': 'Falta el PDF base'}), 400
        base_file = request.files['base_pdf']
        if base_file.filename == '':
            return jsonify({'error': 'No se seleccionó el PDF base'}), 400
        insertions_raw = request.form.get('insertions', '[]')
        try:
            insertions = json.loads(insertions_raw)
        except json.JSONDecodeError:
            return jsonify({'error': 'Formato de inserciones inválido'}), 400
        if not isinstance(insertions, list) or len(insertions) == 0:
            return jsonify({'error': 'Debe agregar al menos un PDF para insertar'}), 400

        base_path = os.path.join(upload, secure_filename(base_file.filename))
        base_file.save(base_path)
        inserted_files = []
        for ins in insertions:
            file_key = ins.get('fileKey')
            if not file_key or file_key not in request.files:
                for f in inserted_files:
                    os.remove(f)
                os.remove(base_path)
                return jsonify({'error': 'Falta el archivo para una inserción'}), 400
            pdf_file = request.files[file_key]
            if pdf_file.filename == '':
                for f in inserted_files:
                    os.remove(f)
                os.remove(base_path)
                return jsonify({'error': 'Archivo vacío en una inserción'}), 400
            fpath = os.path.join(upload, secure_filename(pdf_file.filename))
            pdf_file.save(fpath)
            inserted_files.append(fpath)

        try:
            output_path = merge_pdfs(base_path, insertions, inserted_files, upload)
        except Exception as e:
            log_usage('merge', success=False, error_message=str(e),
                      original_filename=base_file.filename)
            os.remove(base_path)
            for f in inserted_files:
                try:
                    os.remove(f)
                except Exception:
                    pass
            return jsonify({'error': f'Error al procesar PDFs: {str(e)}'}), 500

        timer = getattr(request, '_timer', None)
        duration = timer.end() if timer else 0

        for f in [base_path] + inserted_files:
            try:
                os.remove(f)
            except Exception:
                pass

        log_usage('merge', duration_ms=duration,
                  file_size=os.path.getsize(output_path),
                  original_filename=base_file.filename)

        @after_this_request
        def cleanup(resp):
            try:
                os.remove(output_path)
            except Exception:
                pass
            return resp

        return send_file(output_path, as_attachment=True, download_name='pdf_final_mergeado.pdf')

    @app.route('/merge-multiple')
    def merge_multiple():
        return render_template('merge-multi.html')

    @app.route('/merge-multi', methods=['POST'])
    def merge_multi():
        upload = current_app.config['UPLOAD_FOLDER']
        if 'files[]' not in request.files:
            return jsonify({'error': 'No se enviaron archivos'}), 400
        files = request.files.getlist('files[]')
        order_raw = request.form.get('order', '[]')
        try:
            order = json.loads(order_raw)
        except json.JSONDecodeError:
            return jsonify({'error': 'Orden inválido'}), 400
        if not order:
            return jsonify({'error': 'No hay archivos para unir'}), 400

        saved = []
        try:
            for f in files:
                if f.filename == '':
                    continue
                path = os.path.join(upload, secure_filename(f.filename))
                f.save(path)
                saved.append(path)

            writer = PdfWriter()
            total_pages = 0
            for idx in order:
                if idx < 0 or idx >= len(saved):
                    continue
                reader = PdfReader(saved[idx])
                for page in reader.pages:
                    writer.add_page(page)
                    total_pages += 1

            output = os.path.join(upload, 'merged_multi_output.pdf')
            with open(output, 'wb') as f:
                writer.write(f)

            file_names = [os.path.basename(p) for p in saved]
            log_usage('merge_multi', pages_in=sum(len(PdfReader(p).pages) for p in saved),
                      pages_out=total_pages, file_size=os.path.getsize(output),
                      original_filename=','.join(file_names))

            return jsonify({
                'pages': total_pages,
                'files': len(order),
                'size': os.path.getsize(output),
                'download': '/download-multi'
            })
        except Exception as e:
            log_usage('merge_multi', success=False, error_message=str(e),
                      original_filename=','.join([f.filename for f in files]) if files else None)
            return jsonify({'error': f'Error: {str(e)}'}), 500
        finally:
            for p in saved:
                try:
                    os.remove(p)
                except Exception:
                    pass

    @app.route('/download-multi')
    def download_multi():
        path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'merged_multi_output.pdf')
        if not os.path.exists(path):
            return jsonify({'error': 'Archivo no encontrado'}), 404

        @after_this_request
        def cleanup(resp):
            try:
                os.remove(path)
            except Exception:
                pass
            return resp

        return send_file(path, as_attachment=True, download_name='pdf_unido.pdf')

    @app.route('/page-count', methods=['POST'])
    def page_count():
        upload = current_app.config['UPLOAD_FOLDER']
        if 'pdf' not in request.files:
            return jsonify({'error': 'No se envió PDF'}), 400
        pdf_file = request.files['pdf']
        if pdf_file.filename == '':
            return jsonify({'error': 'Archivo vacío'}), 400

        tmp_path = os.path.join(upload, secure_filename(pdf_file.filename))
        pdf_file.save(tmp_path)
        try:
            reader = PdfReader(tmp_path)
            count = len(reader.pages)
        except Exception as e:
            os.remove(tmp_path)
            return jsonify({'error': f'Error al leer PDF: {str(e)}'}), 400
        os.remove(tmp_path)

        pages_text = ', '.join([str(i + 1) for i in range(count)])
        return jsonify({'pages': count, 'pagesList': pages_text})

    @app.route('/convert')
    def convert_page():
        return render_template('convert.html')

    @app.route('/crop')
    def crop_page():
        return render_template('crop.html')

    @app.route('/crop-pdf', methods=['POST'])
    def crop_pdf():
        upload = current_app.config['UPLOAD_FOLDER']
        if 'pdf' not in request.files:
            return jsonify({'error': 'Falta el PDF'}), 400
        pdf_file = request.files['pdf']
        crops_raw = request.form.get('crops', '[]')
        try:
            crops = json.loads(crops_raw)
        except json.JSONDecodeError:
            return jsonify({'error': 'Formato de recortes inválido'}), 400
        if not isinstance(crops, list) or len(crops) == 0:
            return jsonify({'error': 'No hay datos de recorte'}), 400

        tmp_path = os.path.join(upload, secure_filename(pdf_file.filename))
        pdf_file.save(tmp_path)

        try:
            reader = PdfReader(tmp_path)
            writer = PdfWriter()
            num_pages = len(reader.pages)

            for i, page in enumerate(reader.pages):
                c = crops[i] if i < len(crops) else crops[-1]
                mb = [float(x) for x in page.mediabox]
                pw = mb[2] - mb[0]
                ph = mb[3] - mb[1]

                x = c.get('x', 0.0)
                y_t = c.get('y', 0.0)
                w = c.get('w', 1.0)
                h = c.get('h', 1.0)
                if w < 0.01 or h < 0.01:
                    w, h = 1.0, 1.0

                llx = mb[0] + pw * x
                lly = mb[1] + ph * (1.0 - y_t - h)
                urx = mb[0] + pw * (x + w)
                ury = mb[1] + ph * (1.0 - y_t)

                page.cropbox = RectangleObject((llx, lly, urx, ury))
                for attr in ('trimbox', 'artbox', 'bleedbox'):
                    try:
                        setattr(page, attr, page.cropbox)
                    except Exception:
                        pass
                writer.add_page(page)

            output = os.path.join(upload, 'cropped_output.pdf')
            with open(output, 'wb') as f:
                writer.write(f)

            try:
                with pikepdf.open(output) as pdf:
                    pdf.save(output, compress_streams=True)
            except Exception:
                pass

            log_usage('crop_pdf', pages_in=num_pages, pages_out=num_pages,
                      file_size=os.path.getsize(tmp_path),
                      file_size_out=os.path.getsize(output),
                      original_filename=pdf_file.filename)

            @after_this_request
            def cleanup(resp):
                for p in [tmp_path, output]:
                    try:
                        os.remove(p)
                    except Exception:
                        pass
                return resp

            return send_file(
                output,
                as_attachment=True,
                download_name='pdf_recortado.pdf',
                mimetype='application/pdf'
            )
        except Exception as e:
            log_usage('crop_pdf', success=False, error_message=str(e),
                      original_filename=pdf_file.filename)
            return jsonify({'error': f'Error al recortar: {str(e)}'}), 500

    @app.route('/remove-pages')
    def remove_pages():
        return render_template('remove-pages.html')

    @app.route('/remove-pages-pdf', methods=['POST'])
    def remove_pages_pdf():
        upload = current_app.config['UPLOAD_FOLDER']
        if 'pdf' not in request.files:
            return jsonify({'error': 'Falta el PDF'}), 400
        pdf_file = request.files['pdf']
        pages_str = request.form.get('pages', '').strip()
        if not pages_str:
            return jsonify({'error': 'Especifica las páginas a eliminar'}), 400

        tmp_path = os.path.join(upload, secure_filename(pdf_file.filename))
        pdf_file.save(tmp_path)

        try:
            reader = PdfReader(tmp_path)
            total = len(reader.pages)
            to_remove = parse_pages_to_remove(pages_str, total)
            if not to_remove:
                return jsonify({'error': 'Ninguna página válida para eliminar (de 1 a ' + str(total) + ')'}), 400

            writer = PdfWriter()
            removed = 0
            for i in range(total):
                if (i + 1) in to_remove:
                    removed += 1
                    continue
                writer.add_page(reader.pages[i])

            if removed == 0:
                return jsonify({'error': 'Ninguna página coincide (1\u2013' + str(total) + ')'}), 400
            if len(writer.pages) == 0:
                return jsonify({'error': 'No puedes eliminar todas las páginas'}), 400

            output = os.path.join(upload, 'pages_removed_output.pdf')
            with open(output, 'wb') as f:
                writer.write(f)

            try:
                with pikepdf.open(output) as pdf:
                    pdf.save(output, compress_streams=True)
            except Exception:
                pass

            log_usage('remove_pages', pages_in=total, pages_out=len(writer.pages),
                      file_size=os.path.getsize(tmp_path),
                      file_size_out=os.path.getsize(output),
                      original_filename=pdf_file.filename)

            @after_this_request
            def cleanup(resp):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
                try:
                    os.remove(output)
                except Exception:
                    pass
                return resp

            return send_file(
                output,
                as_attachment=True,
                download_name='pdf_sin_paginas.pdf',
                mimetype='application/pdf'
            )
        except Exception as e:
            log_usage('remove_pages', success=False, error_message=str(e),
                      original_filename=pdf_file.filename)
            return jsonify({'error': f'Error: {str(e)}'}), 500

    @app.route('/reorder')
    def reorder_page():
        return render_template('reorder.html')

    @app.route('/reorder-pdf', methods=['POST'])
    def reorder_pdf():
        upload = current_app.config['UPLOAD_FOLDER']
        if 'pdf' not in request.files:
            return jsonify({'error': 'Falta el PDF'}), 400
        pdf_file = request.files['pdf']
        order_raw = request.form.get('order', '[]')
        try:
            order = json.loads(order_raw)
        except json.JSONDecodeError:
            return jsonify({'error': 'Formato de orden inválido'}), 400
        if not isinstance(order, list) or len(order) == 0:
            return jsonify({'error': 'Orden inválida'}), 400

        tmp_path = os.path.join(upload, secure_filename(pdf_file.filename))
        pdf_file.save(tmp_path)

        try:
            reader = PdfReader(tmp_path)
            total = len(reader.pages)

            for idx in order:
                if idx < 0 or idx >= total:
                    os.remove(tmp_path)
                    return jsonify({'error': f'Índice {idx} fuera de rango (0\u2013{total - 1})'}), 400

            if len(order) != total:
                os.remove(tmp_path)
                return jsonify({'error': f'Debe incluir todas las páginas ({total} páginas, se recibieron {len(order)})'}), 400

            writer = PdfWriter()
            for idx in order:
                writer.add_page(reader.pages[idx])

            output = os.path.join(upload, 'reordered_output.pdf')
            with open(output, 'wb') as f:
                writer.write(f)

            try:
                with pikepdf.open(output) as pdf:
                    pdf.save(output, compress_streams=True)
            except Exception:
                pass

            log_usage('reorder_pdf', pages_in=total, pages_out=total,
                      file_size=os.path.getsize(tmp_path),
                      file_size_out=os.path.getsize(output),
                      original_filename=pdf_file.filename)

            @after_this_request
            def cleanup(resp):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
                try:
                    os.remove(output)
                except Exception:
                    pass
                return resp

            return send_file(
                output,
                as_attachment=True,
                download_name='pdf_reordenado.pdf',
                mimetype='application/pdf'
            )
        except Exception as e:
            log_usage('reorder_pdf', success=False, error_message=str(e),
                      original_filename=pdf_file.filename)
            return jsonify({'error': f'Error al reordenar: {str(e)}'}), 500

    @app.route('/compress')
    def compress_page():
        return render_template('compress.html')

    @app.route('/compress-pdfs', methods=['POST'])
    def compress_pdfs():
        upload = current_app.config['UPLOAD_FOLDER']
        if 'files[]' not in request.files:
            return jsonify({'error': 'No se enviaron archivos'}), 400
        files = request.files.getlist('files[]')
        if not files or files[0].filename == '':
            return jsonify({'error': 'No se seleccionaron archivos'}), 400

        quality = request.form.get('quality', 'balanced')
        target_dpi_str = request.form.get('dpi', '150')
        remove_meta = request.form.get('remove_meta', '1') == '1'

        quality_map = {'high': 55, 'balanced': 35, 'low': 20, 'max': 10}
        jpeg_quality = quality_map.get(quality, 35)

        try:
            target_dpi = int(target_dpi_str) if target_dpi_str else None
        except ValueError:
            target_dpi = None

        saved = []
        out_paths = []
        total_original = 0
        total_pages = 0

        try:
            for f in files:
                if f.filename == '':
                    continue
                tmp_path = os.path.join(upload, secure_filename(f.filename))
                f.save(tmp_path)
                saved.append(tmp_path)
                total_original += os.path.getsize(tmp_path)

            for pdf_path in saved:
                out = compress_pdf(pdf_path, jpeg_quality, target_dpi, remove_meta,
                                   upload, current_app.logger)
                out_paths.append(out)
                reader = PdfReader(out)
                total_pages += len(reader.pages)

            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as z:
                for p in out_paths:
                    arcname = os.path.join('pdfs reducidos', os.path.basename(p))
                    z.write(p, arcname)

            total_compressed = zip_buf.tell()
            compression_ratio = round(total_compressed / total_original, 4) if total_original > 0 else None

            log_usage('compress_pdfs', file_size=total_original, pages_out=total_pages,
                      file_size_out=total_compressed,
                      compression_ratio=compression_ratio,
                      original_filename=';'.join(f.filename for f in files))

            zip_buf.seek(0)
            response = send_file(zip_buf, as_attachment=True,
                                 download_name='pdfs_reducidos.zip',
                                 mimetype='application/zip')
            response.headers['X-Original-Size'] = str(total_original)
            response.headers['X-Compressed-Size'] = str(total_compressed)
            response.headers['X-File-Count'] = str(len(out_paths))
            response.headers['X-Page-Count'] = str(total_pages)
            return response

        except Exception as e:
            log_usage('compress_pdfs', success=False, error_message=str(e),
                      original_filename=';'.join(f.filename for f in files) if files else None)
            return jsonify({'error': f'Error al comprimir: {str(e)}'}), 500
        finally:
            for p in saved + out_paths:
                try:
                    os.remove(p)
                except Exception:
                    pass
