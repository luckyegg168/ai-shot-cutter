"""ToolsPanel — 20 practical video editing tools in a dedicated tab."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
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
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.models import ExtractionError, FrameResult


class ToolsPanel(QWidget):
    """Video editing tools tab — 20 practical features."""

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

        # ── 11. Video Speed Change ────────────────────────────────────
        g11 = QGroupBox(self.tr("11. Video Speed Change"))
        g11_lay = QHBoxLayout(g11)
        g11_lay.addWidget(QLabel(self.tr("Speed:")))
        self._speed_spin = QDoubleSpinBox()
        self._speed_spin.setRange(0.25, 4.0)
        self._speed_spin.setValue(2.0)
        self._speed_spin.setSingleStep(0.25)
        g11_lay.addWidget(self._speed_spin)
        btn_speed = QPushButton(self.tr("Apply Speed"))
        btn_speed.clicked.connect(self._on_change_speed)
        g11_lay.addWidget(btn_speed)
        g11_lay.addStretch()
        layout.addWidget(g11)

        # ── 12. Frame Rotate / Flip ───────────────────────────────────
        g12 = QGroupBox(self.tr("12. Frame Rotate / Flip"))
        g12_lay = QHBoxLayout(g12)
        g12_lay.addWidget(QLabel(self.tr("Operation:")))
        self._rotate_combo = QComboBox()
        for label, val in [
            (self.tr("90° CW"), "90cw"),
            (self.tr("90° CCW"), "90ccw"),
            (self.tr("180°"), "180"),
            (self.tr("Horizontal Flip"), "hflip"),
            (self.tr("Vertical Flip"), "vflip"),
        ]:
            self._rotate_combo.addItem(label, val)
        g12_lay.addWidget(self._rotate_combo)
        btn_rotate = QPushButton(self.tr("Rotate / Flip"))
        btn_rotate.clicked.connect(self._on_rotate_frame)
        g12_lay.addWidget(btn_rotate)
        g12_lay.addStretch()
        layout.addWidget(g12)

        # ── 13. Video Thumbnail Generator ─────────────────────────────
        g13 = QGroupBox(self.tr("13. Video Thumbnail"))
        g13_lay = QHBoxLayout(g13)
        g13_lay.addWidget(QLabel(self.tr("At (sec):")))
        self._thumb_sec = QDoubleSpinBox()
        self._thumb_sec.setRange(0, 99999)
        self._thumb_sec.setValue(1.0)
        self._thumb_sec.setDecimals(1)
        g13_lay.addWidget(self._thumb_sec)
        g13_lay.addWidget(QLabel(self.tr("Width:")))
        self._thumb_width = QSpinBox()
        self._thumb_width.setRange(120, 3840)
        self._thumb_width.setValue(640)
        self._thumb_width.setSingleStep(40)
        g13_lay.addWidget(self._thumb_width)
        btn_thumb = QPushButton(self.tr("Generate Thumbnail"))
        btn_thumb.clicked.connect(self._on_generate_thumbnail)
        g13_lay.addWidget(btn_thumb)
        g13_lay.addStretch()
        layout.addWidget(g13)

        # ── 14. Frame Mosaic / Contact Sheet ──────────────────────────
        g14 = QGroupBox(self.tr("14. Contact Sheet"))
        g14_lay = QHBoxLayout(g14)
        g14_lay.addWidget(QLabel(self.tr("Columns:")))
        self._mosaic_cols = QSpinBox()
        self._mosaic_cols.setRange(2, 10)
        self._mosaic_cols.setValue(4)
        g14_lay.addWidget(self._mosaic_cols)
        g14_lay.addWidget(QLabel(self.tr("Tile width:")))
        self._mosaic_tile = QSpinBox()
        self._mosaic_tile.setRange(120, 960)
        self._mosaic_tile.setValue(320)
        self._mosaic_tile.setSingleStep(40)
        g14_lay.addWidget(self._mosaic_tile)
        btn_mosaic = QPushButton(self.tr("Create Sheet"))
        btn_mosaic.clicked.connect(self._on_contact_sheet)
        g14_lay.addWidget(btn_mosaic)
        g14_lay.addStretch()
        layout.addWidget(g14)

        # ── 15. Video Info / Stats ────────────────────────────────────
        g15 = QGroupBox(self.tr("15. Video Info"))
        g15_lay = QHBoxLayout(g15)
        btn_info = QPushButton(self.tr("Show Video Info"))
        btn_info.clicked.connect(self._on_video_info)
        g15_lay.addWidget(btn_info)
        g15_lay.addStretch()
        layout.addWidget(g15)

        # ── 16. Frame Crop ────────────────────────────────────────────
        g16 = QGroupBox(self.tr("16. Frame Crop"))
        g16_lay = QGridLayout(g16)
        g16_lay.addWidget(QLabel("X:"), 0, 0)
        self._crop_x = QSpinBox()
        self._crop_x.setRange(0, 9999)
        g16_lay.addWidget(self._crop_x, 0, 1)
        g16_lay.addWidget(QLabel("Y:"), 0, 2)
        self._crop_y = QSpinBox()
        self._crop_y.setRange(0, 9999)
        g16_lay.addWidget(self._crop_y, 0, 3)
        g16_lay.addWidget(QLabel(self.tr("Width:")), 1, 0)
        self._crop_w = QSpinBox()
        self._crop_w.setRange(1, 9999)
        self._crop_w.setValue(640)
        g16_lay.addWidget(self._crop_w, 1, 1)
        g16_lay.addWidget(QLabel(self.tr("Height:")), 1, 2)
        self._crop_h = QSpinBox()
        self._crop_h.setRange(1, 9999)
        self._crop_h.setValue(480)
        g16_lay.addWidget(self._crop_h, 1, 3)
        btn_crop = QPushButton(self.tr("Crop Frame"))
        btn_crop.clicked.connect(self._on_crop_frame)
        g16_lay.addWidget(btn_crop, 2, 0, 1, 4)
        layout.addWidget(g16)

        # ── 17. Reverse Video ─────────────────────────────────────────
        g17 = QGroupBox(self.tr("17. Reverse Video"))
        g17_lay = QHBoxLayout(g17)
        btn_reverse = QPushButton(self.tr("Reverse Video"))
        btn_reverse.clicked.connect(self._on_reverse_video)
        g17_lay.addWidget(btn_reverse)
        g17_lay.addStretch()
        layout.addWidget(g17)

        # ── 18. Extract All Frames ────────────────────────────────────
        g18 = QGroupBox(self.tr("18. Extract All Frames"))
        g18_lay = QHBoxLayout(g18)
        g18_lay.addWidget(QLabel(self.tr("Max frames (0=all):")))
        self._all_frames_max = QSpinBox()
        self._all_frames_max.setRange(0, 99999)
        self._all_frames_max.setValue(0)
        g18_lay.addWidget(self._all_frames_max)
        btn_all_frames = QPushButton(self.tr("Extract All"))
        btn_all_frames.clicked.connect(self._on_extract_all_frames)
        g18_lay.addWidget(btn_all_frames)
        g18_lay.addStretch()
        layout.addWidget(g18)

        # ── 19. Frame Deduplication ───────────────────────────────────
        g19 = QGroupBox(self.tr("19. Frame Deduplication"))
        g19_lay = QHBoxLayout(g19)
        g19_lay.addWidget(QLabel(self.tr("Threshold:")))
        self._dedup_threshold = QDoubleSpinBox()
        self._dedup_threshold.setRange(0.5, 1.0)
        self._dedup_threshold.setValue(0.95)
        self._dedup_threshold.setSingleStep(0.01)
        g19_lay.addWidget(self._dedup_threshold)
        btn_dedup = QPushButton(self.tr("Find Duplicates"))
        btn_dedup.clicked.connect(self._on_find_duplicates)
        g19_lay.addWidget(btn_dedup)
        g19_lay.addStretch()
        layout.addWidget(g19)

        # ── 20. Merge Videos ──────────────────────────────────────────
        g20 = QGroupBox(self.tr("20. Merge Videos"))
        g20_lay = QVBoxLayout(g20)
        self._merge_list_label = QLabel(self.tr("No files selected"))
        g20_lay.addWidget(self._merge_list_label)
        h20 = QHBoxLayout()
        btn_merge_add = QPushButton(self.tr("Add Videos"))
        btn_merge_add.clicked.connect(self._on_merge_add_files)
        h20.addWidget(btn_merge_add)
        btn_merge_go = QPushButton(self.tr("Merge"))
        btn_merge_go.clicked.connect(self._on_merge_videos)
        h20.addWidget(btn_merge_go)
        h20.addStretch()
        g20_lay.addLayout(h20)
        self._merge_file_list: list[Path] = []
        layout.addWidget(g20)

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

    # ------------------------------------------------------------------
    # Slot implementations — tools 11-20
    # ------------------------------------------------------------------
    def _on_change_speed(self) -> None:
        vp = self._require_video()
        if not vp:
            return
        dest, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save Speed-Changed Video"), "speed.mp4", "Video (*.mp4)"
        )
        if not dest:
            return
        from core.tools import change_video_speed
        try:
            out = change_video_speed(vp, Path(dest), self._speed_spin.value())
            self._result_label.setText(self.tr("Speed changed") + f": {out}")
            self._log(f"Video speed changed: {self._speed_spin.value()}x → {out}")
        except ExtractionError as e:
            QMessageBox.critical(self, self.tr("Error"), str(e))

    def _on_rotate_frame(self) -> None:
        frames = self._get_frames()
        if not frames:
            QMessageBox.warning(self, self.tr("No Frames"), self.tr("No frames available."))
            return
        src_path = frames[0].image_path
        dest, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save Rotated Frame"), "rotated.jpg", "Images (*.jpg)"
        )
        if not dest:
            return
        from core.tools import rotate_frame
        try:
            out = rotate_frame(src_path, Path(dest), self._rotate_combo.currentData())
            self._result_label.setText(self.tr("Frame rotated") + f": {out}")
            self._log(f"Frame rotated/flipped: {out}")
        except ExtractionError as e:
            QMessageBox.critical(self, self.tr("Error"), str(e))

    def _on_generate_thumbnail(self) -> None:
        vp = self._require_video()
        if not vp:
            return
        dest, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save Thumbnail"), "thumbnail.jpg", "Images (*.jpg)"
        )
        if not dest:
            return
        from core.tools import generate_thumbnail
        try:
            out = generate_thumbnail(vp, Path(dest), self._thumb_sec.value(), self._thumb_width.value())
            self._result_label.setText(self.tr("Thumbnail generated") + f": {out}")
            self._log(f"Thumbnail generated: {out}")
        except ExtractionError as e:
            QMessageBox.critical(self, self.tr("Error"), str(e))

    def _on_contact_sheet(self) -> None:
        frames = self._get_frames()
        if not frames:
            QMessageBox.warning(self, self.tr("No Frames"), self.tr("No frames available."))
            return
        dest, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save Contact Sheet"), "contact_sheet.jpg", "Images (*.jpg)"
        )
        if not dest:
            return
        from core.tools import create_contact_sheet
        try:
            paths = [f.image_path for f in frames]
            out = create_contact_sheet(
                paths, Path(dest), self._mosaic_cols.value(), self._mosaic_tile.value()
            )
            self._result_label.setText(self.tr("Contact sheet created") + f": {out}")
            self._log(f"Contact sheet: {len(frames)} frames → {out}")
        except ExtractionError as e:
            QMessageBox.critical(self, self.tr("Error"), str(e))

    def _on_video_info(self) -> None:
        vp = self._require_video()
        if not vp:
            return
        from core.tools import get_video_info
        try:
            info = get_video_info(vp)
            lines = [self.tr("Video Information:")]
            for k, v in info.items():
                lines.append(f"  {k}: {v}")
            self._result_label.setText("\n".join(lines))
            self._log(f"Video info retrieved: {vp.name}")
        except ExtractionError as e:
            QMessageBox.critical(self, self.tr("Error"), str(e))

    def _on_crop_frame(self) -> None:
        frames = self._get_frames()
        if not frames:
            QMessageBox.warning(self, self.tr("No Frames"), self.tr("No frames available."))
            return
        src_path = frames[0].image_path
        dest, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save Cropped Frame"), "cropped.jpg", "Images (*.jpg)"
        )
        if not dest:
            return
        from core.tools import crop_frame
        try:
            out = crop_frame(
                src_path, Path(dest),
                self._crop_x.value(), self._crop_y.value(),
                self._crop_w.value(), self._crop_h.value(),
            )
            self._result_label.setText(self.tr("Frame cropped") + f": {out}")
            self._log(f"Frame cropped: {out}")
        except ExtractionError as e:
            QMessageBox.critical(self, self.tr("Error"), str(e))

    def _on_reverse_video(self) -> None:
        vp = self._require_video()
        if not vp:
            return
        dest, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save Reversed Video"), "reversed.mp4", "Video (*.mp4)"
        )
        if not dest:
            return
        from core.tools import reverse_video
        try:
            out = reverse_video(vp, Path(dest))
            self._result_label.setText(self.tr("Video reversed") + f": {out}")
            self._log(f"Video reversed: {out}")
        except ExtractionError as e:
            QMessageBox.critical(self, self.tr("Error"), str(e))

    def _on_extract_all_frames(self) -> None:
        vp = self._require_video()
        if not vp:
            return
        dest_dir = QFileDialog.getExistingDirectory(
            self, self.tr("Select Output Folder for Frames")
        )
        if not dest_dir:
            return
        from core.tools import extract_all_frames
        try:
            out_frames = extract_all_frames(vp, Path(dest_dir), self._all_frames_max.value())
            self._result_label.setText(
                self.tr("Frames extracted") + f": {len(out_frames)} → {dest_dir}"
            )
            self._log(f"All frames extracted: {len(out_frames)} frames")
        except ExtractionError as e:
            QMessageBox.critical(self, self.tr("Error"), str(e))

    def _on_find_duplicates(self) -> None:
        frames = self._get_frames()
        if not frames:
            QMessageBox.warning(self, self.tr("No Frames"), self.tr("No frames available."))
            return
        from core.tools import find_duplicate_frames
        paths = [f.image_path for f in frames]
        dups = find_duplicate_frames(paths, self._dedup_threshold.value())
        if not dups:
            self._result_label.setText(self.tr("No duplicates found"))
            self._log("Dedup: no duplicates found")
            return
        lines = [self.tr("Duplicate frame pairs found") + f": {len(dups)}"]
        for a, b, sim in dups[:20]:
            lines.append(f"  Frame {a+1} ↔ {b+1}  (similarity: {sim:.3f})")
        if len(dups) > 20:
            lines.append("  …")
        self._result_label.setText("\n".join(lines))
        self._log(f"Dedup: {len(dups)} duplicate pairs found")

    def _on_merge_add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, self.tr("Select Videos to Merge"), "", "Video (*.mp4 *.mkv *.webm *.avi)"
        )
        if files:
            self._merge_file_list = [Path(f) for f in files]
            names = [Path(f).name for f in files]
            self._merge_list_label.setText(", ".join(names))

    def _on_merge_videos(self) -> None:
        if len(self._merge_file_list) < 2:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Please add at least 2 videos."))
            return
        dest, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save Merged Video"), "merged.mp4", "Video (*.mp4)"
        )
        if not dest:
            return
        from core.tools import merge_videos
        try:
            out = merge_videos(self._merge_file_list, Path(dest))
            self._result_label.setText(self.tr("Videos merged") + f": {out}")
            self._log(f"Videos merged: {len(self._merge_file_list)} → {out}")
        except ExtractionError as e:
            QMessageBox.critical(self, self.tr("Error"), str(e))
