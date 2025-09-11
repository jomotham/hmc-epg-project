
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtGui import QPixmap, QPainter, QColor, QGuiApplication
from PyQt6.QtCore import Qt, QRectF




def svg_to_colored_pixmap(svg_path: str, color: str, size_px: int) -> QPixmap:
    """Render SVG at device-pixel resolution and tint it with 'color' (keeps AA)."""
    renderer = QSvgRenderer(svg_path)


    # Render at device pixel ratio so it’s crisp on HiDPI
    dpr = QGuiApplication.primaryScreen().devicePixelRatio()
    w = int(size_px * dpr)
    h = int(size_px * dpr)

    pm = QPixmap(w, h)
    pm.fill(Qt.GlobalColor.transparent)

    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(p, QRectF(0, 0, w, h))

    # Tint while preserving the original anti-aliased alpha
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    p.fillRect(pm.rect(), QColor(color))
    p.end()

    pm.setDevicePixelRatio(dpr)
    return pm

