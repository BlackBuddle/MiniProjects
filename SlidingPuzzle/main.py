import sys
import random
import os
from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QPixmap, QIcon, QPainter, QColor, QPen

# ── UI / 이미지 파일 경로 ──────────────────────────────────────
UI_FILE = "main_gui.ui"
PUZZLE_IMAGE = "puzzle_image.jpg"   # 퍼즐에 사용할 이미지 (정사각형 권장)

# ── 난이도 설정 ───────────────────────────────────────────────
DIFFICULTY = {
    0: 3,   # Easy  : 3×3  (숫자 1~8  + 빈칸)
    1: 4,   # Medium: 4×4  (숫자 1~15 + 빈칸)
    2: 5,   # Hard  : 5×5  (숫자 1~24 + 빈칸)
}

EMPTY = 0   # 빈 칸을 나타내는 값


class SlidingPuzzle(QMainWindow):
    def __init__(self):
        super().__init__()

        # ── UI 로드 ─────────────────────────────────────────
        uic.loadUi(UI_FILE, self)

        # ── 상태 변수 ───────────────────────────────────────
        self.size = 3
        self.board = []
        self.move_count = 0

        # ── 원본 이미지 로드 ────────────────────────────────
        self.source_pixmap = QPixmap(PUZZLE_IMAGE)
        if self.source_pixmap.isNull():
            # 이미지가 없으면 그라데이션 기본 이미지 생성
            self.source_pixmap = self._make_default_pixmap(600)

        # ── 버튼 참조 캐시 ─────────────────────────────────
        self.buttons = {}
        for r in range(6):
            for c in range(6):
                btn = getattr(self, f"btn_{r}_{c}")
                self.buttons[(r, c)] = btn
                btn.clicked.connect(
                    lambda _, row=r, col=c: self.on_tile_clicked(row, col)
                )

        # ── 시그널 연결 ─────────────────────────────────────
        self.shuffleButton.clicked.connect(self.shuffle)
        self.difficultyCombo.currentIndexChanged.connect(self.on_difficulty_changed)

        # ── 초기 보드 구성 ──────────────────────────────────
        self.init_board()

    # ─────────────────────────────────────────────────────────
    # 이미지 → 격자로 분할하여 QIcon 리스트 반환
    # ─────────────────────────────────────────────────────────
    def _slice_image(self, size: int) -> dict:
        """
        원본 이미지를 size×size 격자로 자릅니다.
        반환: { tile_number(1-base) : QPixmap }
              tile_number = row * size + col + 1
        """
        # 버튼 크기 계산 (gridLayoutWidget 600px - 간격)
        spacing = 6
        tile_px = (600 - spacing * (size - 1)) // size

        # 원본 이미지를 정사각형으로 맞춤
        sq = min(self.source_pixmap.width(), self.source_pixmap.height())
        src = self.source_pixmap.copy(0, 0, sq, sq).scaled(
            tile_px * size, tile_px * size,
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

        slices = {}
        for r in range(size):
            for c in range(size):
                tile_num = r * size + c + 1   # 1-based
                crop = src.copy(c * tile_px, r * tile_px, tile_px, tile_px)
                slices[tile_num] = crop

        return slices, tile_px

    # ─────────────────────────────────────────────────────────
    # 보드 초기화
    # ─────────────────────────────────────────────────────────
    def init_board(self):
        """현재 난이도에 맞는 정렬된 보드를 생성하고 이미지를 조각냅니다."""
        self.size = DIFFICULTY[self.difficultyCombo.currentIndex()]
        self.move_count = 0

        total = self.size * self.size
        nums = list(range(1, total)) + [EMPTY]
        self.board = [nums[r * self.size:(r + 1) * self.size]
                      for r in range(self.size)]

        # 이미지 조각 생성
        self.tile_pixmaps, self.tile_px = self._slice_image(self.size)

        self._refresh_ui()

    # ─────────────────────────────────────────────────────────
    # UI 갱신
    # ─────────────────────────────────────────────────────────
    def _refresh_ui(self):
        """board 배열을 읽어 각 버튼에 이미지 조각을 설정합니다."""
        self.moveLabel.setText(f"이동 횟수: {self.move_count}")

        icon_size = QSize(self.tile_px, self.tile_px)

        for r in range(6):
            for c in range(6):
                btn = self.buttons[(r, c)]
                visible = (r < self.size and c < self.size)
                btn.setVisible(visible)

                if not visible:
                    continue

                val = self.board[r][c]
                btn.setIconSize(icon_size)
                btn.setText("")           # 텍스트 제거

                if val == EMPTY:
                    # ── 빈 칸: 아이콘 없음 + 어두운 스타일 ──
                    btn.setIcon(QIcon())
                    btn.setEnabled(False)
                    btn.setStyleSheet(
                        "QPushButton {"
                        "  background-color: #0d0221;"
                        "  border: 2px dashed #3c096c;"
                        "  border-radius: 8px;"
                        "}"
                    )
                else:
                    # ── 타일: 해당 이미지 조각 표시 ──────────
                    pixmap = self.tile_pixmaps[val]
                    btn.setIcon(QIcon(pixmap))
                    btn.setEnabled(True)
                    btn.setStyleSheet(
                        "QPushButton {"
                        "  background-color: transparent;"
                        "  border: 2px solid #7b2fbe;"
                        "  border-radius: 8px;"
                        "  padding: 0px;"
                        "}"
                        "QPushButton:hover {"
                        "  border: 2px solid #c77dff;"
                        "}"
                        "QPushButton:pressed {"
                        "  border: 3px solid #e0aaff;"
                        "}"
                    )

    # ─────────────────────────────────────────────────────────
    # 타일 클릭 처리
    # ─────────────────────────────────────────────────────────
    def on_tile_clicked(self, row: int, col: int):
        """클릭한 타일이 빈 칸과 인접하면 이동합니다."""
        if row >= self.size or col >= self.size:
            return

        empty_r, empty_c = self._find_empty()

        dr = abs(row - empty_r)
        dc = abs(col - empty_c)
        if (dr == 1 and dc == 0) or (dr == 0 and dc == 1):
            self.board[empty_r][empty_c] = self.board[row][col]
            self.board[row][col] = EMPTY
            self.move_count += 1
            self._refresh_ui()

            if self._is_solved():
                self._show_clear_message()

    # ─────────────────────────────────────────────────────────
    # 셔플
    # ─────────────────────────────────────────────────────────
    def shuffle(self):
        """보드를 초기화하고 랜덤으로 충분히 섞습니다."""
        self.init_board()

        shuffle_count = self.size * self.size * 80
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        prev = None   # 직전 이동의 역방향 (되돌리기 방지)

        for _ in range(shuffle_count):
            er, ec = self._find_empty()
            random.shuffle(directions)
            for dr, dc in directions:
                # 직전 이동의 역방향은 건너뜀
                if prev and (dr, dc) == prev:
                    continue
                nr, nc = er + dr, ec + dc
                if 0 <= nr < self.size and 0 <= nc < self.size:
                    self.board[er][ec] = self.board[nr][nc]
                    self.board[nr][nc] = EMPTY
                    prev = (-dr, -dc)
                    break

        self.move_count = 0
        self._refresh_ui()

    # ─────────────────────────────────────────────────────────
    # 난이도 변경
    # ─────────────────────────────────────────────────────────
    def on_difficulty_changed(self):
        self.init_board()

    # ─────────────────────────────────────────────────────────
    # 유틸리티
    # ─────────────────────────────────────────────────────────
    def _find_empty(self) -> tuple:
        for r in range(self.size):
            for c in range(self.size):
                if self.board[r][c] == EMPTY:
                    return r, c
        raise RuntimeError("빈 칸을 찾을 수 없습니다.")

    def _is_solved(self) -> bool:
        flat = [self.board[r][c]
                for r in range(self.size)
                for c in range(self.size)]
        goal = list(range(1, self.size * self.size)) + [EMPTY]
        return flat == goal

    @staticmethod
    def _make_default_pixmap(size: int) -> QPixmap:
        """puzzle_image.jpg 가 없을 때 사용할 기본 그라데이션 이미지를 생성합니다."""
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        painter = QPainter(pm)
        from PyQt5.QtGui import QLinearGradient
        grad = QLinearGradient(0, 0, size, size)
        grad.setColorAt(0.0, QColor("#7b2fbe"))
        grad.setColorAt(0.5, QColor("#3c096c"))
        grad.setColorAt(1.0, QColor("#240046"))
        painter.fillRect(0, 0, size, size, grad)
        painter.end()
        return pm

    # ─────────────────────────────────────────────────────────
    # 클리어 메시지
    # ─────────────────────────────────────────────────────────
    def _show_clear_message(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("🎉 클리어!")
        msg.setText(
            f"<b style='font-size:18px; color:#e0aaff;'>퍼즐 완성!</b><br><br>"
            f"이동 횟수: <b>{self.move_count}</b>번"
        )
        msg.setStyleSheet(
            "QMessageBox { background-color: #1a1a2e; color: #e0aaff; }"
            "QLabel { color: #e0aaff; font-size: 14px; }"
            "QPushButton { background-color: #7b2fbe; color: white;"
            "  border-radius: 8px; padding: 6px 20px; font-size: 13px; }"
            "QPushButton:hover { background-color: #9d4edd; }"
        )
        again_btn = msg.addButton("다시 셔플", QMessageBox.AcceptRole)
        msg.addButton("닫기", QMessageBox.RejectRole)
        msg.exec_()

        if msg.clickedButton() == again_btn:
            self.shuffle()


# ─────────────────────────────────────────────────────────────
# 진입점
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))

    window = SlidingPuzzle()
    window.show()
    sys.exit(app.exec_())
