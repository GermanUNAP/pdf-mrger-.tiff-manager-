import os
import io
import shutil
from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject
from PIL import Image as PILImage
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


def compress_pdf(pdf_path, jpeg_quality, target_dpi, remove_meta, output_dir, logger=None):
    basename = os.path.splitext(os.path.basename(pdf_path))[0]
    out_path = os.path.join(output_dir, f'{basename}_reducido.pdf')

    with pikepdf.open(pdf_path) as pdf:
        processed = 0
        failed = 0
        for page in pdf.pages:
            for name, image in page.images.items():
                try:
                    pil_image = None
                    try:
                        pil_image = image.as_pil_image()
                    except Exception:
                        try:
                            raw = image.stream.read_bytes()
                            pil_image = PILImage.open(io.BytesIO(raw))
                        except Exception:
                            if logger:
                                logger.debug("Could not decode image %s, skipping", name)

                    if pil_image is None:
                        failed += 1
                        continue

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
                    processed += 1
                except Exception as e:
                    failed += 1
                    if logger:
                        logger.debug("Could not process image %s: %s", name, e)

        if failed and logger:
            logger.info("Compressed %d images, skipped %d unsupported images", processed, failed)

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
