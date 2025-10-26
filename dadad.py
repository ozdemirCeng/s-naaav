import sys
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QLabel

app = QApplication(sys.argv)

# Ana pencere
window = QWidget()
window.setWindowTitle("Padding ve Spacing Örneği (PySide6)")

main_layout = QVBoxLayout(window)

# Açıklama etiketi
label = QLabel("Üstte: margins (iç boşluk), Arada: spacing (widget arası)")
main_layout.addWidget(label)

# Widget ve layout
action_widget = QWidget()
action_layout = QHBoxLayout(action_widget)

# İç kenar boşlukları (padding)
action_layout.setContentsMargins(110, 100, 20, 10)  # sol, üst, sağ, alt
# Widget'lar arası boşluk
action_layout.setSpacing(30)

# Butonlar ekle
for i in range(1, 4):
    btn = QPushButton(f"Button {i}")
    action_layout.addWidget(btn)

main_layout.addWidget(action_widget)

window.show()
sys.exit(app.exec())
