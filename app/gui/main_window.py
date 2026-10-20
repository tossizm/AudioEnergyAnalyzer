from pathlib import Path
from datetime import datetime
import json
import av
import time
import numpy as np

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QFrame, QPushButton, QFileDialog, QHBoxLayout, QHeaderView,
    QAbstractItemView, QMessageBox, QStackedWidget, QLineEdit, QGridLayout,
    QDialog, QDialogButtonBox, QApplication, QProgressBar
)
from PySide6.QtCore import Signal, Qt, QThread, QObject, QSettings, QTimer, QElapsedTimer
from PySide6.QtGui import QFont, QColor, QShortcut

SUPPORTED={".mp3",".wav",".aif",".aiff"}


class DropArea(QFrame):
    file_dropped=Signal(str)
    json_dropped=Signal(str)
    band_customization_requested=Signal()
    ratio_reference_requested=Signal()

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setObjectName("dropArea")
        self.setStyleSheet("QFrame#dropArea{background:#010066;border:0;} QLabel{color:#FFFFFF;} QPushButton{background:#72C6EF;color:#0000FF;font-weight:bold;border:0;border-radius:5px;}")

        self.label=QLabel("ここへドラッグ＆ドロップ\nオーディオサンプル（MP3 / WAV / AIFF）\nリファレンスデータ（JSON）", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(False)

        self.applied=QLabel("", self)
        self.applied.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.applied.setWordWrap(False)

        self.set_genre_button=QPushButton("リファレンスデータ設定", self)
        self.set_genre_button.clicked.connect(self.choose_config)

        self.ratio_button=QPushButton("比率リファレンス設定", self)
        self.ratio_button.clicked.connect(self.ratio_reference_requested.emit)

        self.band_button=QPushButton("帯域カスタマイズ", self)
        self.band_button.clicked.connect(self.band_customization_requested.emit)

        self._load_saved_config()
        self._position_widgets()

    def resizeEvent(self,e):
        super().resizeEvent(e)
        self._position_widgets()

    def _position_widgets(self):
        w,h=self.width(),self.height()
        pad=40
        self.label.setGeometry(pad,125,w-pad*2,150)
        self.applied.setGeometry(pad,350,w-pad*2,80)
        by=h-pad-50
        bw=271
        self.set_genre_button.setGeometry(pad,by,bw,50)
        self.ratio_button.setGeometry((w-bw)//2,by,bw,50)
        self.band_button.setGeometry(w-pad-bw,by,bw,50)

    def _settings(self):
        # Keep the legacy namespace so existing ClubAudioAnalyzer preferences remain available.
        return QSettings("ClubAudioAnalyzer","ClubAudioAnalyzer")

    def _appdata_dir(self):
        from PySide6.QtCore import QStandardPaths
        path=Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
        path.mkdir(parents=True,exist_ok=True)
        return path

    def _bundled_default(self):
        from app.main import resource_path
        return resource_path("config/Reference_Average_Default.json")

    def _selected_cache(self):
        from app.main import resource_path
        config_dir=resource_path("config")
        config_dir.mkdir(parents=True,exist_ok=True)
        return config_dir/"selected_config.json"

    def _load_saved_config(self):
        settings=self._settings()
        # First launch always starts from the single bundled default reference.
        cache=self._selected_cache()
        if settings.value("initial_reference_loaded", False, type=bool) is not True:
            source=self._bundled_default()
            cache.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            candidate=cache
            settings.setValue("initial_reference_loaded", True)
            settings.setValue("selected_config_path", str(cache))
            settings.setValue("selected_config_filename", source.name)
        else:
            saved=settings.value("selected_config_path", "")
            candidate=Path(saved) if saved else cache
            if not candidate.is_file():
                source=self._bundled_default()
                cache.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
                candidate=cache
            settings.setValue("selected_config_path", str(candidate))
        self.config_path=candidate
        self._update_applied()

    def choose_config(self):
        from app.main import resource_path
        default_dir=str(resource_path("config"))
        path,_=QFileDialog.getOpenFileName(self,"リファレンスデータJSONを選択",default_dir,"JSON Files (*.json)")
        if path:
            self.apply_dropped_config(path)

    def _update_applied(self):
        try:
            data=json.loads(self.config_path.read_text(encoding="utf-8"))
            name=str(data.get("name",self.config_path.stem))
            name=name.replace(f" — {data.get('bpm')} BPM club target","")
            self.applied.setText(f"リファレンスデータ：\n{name}")
        except Exception:
            self.applied.setText(f"リファレンスデータ：\n{self.config_path.name}")

    def current_config_path(self):
        return self.config_path

    def current_config_filename(self):
        saved=self._settings().value("selected_config_filename","")
        return saved or self.config_path.name

    def dragEnterEvent(self,e):
        if e.mimeData().hasUrls() and any(Path(u.toLocalFile()).suffix.lower() in SUPPORTED.union({".json"}) for u in e.mimeData().urls()):
            e.acceptProposedAction()

    def dropEvent(self,e):
        for u in e.mimeData().urls():
            p=u.toLocalFile(); ext=Path(p).suffix.lower()
            if ext==".json":
                self.apply_dropped_config(p)
                e.acceptProposedAction(); return
            if ext in SUPPORTED:
                self.file_dropped.emit(p)
                e.acceptProposedAction(); return

    def apply_dropped_config(self,path):
        try:
            src=Path(path); data=json.loads(src.read_text(encoding="utf-8"))
            if not isinstance(data,dict) or "target_db" not in data:
                raise ValueError("target_db がありません")
            if len(data.get("target_db",[])) != 10:
                raise ValueError("target_db は10帯域分必要です")
            cache=self._selected_cache()
            cache.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            self._settings().setValue("selected_config_path",str(cache))
            self._settings().setValue("selected_config_filename",src.name)
            self.config_path=cache
            self._update_applied()
        except Exception as e:
            QMessageBox.critical(self,"Reference Data Error",f"JSONを適用できません：{e}")


class BandCustomizationPage(QWidget):
    home_requested=Signal()
    applied=Signal()

    DEFAULT_MAXIMA=[60,120,250,500,1000,2000,5000,10000,16000]

    def __init__(self, font):
        super().__init__()
        self.font=font
        self.setStyleSheet("QWidget{background:#000000;} QLabel{color:#FFFFFF;font-weight:bold;} QPushButton{font-weight:bold;border-radius:5px;}")

        self.title=QLabel("帯域カスタマイズ設定", self)
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setFont(font)
        self.title.setStyleSheet("background:#0000FF;color:#FFFFFF;font-weight:bold;")

        self.inputs=[]
        self.rows=[]
        self._build_rows()

        self.status=QLabel("①～⑨の最大Hz値を入力してください。", self)
        self.status.setFont(font)
        self.status.setAlignment(Qt.AlignCenter)

        self.home_button=QPushButton("初期画面へ戻る", self)
        self.apply_button=QPushButton("帯域カスタマイズ設定を決定", self)
        self.save_settings_button=QPushButton("設定を保存", self)
        self.load_settings_button=QPushButton("設定を適用", self)
        self.default_settings_button=QPushButton("デフォルトに戻す", self)
        for b in (self.home_button,self.apply_button,self.save_settings_button,self.load_settings_button,self.default_settings_button):
            b.setFont(font)
            b.setMinimumHeight(max(44, font.pointSize()+20))
        self.home_button.setStyleSheet("QPushButton{background:#72C6EF;color:#0000FF;font-weight:bold;border:0;border-radius:5px;padding:8px 16px;}")
        self.apply_button.setStyleSheet("QPushButton{background:#ED1A3D;color:#FFFFFF;font-weight:bold;border:0;border-radius:5px;padding:8px 16px;}")
        self.save_settings_button.setStyleSheet("QPushButton{background:#72C6EF;color:#0000FF;font-weight:bold;border:0;border-radius:5px;padding:8px 16px;}")
        self.load_settings_button.setStyleSheet("QPushButton{background:#72C6EF;color:#0000FF;font-weight:bold;border:0;border-radius:5px;padding:8px 16px;}")
        self.default_settings_button.setStyleSheet("QPushButton{background:#72C6EF;color:#0000FF;font-weight:bold;border:0;border-radius:5px;padding:8px 16px;}")
        self.home_button.clicked.connect(self.home_requested.emit)
        self.apply_button.clicked.connect(self._apply)
        self.save_settings_button.clicked.connect(self._save_band_settings)
        self.load_settings_button.clicked.connect(self._load_band_settings_file)
        self.default_settings_button.clicked.connect(self._restore_default)

        self._position_all()
        self._validate()

    def _band_file_payload(self):
        from app.analysis.spectrum import build_band_settings_payload
        maxima=[int(edit.text().strip()) for edit in self.inputs]
        return build_band_settings_payload(maxima)

    def _save_band_settings(self):
        if not self._validate():
            return
        default_name = "band_settings.json"
        path, _ = QFileDialog.getSaveFileName(self, "帯域設定を保存", default_name, "JSON Files (*.json)")
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        Path(path).write_text(json.dumps(self._band_file_payload(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _load_band_settings_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "帯域設定を適用", "", "JSON Files (*.json)")
        if not path:
            return
        try:
            data=json.loads(Path(path).read_text(encoding="utf-8"))
            bands=data.get("bands")
            if not isinstance(bands,list) or len(bands)!=10:
                raise ValueError("10バンド分の設定が必要です。")
            edges=[int(bands[0]["min_hz"])] + [int(b["max_hz"]) for b in bands]
            if edges[0] != 20 or edges[-1] != 20000:
                raise ValueError("最小20 Hz・最大20000 Hzが必要です。")
            for i in range(10):
                if int(bands[i]["min_hz"]) != edges[i] or int(bands[i]["max_hz"]) != edges[i+1] or edges[i] >= edges[i+1]:
                    raise ValueError("帯域が連続していません。")
            self.load_values(edges[1:10])
        except Exception as e:
            QMessageBox.critical(self, "帯域設定エラー", f"帯域設定を適用できません：{e}")

    def _restore_default(self):
        self.load_values(self.DEFAULT_MAXIMA[:])

    def _build_rows(self):
        nums="①②③④⑤⑥⑦⑧⑨⑩"
        for i in range(10):
            row={}
            row["num"] = nums[i]
            row["min"] = QLabel("", self)
            row["min"].setFont(self.font)
            row["min"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row["min"].setStyleSheet("background:transparent;color:#FFFFFF;font-weight:bold;")

            row["unit1"] = QLabel("Hz", self)
            row["unit1"].setFont(self.font)
            row["unit1"].setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            row["unit1"].setStyleSheet("background:transparent;color:#FFFFFF;font-weight:bold;")

            row["tilde"] = QLabel("～", self)
            row["tilde"].setFont(self.font)
            row["tilde"].setAlignment(Qt.AlignCenter)
            row["tilde"].setStyleSheet("background:transparent;color:#FFFFFF;font-weight:bold;")

            if i < 9:
                edit=QLineEdit(self)
                edit.setFont(self.font)
                edit.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                edit.setStyleSheet("QLineEdit{background:#000000;color:#FFFF00;font-weight:bold;padding:2px 5px;border:1px solid #FFFFFF;border-radius:4px;}")
                edit.setMinimumHeight(self.font.pointSize()+10)
                edit.setText(str(self.DEFAULT_MAXIMA[i]))
                edit.textChanged.connect(self._validate)
                edit.editingFinished.connect(lambda idx=i: self._validate(show_alert=True, focus_index=idx))
                self.inputs.append(edit)
                row["max"]=edit
            else:
                fixed=QLabel("20000", self)
                fixed.setFont(self.font)
                fixed.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                fixed.setStyleSheet("background:transparent;color:#FFFFFF;font-weight:bold;")
                row["max"]=fixed

            row["unit2"] = QLabel("Hz", self)
            row["unit2"].setFont(self.font)
            row["unit2"].setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            row["unit2"].setStyleSheet("background:transparent;color:#FFFFFF;font-weight:bold;")
            self.rows.append(row)

    def _fullwidth_px(self):
        # One Japanese full-width character at the actual row font size.
        fm=self.fontMetrics()
        return max(1, fm.horizontalAdvance("　"))

    def _position_all(self):
        w=self.width() or 1100
        margin=40
        self.title.setGeometry(0,0,w,33)

        # Center the complete "xx Hz　～　xx Hz" unit. Sequence labels are omitted.
        fw=self._fullwidth_px()
        min_w=115; unit_w=32; tilde_w=32; box_w=126
        gap_num_hz=8; gap_hz_tilde=2*fw; gap_tilde_box=fw; gap_box_hz=fw
        total=min_w+gap_num_hz+unit_w+gap_hz_tilde+tilde_w+gap_tilde_box+box_w+gap_box_hz+unit_w
        x0=int((w-total)/2)
        y0=73
        row_h=27
        row_gap=1
        for i,row in enumerate(self.rows):
            y=y0+i*(row_h+row_gap)
            x=x0
            row["min"].setGeometry(x,y,min_w,row_h); x+=min_w+gap_num_hz
            row["unit1"].setGeometry(x,y,unit_w,row_h); x+=unit_w+gap_hz_tilde
            row["tilde"].setGeometry(x,y,tilde_w,row_h); x+=tilde_w+gap_tilde_box
            row["max"].setGeometry(x,y,box_w,row_h); x+=box_w+gap_box_hz
            row["unit2"].setGeometry(x,y,unit_w,row_h)

        # 40 px above and below the status row.
        self.status.setGeometry(margin,504,w-margin*2,0)
        status_y=504
        status_h=0
        # Use a compact one-line status area, leaving the requested 40 px separation.
        status_y=392
        status_h=36
        self.status.setGeometry(margin,status_y,w-margin*2,status_h)

        # Bottom controls: 40 px bottom margin. Home left; decision right.
        button_y=550-40-42
        self.home_button.setGeometry(margin,button_y,230,42)
        self.apply_button.setGeometry(w-margin-308,button_y,308,42)

        # Save / Apply / Default controls are vertically stacked at right-center.
        sx=w-margin-190; sy=195; bw=190; bh=42; gap=12
        self.save_settings_button.setGeometry(sx,sy,bw,bh)
        self.load_settings_button.setGeometry(sx,sy+bh+gap,bw,bh)
        self.default_settings_button.setGeometry(sx,sy+(bh+gap)*2,bw,bh)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self._position_all()

    def load_values(self,maxima):
        vals=[int(v) for v in maxima]
        if len(vals)!=9:
            vals=self.DEFAULT_MAXIMA[:]
        for i,v in enumerate(vals):
            self.inputs[i].setText(str(v))
        self._validate()

    def _set_invalid(self,edit,invalid):
        if invalid:
            edit.setStyleSheet("QLineEdit{background:#AF011C;color:#000000;font-weight:bold;padding:2px 5px;border:1px solid #FFFFFF;border-radius:4px;}")
        else:
            edit.setStyleSheet("QLineEdit{background:#000000;color:#FFFF00;font-weight:bold;padding:2px 5px;border:1px solid #FFFFFF;border-radius:4px;}")

    def _validate(self,*_,show_alert=False,focus_index=None):
        valid=True; errors_by_index={}; previous=20
        for i,edit in enumerate(self.inputs):
            text=edit.text().strip(); ok=True; message=None
            if not text or not text.isascii() or not text.isdigit():
                ok=False; message=f"{i+1}番目：プラスの整数を入力してください。"
            else:
                value=int(text)
                if value < 20: ok=False; message=f"{i+1}番目：20以上で入力してください。"
                elif value > 20000: ok=False; message=f"{i+1}番目：20000以下で入力してください。"
                elif value <= previous: ok=False; message=f"{i+1}番目：前の最大Hz値より大きくしてください。"
                previous=value
            self._set_invalid(edit,not ok)
            valid &= ok
            if message: errors_by_index[i]=message

        for i,row in enumerate(self.rows):
            if i==0:
                row["min"].setText("20")
            else:
                prev=self.inputs[i-1].text().strip()
                row["min"].setText(prev if prev.isascii() and prev.isdigit() else "")

        self.apply_button.setVisible(valid)
        if valid:
            self.status.setText("設定可能です。")
            self.status.setStyleSheet("background:transparent;border:1px solid #FFFFFF;color:#FFFFFF;font-weight:bold;")
        else:
            self.status.setText("入力内容を確認してください。")
            self.status.setStyleSheet("background:transparent;border:1px solid #ED1A3D;color:#ED1A3D;font-weight:bold;")
        if show_alert and errors_by_index:
            idx=focus_index if focus_index in errors_by_index else next(iter(errors_by_index))
            QMessageBox.warning(self,"帯域設定エラー",errors_by_index[idx])
        return valid

    def _apply(self):
        if not self._validate(): return
        maxima=[int(e.text()) for e in self.inputs]
        from app.analysis.spectrum import set_band_maxima
        set_band_maxima(maxima)
        QSettings("ClubAudioAnalyzer","ClubAudioAnalyzer").setValue("band_maxima",json.dumps(maxima))
        self.applied.emit()


class RatioReferencePage(QWidget):
    home_requested=Signal()
    applied=Signal(object)

    def __init__(self, font, reference_path_provider=None):
        super().__init__()
        self.font=font
        self.reference_path_provider=reference_path_provider
        self.setStyleSheet("QWidget{background:#000000;} QLabel{color:#FFFFFF;font-weight:bold;} QPushButton{font-weight:bold;border-radius:5px;}")
        self.title=QLabel("10バンド比率リファレンス設定", self)
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setFont(font)
        self.title.setStyleSheet("background:#0000FF;color:#FFFFFF;font-weight:bold;")
        self.inputs=[]; self.rows=[]
        self._build_rows()
        self.total=QLabel("合計：0.00 %", self); self.total.setFont(font); self.total.setAlignment(Qt.AlignCenter)
        self.status=QLabel("10バンドの合計を100.00%にしてください。", self); self.status.setFont(font); self.status.setAlignment(Qt.AlignCenter)
        self.home_button=QPushButton("初期画面へ戻る", self)
        self.apply_button=QPushButton("比率リファレンス設定を決定", self)
        self.default_button=QPushButton("デフォルトに戻す", self)
        for b in (self.home_button,self.apply_button,self.default_button):
            b.setFont(font); b.setMinimumHeight(max(44,font.pointSize()+20))
        self.home_button.setStyleSheet("QPushButton{background:#72C6EF;color:#0000FF;font-weight:bold;border:0;border-radius:5px;padding:8px 16px;}")
        self.default_button.setStyleSheet("QPushButton{background:#72C6EF;color:#0000FF;font-weight:bold;border:0;border-radius:5px;padding:8px 16px;}")
        self.apply_button.setStyleSheet("QPushButton{background:#ED1A3D;color:#FFFFFF;font-weight:bold;border:0;border-radius:5px;padding:8px 16px;}")
        self.home_button.clicked.connect(self.home_requested.emit)
        self.apply_button.clicked.connect(self._apply)
        self.default_button.clicked.connect(self._restore_default)
        self._position_all()
        self._validate()

    def _build_rows(self):
        from app.analysis.spectrum import BANDS
        for lo,hi,name in BANDS:
            row=QFrame(self); row.setStyleSheet("QFrame{background:#000000;border:0;}")
            band=QLabel(name,row); band.setAlignment(Qt.AlignRight|Qt.AlignVCenter); band.setFont(self.font)
            edit=QLineEdit(row); edit.setFont(self.font); edit.setAlignment(Qt.AlignRight|Qt.AlignVCenter); edit.setMaxLength(7)
            edit.textChanged.connect(self._validate)
            unit=QLabel("%",row); unit.setAlignment(Qt.AlignLeft|Qt.AlignVCenter); unit.setFont(self.font)
            self.inputs.append(edit); self.rows.append((row,band,edit,unit))

    def _position_all(self):
        w,h=self.width(),self.height(); margin=40
        self.title.setGeometry(0,0,w,55)
        row_h=31; top=66
        for i,(row,band,edit,unit) in enumerate(self.rows):
            y=top+i*row_h
            row.setGeometry(margin,y,w-margin*2,row_h)
            band.setGeometry(0,0,360,row_h)
            edit.setGeometry(380,0,126,row_h)
            unit.setGeometry(516,0,50,row_h)
        self.total.setGeometry(0,382,w,34)
        self.status.setGeometry(margin,420,w-margin*2,34)
        by=h-margin-44
        self.home_button.setGeometry(margin,by,240,44)
        self.default_button.setGeometry((w-240)//2,by,240,44)
        self.apply_button.setGeometry(w-margin-350,by,350,44)

    def resizeEvent(self,event):
        super().resizeEvent(event); self._position_all()

    def refresh_band_labels(self):
        from app.analysis.spectrum import BANDS
        for (lo,hi,name),(row,band,edit,unit) in zip(BANDS,self.rows):
            band.setText(name)

    def load_values(self,values):
        vals=[float(v) for v in values]
        if len(vals)!=10:
            vals=[10.0]*10
        # Display two decimals while keeping the displayed total exactly 100.00%.
        vals=[round(v,2) for v in vals]
        correction=round(100.0-sum(vals),2)
        if correction:
            vals[int(np.argmax(vals))]+=correction
        for edit,v in zip(self.inputs,vals): edit.setText(f"{float(v):.2f}")
        self._validate()

    def _restore_default(self):
        from app.analysis.ratio_targeting import default_ratio_from_target_db
        try:
            data=json.loads(Path(self.reference_path_provider()).read_text(encoding="utf-8"))
            precise=default_ratio_from_target_db(data["target_db"]).tolist()
        except Exception:
            from app.analysis.spectrum import BANDS
            precise=[100.0/len(BANDS)]*len(BANDS)
        self.load_values(precise)
        self.reference_precise_values=list(precise)
        self.reference_original_values=self.values()

    def _set_style(self,edit,invalid):
        if invalid:
            edit.setStyleSheet("QLineEdit{background:#AF011C;color:#000000;font-weight:bold;padding:2px 5px;border:1px solid #FFFFFF;border-radius:4px;}")
        else:
            edit.setStyleSheet("QLineEdit{background:#000000;color:#FFFF00;font-weight:bold;padding:2px 5px;border:1px solid #FFFFFF;border-radius:4px;}")

    def _validate(self,*_):
        import math
        vals=[]; valid=True
        for i,edit in enumerate(self.inputs):
            text=edit.text().strip(); ok=True
            try:
                v=float(text)
                # Only BAND10 (16000–20000 Hz) may be exactly 0.00%.
                # A zero value in any of BAND1–BAND9 remains invalid.
                if not math.isfinite(v) or v < 0.0 or v>100.0 or (i < 9 and v == 0.0): ok=False
            except Exception:
                ok=False; v=0.0
            self._set_style(edit,not ok); valid &= ok; vals.append(v)
        total=sum(vals)
        self.total.setText(f"合計：{total:.2f} %")
        total_ok=abs(total-100.0)<=0.005
        valid=valid and total_ok
        self.apply_button.setVisible(valid)
        if valid:
            self.status.setText("設定可能です。")
            self.status.setStyleSheet("background:transparent;border:1px solid #FFFFFF;color:#FFFFFF;font-weight:bold;")
        else:
            self.status.setText("入力内容を確認してください。合計は100.00%です。")
            self.status.setStyleSheet("background:transparent;border:1px solid #ED1A3D;color:#ED1A3D;font-weight:bold;")
        return valid

    def values(self):
        if not self._validate(): return None
        return [float(e.text().strip()) for e in self.inputs]

    def _apply(self):
        vals=self.values()
        if vals is None: return
        QSettings("ClubAudioAnalyzer","ClubAudioAnalyzer").setValue("ratio_target_percent",json.dumps(vals))
        self.applied.emit(vals)


class ProcessingProgressPage(QFrame):
    """Progress view used during audio loading/analysis operations."""
    def __init__(self, font):
        super().__init__()
        self.setObjectName("processingProgressPage")
        self.setStyleSheet("QFrame#processingProgressPage{background:#010066;border:0;} QLabel{color:#FFFFFF;font-weight:bold;}")
        self.stage_label=QLabel("", self)
        self.stage_label.setAlignment(Qt.AlignCenter)
        self.stage_label.setWordWrap(False)
        self.stage_label.setFont(font)
        self.elapsed_label=QLabel("経過時間：00:00", self)
        self.elapsed_label.setAlignment(Qt.AlignCenter)
        self.elapsed_label.setFont(font)

        self.progress_bar=QProgressBar(self)
        self.progress_bar.setRange(0,100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(
            "QProgressBar{background:transparent;border:2px solid #000000;border-radius:0;}"
            "QProgressBar::chunk{background:#ED1A3D;border:none;}"
        )

        self._timer=QElapsedTimer()
        self._clock=QTimer(self)
        self._clock.setInterval(100)
        self._clock.timeout.connect(self._refresh_elapsed)
        self._layout_widgets()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_widgets()

    def _layout_widgets(self):
        w,h=self.width(),self.height()
        self.stage_label.setGeometry(40,max(80,int(h*0.33)-34),w-80,54)
        self.elapsed_label.setGeometry(40,max(135,int(h*0.49)),w-80,42)
        bar_w=max(300,w-160)
        self.progress_bar.setGeometry((w-bar_w)//2,max(195,int(h*0.62)),bar_w,36)

    @staticmethod
    def _mmss(ms):
        total=max(0,int(ms/1000))
        return f"{total//60:02d}:{total%60:02d}"

    def start(self, text=""):
        self.stage_label.setText(text)
        self.elapsed_label.setText("経過時間：00:00")
        self.progress_bar.setValue(0)
        self._timer.start()
        self._clock.start()

    def update(self, text, percent):
        self.stage_label.setText(text)
        self.progress_bar.setValue(max(0,min(100,int(percent))))
        self._refresh_elapsed()

    def finish(self, text=None):
        if text is not None:
            self.stage_label.setText(text)
        if self._timer.isValid():
            self._refresh_elapsed()
        self._clock.stop()

    def _refresh_elapsed(self):
        if self._timer.isValid():
            self.elapsed_label.setText(f"経過時間：{self._mmss(self._timer.elapsed())}")


class AnalysisWorker(QObject):
    progress=Signal(str,int); finished=Signal(object); failed=Signal(str)
    def __init__(self,path,target_path,config_filename):
        super().__init__(); self.path=path; self.target_path=target_path; self.config_filename=config_filename
    def run(self):
        try:
            from app.analysis.pipeline import analyze_file
            def cb(stage,pct): self.progress.emit(stage,pct)
            started=time.perf_counter()
            r=analyze_file(self.path,self.target_path,cb)
            r.config_filename=self.config_filename
            if self.path.suffix.lower()==".mp3":
                try:
                    with av.open(str(self.path)) as c:
                        rates=[int(s.bit_rate) for s in c.streams.audio if getattr(s,"bit_rate",None)]
                        r.bitrate_kbps=round(max(rates)/1000) if rates else None
                except Exception:
                    r.bitrate_kbps=None
            r.analysis_elapsed_seconds=max(0.0,time.perf_counter()-started)
            self.finished.emit(r)
        except Exception as e:self.failed.emit(str(e))


class ReferenceWorker(QObject):
    progress=Signal(str,int); finished=Signal(object); failed=Signal(str)
    def __init__(self,path,source_config_path):
        super().__init__(); self.path=path; self.source_config_path=source_config_path
    def run(self):
        try:
            from app.analysis.pipeline import generate_reference_config
            def cb(stage,pct): self.progress.emit(stage,pct)
            data=generate_reference_config(self.path,self.source_config_path,cb)
            self.finished.emit(data)
        except Exception as e:self.failed.emit(str(e))


class RatioEQDialog(QDialog):
    def __init__(self, result, parent=None):
        super().__init__(parent)
        self.setWindowTitle("10バンド比率EQ調整結果")
        self.resize(980,620)
        lay=QVBoxLayout(self); lay.setContentsMargins(12,12,12,12)
        status="収束しました" if result.converged else "許容誤差内へ収束しませんでした"
        head=QLabel(f"{status}　|　反復回数：{result.iterations}　|　最大誤差：{result.max_abs_error_pct:.3f} %")
        head.setStyleSheet("font-weight:bold;")
        lay.addWidget(head)
        table=QTableWidget(10,6,self)
        table.setHorizontalHeaderLabels(["Band","Pre %","Target %","Post %","Diff %","EQ"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        for i,(lo,hi,name) in enumerate(__import__('app.analysis.spectrum',fromlist=['BANDS']).BANDS):
            gain=float(result.eq_gains_db[i])
            vals=[f"{int(lo)} ~ {int(hi)} Hz",f"{result.pre_pct[i]:.2f} %",f"{result.target_pct[i]:.2f} %",f"{result.post_pct[i]:.2f} %",f"{result.residual_pct[i]:+.2f} %",f"{gain:+.2f} dB" if abs(gain)>=0.01 else "0.00 dB"]
            for j,v in enumerate(vals):
                item=QTableWidgetItem(v); item.setTextAlignment(Qt.AlignCenter); table.setItem(i,j,item)
        lay.addWidget(table)
        note=QLabel("このEQは既存のtarget_db判定とは独立した、10バンド比率一致用の推奨EQです。音源ファイル自体は変更しません。")
        note.setWordWrap(True); lay.addWidget(note)
        buttons=QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject); buttons.accepted.connect(self.accept)
        lay.addWidget(buttons)


class RatioEQWorker(QObject):
    finished=Signal(object); failed=Signal(str); progress=Signal(str,int)
    def __init__(self,path,target_pct):
        super().__init__(); self.path=Path(path); self.target_pct=target_pct
    def run(self):
        try:
            from app.analysis.spectrum import load_audio
            from app.analysis.ratio_targeting import optimize_ratio_eq
            ext=self.path.suffix.lower()
            if ext==".mp3":
                self.progress.emit("decode",0)
                x,sr=load_audio(self.path,lambda p:self.progress.emit("decode",p))
            else:
                self.progress.emit("load",0)
                x,sr=load_audio(self.path,lambda p:self.progress.emit("load",p))
            self.progress.emit("ratio",10)
            result=optimize_ratio_eq(x,sr,self.target_pct)
            self.progress.emit("ratio",100)
            self.finished.emit(result)
        except Exception as e:
            self.failed.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Club Audio Analyzer")
        self.resize(1100,550)
        self.setMinimumSize(700,400)
        base=QFont("Segoe UI")
        system_size=QApplication.font().pointSizeF()
        base_size=system_size if system_size>0 else 10.0
        base.setPointSizeF(base_size*1.32)
        self.setFont(base)
        self.current_result=None; self.current_ratio_target=None; self.ratio_result=None; self.thread=None; self.worker=None; self.ratio_thread=None; self.ratio_worker=None
        self.stack=QStackedWidget(); self.setCentralWidget(self.stack)

        self._load_band_settings()
        startup_size=base_size*1.76
        startup_font=QFont("Segoe UI"); startup_font.setPointSizeF(startup_size)

        self.drop=DropArea()
        self.drop.file_dropped.connect(self.start_analysis)
        self.drop.band_customization_requested.connect(self.open_band_customization)
        self.drop.ratio_reference_requested.connect(self.open_ratio_reference)
        for w in (self.drop,self.drop.label,self.drop.applied,self.drop.set_genre_button,self.drop.ratio_button,self.drop.band_button):
            w.setFont(startup_font)
        self._scale_button(self.drop.set_genre_button,1.5)
        self._scale_button(self.drop.ratio_button,1.5)
        self._scale_button(self.drop.band_button,1.5)
        self.stack.addWidget(self.drop)

        self.progress_page=ProcessingProgressPage(startup_font)
        self.stack.addWidget(self.progress_page)

        self.band_page=BandCustomizationPage(startup_font)
        self.band_page.home_requested.connect(self.return_home)
        self.band_page.applied.connect(self.band_settings_applied)
        self.stack.addWidget(self.band_page)
        self.ratio_page=RatioReferencePage(startup_font, self.drop.current_config_path)
        self.ratio_page.home_requested.connect(self.return_home)
        self.ratio_page.applied.connect(self.ratio_settings_applied)
        self.stack.addWidget(self.ratio_page)
        self._apply_band_page_sizes()

        self.result=QWidget(); rl=QVBoxLayout(self.result); rl.setContentsMargins(12,12,12,12)
        top_result_row=QHBoxLayout()
        self.config_info=QLabel("リファレンスデータ：-"); top_result_row.addWidget(self.config_info,1)
        self.ratio_eq_button=QPushButton("目標比率へEQ調整"); self.ratio_eq_button.setEnabled(False)
        self.ratio_eq_button.setStyleSheet("QPushButton{background:#ED1A3D;color:#FFFFFF;font-weight:bold;padding:8px 14px;border-radius:5px;} QPushButton:hover{background:#C91435;} QPushButton:disabled{background:#777777;}")
        top_result_row.addWidget(self.ratio_eq_button)
        rl.addLayout(top_result_row)
        self.info=QLabel("ファイル未解析"); rl.addWidget(self.info)
        row=QHBoxLayout()
        self.save_button=QPushButton("分析結果データ生成"); self.save_button.setEnabled(False)
        self.save_button.setStyleSheet("QPushButton{background:#27AE60;color:white;font-weight:bold;padding:8px 16px;border-radius:5px;} QPushButton:hover{background:#219653;} QPushButton:disabled{background:#95A5A6;}")
        self.save_button.clicked.connect(self.save_result); row.addWidget(self.save_button)
        self.reference_button=QPushButton("リファレンスデータ生成"); self.reference_button.setEnabled(False)
        self.reference_button.setStyleSheet("QPushButton{background:#010066;color:white;font-weight:bold;padding:10px 18px;border-radius:5px;} QPushButton:hover{background:#020099;} QPushButton:disabled{background:#777777;}")
        self.reference_button.clicked.connect(self.generate_reference); row.addWidget(self.reference_button)
        self.ratio_eq_button.clicked.connect(self.start_ratio_eq)
        self.home_button=QPushButton("初期画面に戻る"); self.home_button.clicked.connect(self.return_home); row.addWidget(self.home_button)
        for _btn in (self.save_button,self.reference_button,self.home_button):
            _f=_btn.font(); _f.setPointSizeF(_f.pointSizeF()*1.5); _btn.setFont(_f)
        _f=self.ratio_eq_button.font(); _f.setPointSizeF(_f.pointSizeF()*1.5); self.ratio_eq_button.setFont(_f); self.ratio_eq_button.setMinimumSize(250,44)
        self._equalize_buttons(self.save_button,self.reference_button,self.home_button)
        row.addStretch(); rl.addLayout(row)
        # Five global measurements are placed between the three action buttons and the result table.
        self.metrics_row=QHBoxLayout()
        self.metric_labels={}
        for key in ("Peak", "RMS", "TruePeak", "Integrated LUFS", "クレストファクター", "全体相関"):
            lab=QLabel(f"{key}：-")
            lab.setAlignment(Qt.AlignCenter)
            lab.setMinimumHeight(34)
            self.metric_labels[key]=lab
            self.metrics_row.addWidget(lab,1)
        rl.addLayout(self.metrics_row)
        self.ratio_status=QLabel(""); self.ratio_status.setAlignment(Qt.AlignCenter); self.ratio_status.setVisible(False); rl.addWidget(self.ratio_status)
        self.table=QTableWidget(0,9); self.table.setHorizontalHeaderLabels(["Band","Sample %","Target %","Correlation","Post %","Diff","Sample dB","Target dB","EQ"])
        # Match the lower table's text size to the base font used by the Peak–overall-correlation metric row.
        self.table.setFont(self.metric_labels["Peak"].font())
        h=self.table.horizontalHeader(); h.setFont(self.metric_labels["Peak"].font()); h.setSectionsMovable(False); h.setSectionResizeMode(QHeaderView.Interactive); h.setStretchLastSection(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers); self.table.setWordWrap(False)
        rl.addWidget(self.table)
        self.stack.addWidget(self.result)
        self.stack.setCurrentWidget(self.drop)

    @staticmethod
    def _scale_button(btn,factor):
        size=btn.sizeHint(); btn.setMinimumSize(int(size.width()*factor),int(size.height()*factor))

    @staticmethod
    def _equalize_buttons(*buttons):
        sizes=[b.sizeHint() for b in buttons]
        w=max(s.width() for s in sizes); h=max(s.height() for s in sizes)
        for b in buttons: b.setFixedSize(w,h)

    def _load_band_settings(self):
        from app.analysis.spectrum import set_band_maxima
        raw=QSettings("ClubAudioAnalyzer","ClubAudioAnalyzer").value("band_maxima","")
        if raw:
            try:
                vals=json.loads(raw)
                set_band_maxima(vals)
                return
            except Exception:
                pass
        set_band_maxima([60,120,250,500,1000,2000,5000,10000,16000])

    def _apply_band_page_sizes(self):
        self._equalize_buttons(self.band_page.home_button,self.band_page.apply_button)

    def open_band_customization(self):
        from app.analysis.spectrum import BANDS
        self.band_page.load_values([b[1] for b in BANDS[:9]])
        self.stack.setCurrentWidget(self.band_page)

    def open_ratio_reference(self):
        from app.analysis.ratio_targeting import default_ratio_from_target_db
        data=json.loads(self.drop.current_config_path().read_text(encoding="utf-8"))
        vals=default_ratio_from_target_db(data.get("target_db",[])).tolist()
        self.ratio_page.refresh_band_labels()
        self.ratio_page.load_values(vals)
        self.ratio_page.reference_precise_values=list(vals)
        self.ratio_page.reference_original_values=self.ratio_page.values()
        self.stack.setCurrentWidget(self.ratio_page)

    def ratio_settings_applied(self,vals):
        from app.analysis.ratio_targeting import default_ratio_from_target_db, target_db_from_ratio, validate_ratio_target
        config_path=self.drop.current_config_path()
        try:
            data=json.loads(config_path.read_text(encoding="utf-8"))
            original=getattr(self.ratio_page,"reference_original_values",None)
            precise=getattr(self.ratio_page,"reference_precise_values",None)
            if original is not None and precise is not None and all(abs(float(vals[i])-float(original[i]))<1e-9 for i in range(10)):
                # Confirming the unchanged rounded display must not turn a tiny
                # nonzero reference band (shown as 0.00%) into an actual zero.
                self.current_ratio_target=list(map(float,default_ratio_from_target_db(data.get("target_db",[]))))
                self.stack.setCurrentWidget(self.drop)
                return
            effective=[]
            for i,value in enumerate(vals):
                if original is not None and precise is not None and abs(float(value)-float(original[i]))<1e-9:
                    effective.append(float(precise[i]))
                else:
                    effective.append(float(value))
            total=sum(effective)
            if total<=0:
                raise ValueError("比率合計が0です。")
            effective=[v*100.0/total for v in effective]
            effective=validate_ratio_target(effective).tolist()
            converted=target_db_from_ratio(effective, data.get("target_db",[]))
            data["target_db"]=[round(float(v),2) for v in converted]
            config_path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            self.current_ratio_target=effective
            self.drop._update_applied()
            self.stack.setCurrentWidget(self.drop)
        except Exception as exc:
            QMessageBox.critical(self,"比率リファレンス設定エラー",f"selected_config.json を更新できません：{exc}")

    def band_settings_applied(self):
        self.stack.setCurrentWidget(self.drop)

    def start_analysis(self,path):
        if self.thread is not None:return
        self.current_audio_path=Path(path)
        self.current_result=None; self.ratio_result=None; self.save_button.setEnabled(False); self.reference_button.setEnabled(False); self.ratio_eq_button.setEnabled(False); self.table.clearContents(); self.table.setRowCount(0); self.ratio_status.setVisible(False)
        for key in self.metric_labels: self.metric_labels[key].setText(f"{key}：-")
        self.stack.setCurrentWidget(self.progress_page)
        ext=self.current_audio_path.suffix.lower()
        start_text="① オーディオをデコード中です" if ext==".mp3" else "① オーディオを読み込み中です"
        self.progress_page.start(start_text)
        config_filename=self.drop.current_config_filename(); target_path=self.drop.current_config_path()
        self.thread=QThread(self); self.worker=AnalysisWorker(Path(path),target_path,config_filename); self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run); self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.analysis_finished); self.worker.failed.connect(self.analysis_failed)
        self.worker.finished.connect(self.thread.quit); self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater); self.thread.finished.connect(self.thread_cleanup); self.thread.start()

    def update_progress(self,stage,pct):
        # Normal analysis combines audio loading and analysis into one 0–100 progress bar.
        if stage in ("decode", "load"):
            text="① オーディオをデコード中です" if stage=="decode" else "① オーディオを読み込み中です"
            overall=int(float(pct)*0.30)
        else:
            text="② オーディオを分析中です"
            overall=30+int(float(pct)*0.70)
        self.progress_page.update(text,overall)

    def analysis_finished(self,r): self.progress_page.finish(); self.show_result(r); self.reference_button.setEnabled(True); self.ratio_eq_button.setEnabled(True); self.stack.setCurrentWidget(self.result)

    def _ratio_target_available(self):
        from app.analysis.ratio_targeting import validate_ratio_target
        raw=QSettings("ClubAudioAnalyzer","ClubAudioAnalyzer").value("ratio_target_percent","")
        if not raw: return False
        try:
            validate_ratio_target(json.loads(raw)); return True
        except Exception:
            return False

    def _current_ratio_target(self):
        from app.analysis.ratio_targeting import default_ratio_from_target_db, validate_ratio_target
        data=json.loads(self.drop.current_config_path().read_text(encoding="utf-8"))
        vals=default_ratio_from_target_db(data.get("target_db",[]))
        return validate_ratio_target(vals).tolist()

    def start_ratio_eq(self):
        if self.current_result is None or self.ratio_thread is not None: return
        target=self._current_ratio_target()
        self.ratio_result=None
        self.ratio_eq_button.setEnabled(False); self.save_button.setEnabled(False); self.reference_button.setEnabled(False)
        self.progress_page.start("④ 目標比率EQを計算中です")
        path=getattr(self,"current_audio_path",None)
        if not path:
            self.ratio_eq_button.setEnabled(True); return
        self.ratio_thread=QThread(self); self.ratio_worker=RatioEQWorker(path,target); self.ratio_worker.moveToThread(self.ratio_thread)
        self.ratio_thread.started.connect(self.ratio_worker.run); self.ratio_worker.progress.connect(self.update_ratio_progress)
        self.ratio_worker.finished.connect(self.ratio_eq_finished); self.ratio_worker.failed.connect(self.ratio_eq_failed)
        self.ratio_worker.finished.connect(self.ratio_thread.quit); self.ratio_worker.failed.connect(self.ratio_thread.quit)
        self.ratio_thread.finished.connect(self.ratio_worker.deleteLater); self.ratio_thread.finished.connect(self.ratio_thread_cleanup)
        self.stack.setCurrentWidget(self.progress_page); self.ratio_thread.start()

    def update_ratio_progress(self,stage,pct):
        if stage in ("decode", "load"):
            text="④ オーディオをデコード中です" if stage=="decode" else "④ オーディオを読み込み中です"
            overall=int(float(pct)*0.30)
        else:
            text="④ 目標比率EQを計算中です"
            overall=30+int(float(pct)*0.70)
        self.progress_page.update(text,overall)

    def ratio_eq_finished(self,result):
        self.progress_page.finish()
        self.ratio_result=result; self.stack.setCurrentWidget(self.result)
        self.ratio_status.setText(f"目標比率EQ：最大誤差 {result.max_abs_error_pct:.3f} % / 反復 {result.iterations} / {'収束' if result.converged else '未収束'}")
        self.ratio_status.setStyleSheet("color:#ED1A3D;font-weight:bold;")
        self.ratio_status.setVisible(True); self.ratio_eq_button.setEnabled(True); self.save_button.setEnabled(True); self.reference_button.setEnabled(True)
        dlg=RatioEQDialog(result,self); dlg.exec()

    def ratio_eq_failed(self,msg):
        self.progress_page.finish()
        QMessageBox.critical(self,"Ratio EQ Error",msg); self.stack.setCurrentWidget(self.result); self.ratio_eq_button.setEnabled(True); self.save_button.setEnabled(True); self.reference_button.setEnabled(True)

    def ratio_thread_cleanup(self):
        if getattr(self,"ratio_thread",None): self.ratio_thread.deleteLater()
        self.ratio_thread=None; self.ratio_worker=None

    def generate_reference(self):
        if self.current_result is None or self.thread is not None:
            return
        source_path=self.drop.current_config_path()
        audio_path=getattr(self,"current_audio_path",Path(self.current_result.filename))
        if not audio_path.is_file():
            QMessageBox.critical(self,"Reference Error","解析元オーディオファイルが見つかりません。")
            return
        self.reference_button.setEnabled(False); self.save_button.setEnabled(False)
        self.stack.setCurrentWidget(self.progress_page)
        self.progress_page.start("③ リファレンスデータを分析中です")
        self.reference_thread=QThread(self); self.reference_worker=ReferenceWorker(audio_path,source_path); self.reference_worker.moveToThread(self.reference_thread)
        self.reference_thread.started.connect(self.reference_worker.run); self.reference_worker.progress.connect(self.update_reference_progress)
        self.reference_worker.finished.connect(self.reference_finished); self.reference_worker.failed.connect(self.reference_failed)
        self.reference_worker.finished.connect(self.reference_thread.quit); self.reference_worker.failed.connect(self.reference_thread.quit)
        self.reference_thread.finished.connect(self.reference_worker.deleteLater); self.reference_thread.finished.connect(self.reference_thread_cleanup); self.reference_thread.start()

    def update_reference_progress(self,stage,pct):
        if stage in ("decode", "load"):
            text="③ オーディオをデコード中です" if stage=="decode" else "③ オーディオを読み込み中です"
            overall=int(float(pct)*0.30)
        else:
            text="③ リファレンスデータを分析中です"
            overall=30+int(float(pct)*0.70)
        self.progress_page.update(text,overall)

    def reference_finished(self,data):
        self.progress_page.finish()
        self.stack.setCurrentWidget(self.result); self.save_reference_config(data)

    def reference_failed(self,msg):
        self.progress_page.finish()
        QMessageBox.critical(self,"Reference Error",msg); self.reference_button.setEnabled(True); self.save_button.setEnabled(True); self.stack.setCurrentWidget(self.result)

    def reference_thread_cleanup(self):
        if getattr(self,"reference_thread",None): self.reference_thread.deleteLater()
        self.reference_thread=None; self.reference_worker=None

    def save_reference_config(self,data):
        audio_name=Path(getattr(self,"current_audio_path",Path(self.current_result.filename))).stem
        default=f"reference_{audio_name}.json"
        path,_=QFileDialog.getSaveFileName(self,"リファレンスデータをJSON保存",default,"JSON Files (*.json)")
        if path:
            if not path.lower().endswith(".json"): path += ".json"
            Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        self.reference_button.setEnabled(True); self.save_button.setEnabled(True)

    def return_home(self):
        if self.thread is not None or getattr(self,"reference_thread",None) is not None or getattr(self,"ratio_thread",None) is not None:
            return
        if self.stack.currentWidget() is self.result and self.current_result is not None:
            box=QMessageBox(self)
            box.setIcon(QMessageBox.Question)
            box.setWindowTitle("分析結果")
            box.setText("移動すると分析結果が失われます。分析データを保存しますか？")
            yes=box.addButton("YES(Y)", QMessageBox.YesRole)
            no=box.addButton("NO(N)", QMessageBox.NoRole)
            box.setDefaultButton(yes)
            shortcut_y=QShortcut("Y", box)
            shortcut_n=QShortcut("N", box)
            shortcut_y.activated.connect(yes.click)
            shortcut_n.activated.connect(no.click)
            box.exec()
            if box.clickedButton() is yes:
                if not self.save_result():
                    return
            elif box.clickedButton() is not no:
                return
        self.current_result=None; self.current_audio_path=None; self.ratio_result=None
        self.save_button.setEnabled(False); self.reference_button.setEnabled(False); self.ratio_eq_button.setEnabled(False); self.ratio_status.setVisible(False)
        self.table.clearContents(); self.table.setRowCount(0)
        self.progress_page.stage_label.setText("")
        self.progress_page.elapsed_label.setText("経過時間：00:00")
        self.progress_page.progress_bar.setValue(0)
        self.stack.setCurrentWidget(self.drop)

    def analysis_failed(self,msg): self.progress_page.finish(); QMessageBox.critical(self,"Analysis Error",msg); self.stack.setCurrentWidget(self.drop)
    def thread_cleanup(self):
        if self.thread:self.thread.deleteLater()
        self.thread=None; self.worker=None

    @staticmethod
    def priority_display(p): return {"LOW":"■　　","MEDIUM":"■■　","HIGH":"■■■"}.get(p,p)

    @staticmethod
    def _metric_html(label, value, unit, decimals=2):
        if isinstance(value, float):
            text=f"{value:+.{decimals}f}" if label in ("Peak","TruePeak","全体相関") else f"{value:.{decimals}f}"
        else:
            text=str(value)
        return f'<span>{label}： </span><span style="color:#ED1A3D;font-size:150%;font-weight:700">{text}</span><span> {unit}</span>'

    def show_result(self,r):
        self.current_result=r; self.save_button.setEnabled(True)
        m=int(r.duration//60); s=int(round(r.duration-m*60))
        if s==60:m+=1;s=0
        extra=f"   |   作成日時：{getattr(r, 'audio_created_at', '-')}"
        if Path(r.filename).suffix.lower()==".mp3":
            br=getattr(r,"bitrate_kbps",None)
            if br: extra += f"   |   {br} kbps"
        self.config_info.setText(f"リファレンスデータ：{getattr(r,'config_filename','-')}")
        elapsed=max(0,int(round(getattr(r,"analysis_elapsed_seconds",0.0))))
        elapsed_text=f"{elapsed//60:02d}:{elapsed%60:02d}"
        self.info.setText(f"{r.filename}   |   {m}m{s}s   |   分析時間：{elapsed_text}{extra}")
        self.metric_labels["Peak"].setText(self._metric_html("Peak",r.peak_dbfs,"dBFS",2))
        self.metric_labels["RMS"].setText(self._metric_html("RMS",r.rms_dbfs,"dBFS",2))
        self.metric_labels["TruePeak"].setText(self._metric_html("TruePeak",r.true_peak_dbtp,"dBTP",2))
        self.metric_labels["Integrated LUFS"].setText(self._metric_html("Integrated LUFS",r.integrated_lufs,"LUFS",2))
        self.metric_labels["クレストファクター"].setText(self._metric_html("クレストファクター",r.crest_factor_db,"dB",2))
        self.metric_labels["全体相関"].setText(self._metric_html("全体相関",r.stereo_correlation,"",3))
        self.table.setRowCount(len(r.bands))
        for i,b in enumerate(r.bands):
            eq=[e for e in r.eq if b.low<=e.frequency<=b.high]
            eq_text="" if not eq else f"{eq[0].filter_type} / {eq[0].frequency:.1f} Hz / {eq[0].gain_db:+.1f} dB / Q {eq[0].q:.2f}"
            corr = r.band_correlations[i] if getattr(r,"band_correlations",None) else 0.0
            target_weights=np.asarray([10.0**(float(item.target_db)/10.0) for item in r.bands],dtype=float)
            target_total=float(np.sum(target_weights))
            target_pct=(target_weights/target_total*100.0) if target_total>0 else np.zeros(len(target_weights))
            vals=[f"{int(b.low)} ~ {int(b.high)} Hz",f"{b.energy_occupancy_pct:.2f} %",f"{target_pct[i]:.2f} %",f"{corr:+.3f}",f"{b.post_energy_occupancy_pct:.2f} %",f"{b.diff_db:+.2f} dB",f"{b.sample_db:+.2f} dB",f"{b.target_db:+.2f} dB",eq_text]
            for j,v in enumerate(vals):
                it=QTableWidgetItem(v)
                it.setTextAlignment((Qt.AlignLeft if j in (0,8) else Qt.AlignRight) | Qt.AlignVCenter)
                if j in (1,2,3,5):
                    ft=it.font(); ft.setBold(True); it.setFont(ft)
                if j in (1,3):
                    it.setForeground(QColor("#FFD84D"))
                elif j==2:
                    it.setForeground(QColor("#FFFFFF"))
                if j==5:
                    it.setForeground(QColor("#FFD84D" if b.diff_db>0 else "#FF4D4D" if b.diff_db<0 else "#FFFFFF"))
                if j==6:
                    ft=it.font(); ft.setBold(True); it.setFont(ft)
                    it.setForeground(QColor("#FFD84D"))
                self.table.setItem(i,j,it)
        self.table.setColumnHidden(4,True)
        self.table.setColumnHidden(5,True)
        self.table.setColumnHidden(8,True)
        self.table.resizeColumnsToContents()
        for col in range(self.table.columnCount()): self.table.setColumnWidth(col,self.table.columnWidth(col)+18)
        self.table.resizeRowsToContents()

    def save_result(self):
        if self.current_result is None:return False
        r=self.current_result; stamp=datetime.now().strftime("%Y-%m-%d-%H-%M"); default=r.filename.rsplit(".",1)[0]+f"_{stamp}.txt"
        path,_=QFileDialog.getSaveFileName(self,"分析結果データ生成",default,"Text Files (*.txt)")
        if not path:return False
        m=int(r.duration//60); s=int(round(r.duration%60))
        elapsed=max(0,int(round(getattr(r,"analysis_elapsed_seconds",0.0))))
        elapsed_text=f"{elapsed//60:02d}:{elapsed%60:02d}"
        lines=["CLUB AUDIO ANALYZER","="*72,f"リファレンスデータ：{getattr(r,'config_filename','-')}",f"File : {r.filename}",f"Duration : {m}m{s}s",f"Analysis Time : {elapsed_text} (MM:SS)",f"Created : {getattr(r, 'audio_created_at', '-')}"]
        if Path(r.filename).suffix.lower()==".mp3":
            br=getattr(r,"bitrate_kbps",None)
            if br: lines.append(f"Bitrate : {br} kbps")
        lines += ["", "GLOBAL METRICS", "-"*72,
                  f"Peak : {r.peak_dbfs:+.2f} dBFS",
                  f"RMS : {r.rms_dbfs:+.2f} dBFS",
                  f"TruePeak : {r.true_peak_dbtp:+.2f} dBTP",
                  f"Integrated LUFS : {r.integrated_lufs:.2f} LUFS",
                  f"Crest Factor : {r.crest_factor_db:.2f} dB",
                  f"Overall Correlation : {r.stereo_correlation:+.3f}",
                  "", "BAND ANALYSIS", "-"*128, "Band | Pre % | Correlation | Post % | EQ | Diff | Sample | Target"]
        for b in r.bands:
            eq=[e for e in r.eq if b.low<=e.frequency<=b.high]; eq_text="" if not eq else f"{eq[0].filter_type}, {eq[0].frequency:.1f} Hz, {eq[0].gain_db:+.1f} dB, Q {eq[0].q:.2f}"
            idx=r.bands.index(b)
            corr=r.band_correlations[idx] if getattr(r,"band_correlations",None) else 0.0
            lines.append(f"{int(b.low)} ~ {int(b.high)} Hz | {b.energy_occupancy_pct:.2f} % | {corr:+.3f} | {b.post_energy_occupancy_pct:.2f} % | {eq_text} | {b.diff_db:+.2f} dB | {b.sample_db:+.2f} dB | {b.target_db:+.2f} dB")
        if getattr(self,"ratio_result",None) is not None:
            rr=self.ratio_result
            lines += ["", "RATIO TARGET EQ", "-"*128, f"Converged : {rr.converged}", f"Iterations : {rr.iterations}", f"Max Error : {rr.max_abs_error_pct:.3f} %", "Band | Pre % | Target % | Post % | Residual % | EQ"]
            from app.analysis.spectrum import BANDS
            for i,(lo,hi,name) in enumerate(BANDS):
                lines.append(f"{int(lo)} ~ {int(hi)} Hz | {rr.pre_pct[i]:.2f} % | {rr.target_pct[i]:.2f} % | {rr.post_pct[i]:.2f} % | {rr.residual_pct[i]:+.2f} % | {rr.eq_gains_db[i]:+.2f} dB")
        Path(path).write_text("\n".join(lines),encoding="utf-8")
        return True
