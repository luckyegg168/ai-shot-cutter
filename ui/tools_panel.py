"""ToolsPanel — 10 practical video editing tools in a dedicated tab."""
from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import Qt, QRunnable, QThreadPool, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.models import ExtractionError, FrameResult


class ToolsPanel(QWidget):
    """Video editing tools tab — 10 practical features."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._video_path: Path | None = None
        self._all_frames_getter = None
        self._log_fn = None
        self._setup_ui()

    def set_video_path(self, path: Path) -> None:
        self._video_path = path
        self._video_label.setText(str(path.name) if path else self.tr("No video loaded"))

    def set_all_frames_getter(self, getter) -> None:
        self._all_frames_getter = getter

    def set_logger(self, log_fn) -> None:
        self._log_fn = log_fn

    def _log(self, msg: str) -> None:
        if self._log_fn:
            self._log_fn(msg)

    def _get_frames(self) -> list[FrameResult]:
        if self._all_frames_getter:
            return self._all_frames_getter()
        return []

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Video indicator
        self._video_label = QLabel(self.tr("No video loaded"))
        self._video_label.setStyleSheet("color: #89b4fa; font-weight: bold;")
        layout.addWidget(self._video_label)

        # ── 1. Scene Change Detection ─────────────────────────────────
        g1 = QGroupBox(self.tr("1. Scene Change Detection"))
        g1_lay = QHBoxLayout(g1)
        g1_lay.addWidget(QLabel(self.tr("Threshold:")))
        self._scene_threshold = QDoubleSpinBox()
        self._scene_threshold.setRange(0.05, 1.0)
        self._scene_threshold.setValue(0.3)
        self._scene_threshold.setSingleStep(0.05)
        g1_lay.addWidget(self._scene_threshold)
        btn_scene = QPushButton(self.tr("Detect Scenes"))
        btn_scene.clicked.connect(self._on_detect_scenes)
        g1_lay.addWidget(btn_scene)
        g1_lay.addStretch()
        layout.addWidget(g1)

        # ── 2. Video Trim ─────────────────────────────────────────────
        g2 = QGroupBox(self.tr("2. Video Trim"))
        g2_lay = QHBoxLayout(g2)
        g2_lay.addWidget(QLabel(self.tr("Start (sec):")))
        self._trim_start = QDoubleSpinBox()
        self._trim_start.setRange(0, 99999)
        self._trim_start.setDecimals(1)
        g2_lay.addWidget(self._trim_start)
        g2_lay.addWidget(QLabel(self.tr("End (sec):")))
        self._trim_end = QDoubleSpinBox()
        self._trim_end.setRange(0, 99999)
        self._trim_end.setDecimals(1)
        self._trim_end.setValue(30.0)
        g2_lay.addWidget(self._trim_end)
        btn_trim = QPushButton(self.tr("Trim"))
        btn_trim.clicked.connect(self._on_trim)
        g2_lay.addWidget(btn_trim)
        g2_lay.addStretch()
        layout.addWidget(g2)

        # ── 3. Frame Comparison ───────────────────────────────────────
        g3 = QGroupBox(self.tr("3. Frame Comparison"))
        g3_lay = QHBoxLayout(g3)
        g3_lay.addWidget(QLabel(self.tr("Frame A index:")))
        self._cmp_a = QSpinBox()
        self._cmp_a.setRange(1, 9999)
        self._cmp_a.setValue(1)
        g3_lay.addWidget(self._cmp_a)
        g3_lay.addWidget(QLabel(self.tr("Frame B index:")))
        self._cmp_b = QSpinBox()
        self._cmp_b.setRange(1, 9999)
        self._cmp_b.setValue(2)
        g3_lay.addWidget(self._cmp_b)
        btn_cmp = QPushButton(self.tr("Compare"))
        btn_cmp.clicked.connect(self._on_compare)
        g3_lay.addWidget(btn_cmp)
        g3_lay.addStretch()
        layout.addWidget(g3)

        # ── 4. GIF Preview Export ─────────────────────────────────────
        g4 = QGroupBox(self.tr("4. GIF Preview Export"))
        g4_lay = QHBoxLayout(g4)
        g4_lay.addWidget(QLabel(self.tr("FPS:")))
        self._gif_fps = QSpinBox()
        self._gif_fps.setRange(1, 10)
        self._gif_fps.setValue(2)
        g4_lay.addWidget(self._gif_fps)
        g4_lay.addWidget(QLabel(self.tr("Width:")))
        self._gif_width = QSpinBox()
        self._gif_width.setRange(120, 1920)
        self._gif_width.setValue(480)
        self._gif_width.setSingleStep(40)
        g4_lay.addWidget(self._gif_width)
        btn_gif = QPushButton(self.tr("Export GIF"))
        btn_gif.clicked.connect(self._on_export_gif)
        g4_lay.addWidget(btn_gif)
        g4_lay.addStretch()
        layout.addWidget(g4)

        # ── 5. Audio Extraction ───────────────────────────────────────
        g5 = QGroupBox(self.tr("5. Audio Extraction"))
        g5_lay = QHBoxLayout(g5)
        g5_lay.addWidget(QLabel(self.tr("Format:")))
        self._audio_fmt = QComboBox()
        self._audio_fmt.addItem("MP3", "mp3")
        self._audio_fmt.addItem("WAV", "wav")
        g5_lay.addWidget(self._audio_fmt)
        btn_audio = QPushButton(self.tr("Extract Audio"))
        btn_audio.clicked.connect(self._on_extract_audio)
        g5_lay.addWidget(btn_audio)
        g5_lay.addStretch()
        layout.addWidget(g5)

        # ── 6. Watermark Overlay ──────────────────────────────────────
        g6 = QGroupBox(self.tr("6. Text Watermark"))
        g6_lay = QGridLayout(g6)
        g6_lay.addWidget(QLabel(self.tr("Text:")), 0, 0)
        self._wm_text = QLineEdit()
        self._wm_text.setPlaceholderText("© My Channel 2025")
        g6_lay.addWidget(self._wm_text, 0, 1, 1, 2)
        g6_lay.addWidget(QLabel(self.tr("Position:")), 1, 0)
        self._wm_pos = QComboBox()
        for label, val in [
            (self.tr("Bottom Right"), "bottom_right"),
            (self.tr("Bottom Left"), "bottom_left"),
            (self.tr("Top Right"), "top_right"),
            (self.tr("Top Left"), "top_left"),
            (self.tr("Center"), "center"),
        ]:
            self._wm_pos.addItem(label, val)
        g6_lay.addWidget(self._wm_pos, 1, 1)
        btn_wm = QPushButton(self.tr("Add Watermark"))
        btn_wm.clicked.connect(self._on_add_watermark)
        g6_lay.addWidget(btn_wm, 1, 2)
        layout.addWidget(g6)

        # ── 7. Auto Best Frame ────────────────────────────────────────
        g7 = QGroupBox(self.tr("7. Auto Best Frame"))
        g7_lay = QHBoxLayout(g7)
        g7_lay.addWidget(QLabel(self.tr("Top N:")))
        self._best_n = QSpinBox()
        self._best_n.setRange(1, 50)
        self._best_n.setValue(5)
        g7_lay.addWidget(self._best_n)
        btn_best = QPushButton(self.tr("Find Best Frames"))
        btn_best.clicked.connect(self._on_find_best)
        g7_lay.addWidget(btn_best)
        g7_lay.addStretch()
        layout.addWidget(g7)

        # ── 8. SRT Subtitle Export ────────────────────────────────────
        g8 = QGroupBox(self.tr("8. SRT Subtitle Export"))
        g8_lay = QHBoxLayout(g8)
        g8_lay.addWidget(QLabel(self.tr("Duration per entry (sec):")))
        self._srt_dur = QDoubleSpinBox()
        self._srt_dur.setRange(1, 30)
        self._srt_dur.setValue(5.0)
        g8_lay.addWidget(self._srt_dur)
        btn_srt = QPushButton(self.tr("Export SRT"))
        btn_srt.clicked.connect(self._on_export_srt)
        g8_lay.addWidget(btn_srt)
        g8_lay.addStretch()
        layout.addWidget(g8)

        # ── 9. Batch Prompt Template ──────────────────────────────────
        g9 = QGroupBox(self.tr("9. Batch Prompt Template"))
        g9_lay = QVBoxLayout(g9)
        self._template_edit = QPlainTextEdit()
        self._template_edit.setFixedHeight(60)
        self._template_edit.setPlaceholderText(
            "{index}. [{timestamp}] {prompt}"
        )
        g9_lay.addWidget(self._template_edit)
        btn_tpl = QPushButton(self.tr("Render & Copy"))
        btn_tpl.clicked.connect(self._on_render_template)
        g9_lay.addWidget(btn_tpl)
        layout.addWidget(g9)

        # ── 10. Project Save / Load ───────────────────────────────────
        g10 = QGroupBox(self.tr("10. Project Save / Load"))
        g10_lay = QHBoxLayout(g10)
        btn_save_proj = QPushButton(self.tr("Save Project"))
        btn_save_proj.clicked.connect(self._on_save_project)
        btn_load_proj = QPushButton(self.tr("Load Project"))
        btn_load_proj.clicked.connect(self._on_load_project)
        g10_lay.addWidget(btn_save_proj)
        g10_lay.addWidget(btn_load_proj)
        g10_lay.addStretch()
        layout.addWidget(g10)

        # ── Result area ───────────────────────────────────────────────
        self._result_label = QLabel()
        self._result_label.setWordWrap(True)
        self._result_label.setStyleSheet("color: #a6e3a1; font-size: 12px;")
        layout.addWidget(self._result_label)

        layout.addStretch()
        scroll.setWidget(container)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    # ------------------------------------------------------------------
    # Slot implementations
    # ------------------------------------------------------------------
    def _require_video(self) -> Path | None:
        if not self._video_path or not self._video_path.exists():
            QMessageBox.warning(self, self.tr("No Video"), self.tr("Please run a job first to load a video."))
            return None
        return self._video_path

    def _on_detect_scenes(self) -> None:
        vp = self._require_video()
        if not vp:
            return
        from core.tools import detect_scene_changes
        try:
            ts = detect_scene_changes(vp, self._scene_threshold.value())
            msg = self.tr("Scene changes detected") + f": {len(ts)}\n"
            msg += ", ".join(f"{t:.1f}s" for t in ts[:20])
            if len(ts) > 20:
                msg += "…"
            self._result_label.setText(msg)
            self._log(f"Scene detection: {len(ts)} changes found")
        except ExtractionError as e:
            QMessageBox.critical(self, self.tr("Error"), str(e))

    def _on_trim(self) -> None:
        vp = self._require_video()
        if not vp:
            return
        dest, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save Trimmed Video"), "trimmed.mp4", "Video (*.mp4)"
        )
        if not dest:
            return
        from core.tools import trim_video
        try:
            out = trim_video(vp, self._trim_start.value(), self._trim_end.value(), Path(dest))
            self._result_label.setText(self.tr("Trimmed video saved") + f": {out}")
            self._log(f"Video trimmed: {out}")
        except ExtractionError as e:
            QMessageBox.critical(self, self.tr("Error"), str(e))

    def _on_compare(self) -> None:
        frames = self._get_frames()
        if not frames:
            QMessageBox.warning(self, self.tr("No Frames"), self.tr("No frames available."))
            return
        idx_a = self._cmp_a.value() - 1
        idx_b = self._cmp_b.value() - 1
        if idx_a < 0 or idx_a >= len(frames) or idx_b < 0 or idx_b >= len(frames):
            QMessageBox.warning(self, self.tr("Error"), self.tr("Frame index out of range."))
            return
        dest, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save Comparison"), "comparison.jpg", "Images (*.jpg)"
        )
        if not dest:
            return
        from core.tools import compare_frames
        try:
            out = compare_frames(frames[idx_a].image_path, frames[idx_b].image_path, Path(dest))
            self._result_label.setText(self.tr("Comparison saved") + f": {out}")
        except ExtractionError as e:
            QMessageBox.critical(self, self.tr("Error"), str(e))

    def _on_export_gif(self) -> None:
        frames = self._get_frames()
        if not frames:
            QMessageBox.warning(self, self.tr("No Frames"), self.tr("No frames available."))
            return
        dest, _ = QFileDialog.getSaveFileName(
            self, self.tr("Export GIF"), "preview.gif", "GIF (*.gif)"
        )
        if not dest:
            return
        from core.tools import export_gif
        try:
            paths = [f.image_path for f in frames]
            out = export_gif(paths, Path(dest), self._gif_fps.value(), self._gif_width.value())
            self._result_label.setText(self.tr("GIF exported") + f": {out}")
            self._log(f"GIF exported: {out}")
        except ExtractionError as e:
            QMessageBox.critical(self, self.tr("Error"), str(e))

    def _on_extract_audio(self) -> None:
        vp = self._require_video()
        if not vp:
            return
        fmt = self._audio_fmt.currentData()
        dest, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save Audio"), f"audio.{fmt}", f"Audio (*.{fmt})"
        )
        if not dest:
            return
        from core.tools import extract_audio
        try:
            out = extract_audio(vp, Path(dest), fmt)
            self._result_label.setText(self.tr("Audio extracted") + f": {out}")
            self._log(f"Audio extracted: {out}")
        except ExtractionError as e:
            QMessageBox.critical(self, self.tr("Error"), str(e))

    def _on_add_watermark(self) -> None:
        vp = self._require_video()
        if not vp:
            return
        text = self._wm_text.text().strip()
        if not text:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Please enter watermark text."))
            return
        dest, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save Watermarked Video"), "watermarked.mp4", "Video (*.mp4)"
        )
        if not dest:
            return
        from core.tools import add_text_watermark
        try:
            out = add_text_watermark(vp, Path(dest), text, self._wm_pos.currentData())
            self._result_label.setText(self.tr("Watermark added") + f": {out}")
            self._log(f"Watermark added: {out}")
        except ExtractionError as e:
            QMessageBox.critical(self, self.tr("Error"), str(e))

    def _on_find_best(self) -> None:
        frames = self._get_frames()
        if not frames:
            QMessageBox.warning(self, self.tr("No Frames"), self.tr("No frames available."))
            return
        from core.tools import rank_frames_by_sharpness
        paths = [f.image_path for f in frames]
        ranked = rank_frames_by_sharpness(paths, self._best_n.value())
        lines = [self.tr("Best frames by sharpness:")]
        for i, (p, score) in enumerate(ranked, 1):
            lines.append(f"  {i}. {p.name}  (score: {score:.1f})")
        self._result_label.setText("\n".join(lines))
        self._log(f"Best frame analysis: {len(ranked)} frames ranked")

    def _on_export_srt(self) -> None:
        frames = self._get_frames()
        if not frames:
            QMessageBox.warning(self, self.tr("No Frames"), self.tr("No frames available."))
            return
        dest, _ = QFileDialog.getSaveFileName(
            self, self.tr("Export SRT"), "subtitles.srt", "SRT (*.srt)"
        )
        if not dest:
            return
        from core.tools import export_srt
        try:
            out = export_srt(frames, Path(dest), self._srt_dur.value())
            self._result_label.setText(self.tr("SRT exported") + f": {out}")
            self._log(f"SRT exported: {out}")
        except ExtractionError as e:
            QMessageBox.critical(self, self.tr("Error"), str(e))

    def _on_render_template(self) -> None:
        frames = self._get_frames()
        if not frames:
            QMessageBox.warning(self, self.tr("No Frames"), self.tr("No frames available."))
            return
        tpl = self._template_edit.toPlainText().strip()
        if not tpl:
            tpl = "{index}. [{timestamp}] {prompt}"
        from core.tools import render_prompt_template
        text = render_prompt_template(tpl, frames)
        QApplication.clipboard().setText(text)
        self._result_label.setText(self.tr("Template rendered & copied") + f" ({len(frames)} frames)")
        self._log(f"Template rendered: {len(frames)} frames")

    def _on_save_project(self) -> None:
        frames = self._get_frames()
        if not frames:
            QMessageBox.warning(self, self.tr("No Frames"), self.tr("No frames available to save."))
            return
        dest, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save Project"), "project.json", "JSON (*.json)"
        )
        if not dest:
            return
        from core.tools import save_project
        config_dict = {}
        if self._video_path:
            config_dict["video_path"] = str(self._video_path)
        save_project(Path(dest), config_dict, frames)
        self._result_label.setText(self.tr("Project saved") + f": {dest}")
        self._log(f"Project saved: {dest}")

    def _on_load_project(self) -> None:
        src, _ = QFileDialog.getOpenFileName(
            self, self.tr("Load Project"), "", "JSON (*.json)"
        )
        if not src:
            return
        from core.tools import load_project
        try:
            config_dict, frames = load_project(Path(src))
            # Signal to parent to load frames
            self._loaded_frames = frames
            self._loaded_config = config_dict
            vp = config_dict.get("video_path", "")
            if vp:
                self._video_path = Path(vp)
                self._video_label.setText(Path(vp).name)
            self._result_label.setText(
                self.tr("Project loaded") + f": {len(frames)} frames\n"
                + self.tr("Use gallery to view loaded frames.")
            )
            self._log(f"Project loaded: {len(frames)} frames from {src}")

            # Emit frames to gallery if parent connected load handler
            if hasattr(self, "project_loaded") and callable(self.project_loaded):
                self.project_loaded(config_dict, frames)
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), str(e))
