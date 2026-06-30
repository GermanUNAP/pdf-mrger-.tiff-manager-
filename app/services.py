import os
import io
import tempfile
import shutil
from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject
from PIL import Image as PILImage
import img2pdf
import pikepdf


def merge_pdfs(base_path, insertions, inserted_files, upload_folder):
    insertions_sorted = sorted(
        enumerate(insertions),
        key=lambda x: int(x[1].get('afterPage', 0))
    )

    reader = PdfReader(base_path)
    total_base_pages = len(reader.pages)
    writer = PdfWriter()
    current_page = 0

    for idx, ins in insertions_sorted:
        after_page = int(ins.get('afterPage', 0))
        while current_page < after_page and current_page < total_base_pages:
            writer.add_page(reader.pages[current_page])
            current_page += 1
        ins_reader = PdfReader(inserted_files[idx])
        for ins_page in ins_reader.pages:
            writer.add_page(ins_page)

    while current_page < total_base_pages:
        writer.add_page(reader.pages[current_page])
        current_page += 1

    output_path = os.path.join(upload_folder, 'merged_output.pdf')
    with open(output_path, 'wb') as f:
        writer.write(f)
    return output_path


def parse_pages_to_remove(input_str, total):
    parts = [p.strip() for p in input_str.split(',')]
    to_remove = set()
    for part in parts:
        if '-' in part:
            a, b = part.split('-', 1)
            try:
                start, end = int(a.strip()), int(b.strip())
                for p in range(start, end + 1):
                    if 1 <= p <= total:
                        to_remove.add(p)
            except ValueError:
                continue
        else:
            try:
                p = int(part)
                if 1 <= p <= total:
                    to_remove.add(p)
            except ValueError:
                continue
    return sorted(to_remove)


def process_tiff_stream(tiff_path, quality, target_dpi, out_dir):
    paths = []
    basename = os.path.splitext(os.path.basename(tiff_path))[0]

    with PILImage.open(tiff_path) as img:
        n_frames = getattr(img, 'n_frames', 1)

        for i in range(n_frames):
            if hasattr(img, 'seek'):
                img.seek(i)
            page = img.copy()

            orig_dpi = None
            try:
                x_res = int(page.info.get('dpi', (0, 0))[0] or 0)
                if x_res > 0:
                    orig_dpi = x_res
            except Exception:
                pass

            if orig_dpi and target_dpi and orig_dpi > target_dpi:
                ratio = target_dpi / orig_dpi
                new_w = int(page.width * ratio)
                new_h = int(page.height * ratio)
                page = page.resize((new_w, new_h), PILImage.LANCZOS)

            q_val = 92 if quality == 'high' else 75 if quality == 'balanced' else 85
            out_path = os.path.join(out_dir, f'{basename}_p{i:04d}.jpg')

            if page.mode in ('1', 'L', 'LA'):
                if quality == 'lossless':
                    out_path = os.path.join(out_dir, f'{basename}_p{i:04d}.png')
                    if page.mode == '1':
                        page = page.convert('L')
                    page.save(out_path, format='PNG', optimize=True)
                else:
                    if page.mode == '1':
                        page = page.convert('L')
                    page.save(out_path, format='JPEG', quality=q_val, optimize=True)
            else:
                if page.mode == 'CMYK':
                    page = page.convert('RGB')
                elif page.mode == 'RGBA':
                    bg = PILImage.new('RGB', page.size, (255, 255, 255))
                    bg.paste(page, mask=page.split()[3])
                    page = bg
                elif page.mode != 'RGB':
                    page = page.convert('RGB')
                page.save(out_path, format='JPEG', quality=q_val, optimize=True)

            paths.append(out_path)
    return paths


def compress_pdf(pdf_path, jpeg_quality, target_dpi, remove_meta, output_dir, logger=None):
    basename = os.path.splitext(os.path.basename(pdf_path))[0]
    out_path = os.path.join(output_dir, f'{basename}_reducido.pdf')

    with pikepdf.open(pdf_path) as pdf:
        for page in pdf.pages:
            for name, image in page.images.items():
                try:
                    pil_image = image.as_pil_image()
                    if target_dpi:
                        orig_dpi = pil_image.info.get('dpi', (None, None))[0]
                        if orig_dpi and orig_dpi > target_dpi:
                            ratio = target_dpi / orig_dpi
                            new_w = int(pil_image.width * ratio)
                            new_h = int(pil_image.height * ratio)
                            pil_image = pil_image.resize((new_w, new_h), PILImage.LANCZOS)

                    if pil_image.mode in ('CMYK',):
                        pil_image = pil_image.convert('RGB')
                    elif pil_image.mode == 'RGBA':
                        bg = PILImage.new('RGB', pil_image.size, (255, 255, 255))
                        bg.paste(pil_image, mask=pil_image.split()[3])
                        pil_image = bg
                    elif pil_image.mode != 'RGB':
                        pil_image = pil_image.convert('RGB')

                    buf = io.BytesIO()
                    pil_image.save(buf, format='JPEG', quality=jpeg_quality, optimize=True)
                    buf.seek(0)
                    page.images[name] = pikepdf.Stream(pdf, buf.read())
                except Exception as e:
                    if logger:
                        logger.warning("Could not process image %s: %s", name, e)

        if remove_meta:
            for key in ('/Author', '/Title', '/Subject', '/Creator', '/Producer', '/Keywords'):
                try:
                    del pdf.docinfo[key]
                except (KeyError, ValueError):
                    pass

        pdf.save(out_path, compress_streams=True)
    return out_path


def init_cleanup(app):
    import atexit

    @atexit.register
    def cleanup_temp():
        upload_folder = app.config.get('UPLOAD_FOLDER', '')
        if upload_folder and os.path.exists(upload_folder):
            try:
                shutil.rmtree(upload_folder, ignore_errors=True)
            except Exception:
                pass
