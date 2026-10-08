import sys
import os
import random
import string
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QComboBox, QSpinBox, QFileDialog, QMessageBox,
                             QCheckBox)
from PyQt5.QtCore import Qt

class RandomRenameApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("批量文件随机重命名")
        self.setGeometry(100, 100, 1000, 500)  # 增加窗口宽度，确保控件显示

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 标题
        title_label = QLabel("批量文件随机重命名")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        main_layout.addWidget(title_label)

        # 目录选择
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("需要修改的文件目录:"))
        self.dir_edit = QLineEdit()
        self.dir_edit.setPlaceholderText("选择文件夹")
        dir_layout.addWidget(self.dir_edit)
        browse_dir_btn = QPushButton("浏览文件夹")
        browse_dir_btn.clicked.connect(self.browse_directory)
        dir_layout.addWidget(browse_dir_btn)
        main_layout.addLayout(dir_layout)

        # 随机规则 + 按钮
        combined_layout = QHBoxLayout()
        rule_widget = QWidget()
        rule_layout = QHBoxLayout(rule_widget)
        rule_layout.setContentsMargins(0, 0, 0, 0)
        rule_layout.addWidget(QLabel("随机规则:"))
        self.rule_combo = QComboBox()
        self.rule_combo.addItems([
            "十六进制（MD5风格）",
            "随机字母(大小写随机)",
            "随机字母(大写)",
            "随机字母(小写)",
            "随机数字"
        ])
        rule_layout.addWidget(self.rule_combo)
        rule_layout.addWidget(QLabel("位数:"))
        self.length_spin = QSpinBox()
        self.length_spin.setRange(1, 64)
        self.length_spin.setValue(32)
        rule_layout.addWidget(self.length_spin)

        # ---- 扩展名下拉框（固定宽度，避免被压缩） ----
        rule_layout.addWidget(QLabel("扩展名:"))
        self.ext_combo = QComboBox()
        self.ext_combo.setFixedWidth(80)   # 固定宽度确保显示
        ext_list = ["", "JPG", "PNG", "DOC", "DOCX", "XLS", "XLSX", "TXT", "RTF", "PPT", "PPTX"]
        self.ext_combo.addItems(ext_list)
        self.ext_combo.setCurrentIndex(0)   # 空白（不改变）
        rule_layout.addWidget(self.ext_combo)

        preview_btn = QPushButton("预览")
        preview_btn.clicked.connect(self.preview_rename)
        rule_layout.addWidget(preview_btn)

        for child in rule_widget.findChildren((QComboBox, QSpinBox, QPushButton)):
            child.setFixedHeight(28)
        combined_layout.addWidget(rule_widget)
        combined_layout.addStretch()

        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        self.select_only_checkbox = QCheckBox("仅处理选中项")
        btn_layout.addWidget(self.select_only_checkbox)

        clear_btn = QPushButton("清空列表")
        clear_btn.clicked.connect(self.clear_table)
        btn_layout.addWidget(clear_btn)

        undo_btn = QPushButton("撤销重命名")
        undo_btn.clicked.connect(self.undo_rename)
        btn_layout.addWidget(undo_btn)

        rename_btn = QPushButton("批量重命名")
        rename_btn.clicked.connect(self.rename_files)
        rename_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        btn_layout.addWidget(rename_btn)

        for btn in btn_widget.findChildren(QPushButton):
            btn.setFixedHeight(28)
        combined_layout.addWidget(btn_widget)
        main_layout.addLayout(combined_layout)

        # 表格（3列，行号由垂直表头提供）
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["原文件名", "新文件名", "状态"])
        self.table.verticalHeader().setVisible(True)
        self.table.verticalHeader().setDefaultAlignment(Qt.AlignCenter)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setMinimumSectionSize(150)
        self.table.setColumnWidth(2, 100)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.table.setAcceptDrops(True)
        self.table.setDragDropMode(QTableWidget.DropOnly)
        self.table.setDropIndicatorShown(True)
        self.table.viewport().installEventFilter(self)
        self.table.setDragEnabled(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        main_layout.addWidget(self.table)

        self.file_list = []   # [原路径, 原文件名, 新文件名, 状态]
        self.history = []     # [(旧路径, 新路径)]

    # ----- 事件过滤器（拖拽）-----
    def eventFilter(self, obj, event):
        if obj is self.table.viewport():
            if event.type() == event.DragEnter:
                if event.mimeData().hasUrls():
                    event.acceptProposedAction()
                    return True
            elif event.type() == event.DragMove:
                if event.mimeData().hasUrls():
                    event.acceptProposedAction()
                    return True
            elif event.type() == event.Drop:
                if event.mimeData().hasUrls():
                    self.handle_drop_files(event.mimeData().urls())
                    event.acceptProposedAction()
                    return True
        return super().eventFilter(obj, event)

    def handle_drop_files(self, urls):
        files = [url.toLocalFile() for url in urls if url.isLocalFile()]
        for f in files:
            if os.path.isfile(f):
                self.add_single_file(f)
            elif os.path.isdir(f):
                self.add_directory(f)

    def browse_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if dir_path:
            self.dir_edit.setText(dir_path)
            self.add_directory(dir_path)

    def add_directory(self, dir_path):
        try:
            for root, _, files in os.walk(dir_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    self.add_single_file(full_path)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"读取目录失败：{str(e)}")

    def add_single_file(self, file_path):
        file_path = os.path.abspath(os.path.normpath(file_path))
        if not os.path.exists(file_path):
            return
        existing = [item[0] for item in self.file_list]
        if file_path in existing:
            return
        base_name = os.path.basename(file_path)
        self.file_list.append([file_path, base_name, "", "待处理"])
        self.update_table()

    def clear_table(self):
        self.file_list.clear()
        self.history.clear()
        self.table.setRowCount(0)

    def update_table(self):
        self.table.setRowCount(len(self.file_list))
        for row, item in enumerate(self.file_list):
            self.table.setItem(row, 0, QTableWidgetItem(item[1]))
            self.table.setItem(row, 1, QTableWidgetItem(item[2]))
            state_item = QTableWidgetItem(item[3])
            state_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, state_item)

    # ----- 生成随机文件名，支持强制扩展名 -----
    def generate_random_name(self, original_name, force_ext=None):
        name, orig_ext = os.path.splitext(original_name)
        if force_ext is None or force_ext == "":
            ext = orig_ext
        else:
            clean_ext = force_ext.lstrip('.').lower()
            ext = '.' + clean_ext
        rule = self.rule_combo.currentText()
        length = self.length_spin.value()

        if rule == "十六进制（MD5风格）":
            chars = '0123456789abcdef'
        elif rule == "随机字母(大小写随机)":
            chars = string.ascii_letters
        elif rule == "随机字母(大写)":
            chars = string.ascii_uppercase
        elif rule == "随机字母(小写)":
            chars = string.ascii_lowercase
        elif rule == "随机数字":
            chars = string.digits
        else:
            chars = string.ascii_letters

        new_name = ''.join(random.choice(chars) for _ in range(length))
        return new_name + ext

    def preview_rename(self):
        if not self.file_list:
            QMessageBox.information(self, "提示", "列表为空，请先添加文件。")
            return
        if self.select_only_checkbox.isChecked():
            selected_rows = set()
            for item in self.table.selectedItems():
                selected_rows.add(item.row())
            if not selected_rows:
                QMessageBox.information(self, "提示", "请先选中要预览的行。")
                return
            target_items = [self.file_list[row] for row in selected_rows if row < len(self.file_list)]
        else:
            target_items = self.file_list

        force_ext = self.ext_combo.currentText()
        for item in target_items:
            new_name = self.generate_random_name(item[1], force_ext)
            item[2] = new_name
            item[3] = "预览"
        self.update_table()

    def undo_rename(self):
        if not self.history:
            QMessageBox.information(self, "提示", "没有可撤销的操作。")
            return

        if self.select_only_checkbox.isChecked():
            selected_rows = set()
            for item in self.table.selectedItems():
                selected_rows.add(item.row())
            if not selected_rows:
                QMessageBox.information(self, "提示", "请先选中要撤销的行。")
                return

            to_undo = []
            for row in selected_rows:
                if row < len(self.file_list):
                    current_path = self.file_list[row][0]
                    for idx, (old, new) in enumerate(self.history):
                        if new == current_path:
                            to_undo.append((idx, old, new))
                            break
            if not to_undo:
                QMessageBox.information(self, "提示", "选中的文件没有可撤销的历史记录。")
                return

            to_undo.sort(reverse=True)
            success = 0
            for idx, old, new in to_undo:
                try:
                    os.rename(new, old)
                    for item in self.file_list:
                        if item[0] == new:
                            item[0] = old
                            item[1] = os.path.basename(old)
                            item[2] = ""
                            item[3] = "已撤销"
                            break
                    self.history.pop(idx)
                    success += 1
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"撤销 {os.path.basename(new)} 失败: {str(e)}")
            self.update_table()
            QMessageBox.information(self, "完成", f"成功撤销 {success} 个文件。")
        else:
            if not self.history:
                return
            reply = QMessageBox.question(self, "确认撤销",
                                         f"将撤销所有 {len(self.history)} 个文件的重命名，是否继续？",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return

            success = 0
            while self.history:
                old, new = self.history.pop()
                try:
                    os.rename(new, old)
                    for item in self.file_list:
                        if item[0] == new:
                            item[0] = old
                            item[1] = os.path.basename(old)
                            item[2] = ""
                            item[3] = "已撤销"
                            break
                    success += 1
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"撤销 {os.path.basename(new)} 失败: {str(e)}")
            self.update_table()
            QMessageBox.information(self, "完成", f"成功撤销 {success} 个文件。")

    def rename_files(self):
        if not self.file_list:
            QMessageBox.information(self, "提示", "列表为空，请先添加文件。")
            return

        if self.select_only_checkbox.isChecked():
            selected_rows = set()
            for item in self.table.selectedItems():
                selected_rows.add(item.row())
            if not selected_rows:
                QMessageBox.information(self, "提示", "请先选中要重命名的行。")
                return
            target_items = [self.file_list[row] for row in selected_rows if row < len(self.file_list)]
        else:
            target_items = self.file_list

        force_ext = self.ext_combo.currentText()
        for item in target_items:
            if not item[2]:
                new_name = self.generate_random_name(item[1], force_ext)
                item[2] = new_name
                item[3] = "待重命名"
            else:
                item[3] = "待重命名"
        self.update_table()

        reply = QMessageBox.question(self, "确认重命名",
                                     f"即将重命名 {len(target_items)} 个文件，是否继续？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        success_count = 0
        for item in target_items:
            old_path = item[0]
            dir_path = os.path.dirname(old_path)
            new_path = os.path.join(dir_path, item[2])
            if os.path.exists(new_path):
                base, ext = os.path.splitext(item[2])
                counter = 1
                while True:
                    test_path = os.path.join(dir_path, f"{base}_{counter}{ext}")
                    if not os.path.exists(test_path):
                        new_path = test_path
                        item[2] = os.path.basename(new_path)
                        break
                    counter += 1
            try:
                os.rename(old_path, new_path)
                self.history.append((old_path, new_path))
                item[0] = new_path
                item[1] = os.path.basename(new_path)
                item[3] = "成功"
                success_count += 1
            except Exception as e:
                item[3] = f"失败: {str(e)}"
        self.update_table()
        QMessageBox.information(self, "完成", f"重命名完成，成功 {success_count} 个，失败 {len(target_items) - success_count} 个。")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RandomRenameApp()
    window.show()
    sys.exit(app.exec_())
