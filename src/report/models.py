"""
PDFレポート データモデル定義
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class PDFReport:
    """
    生成されたPDFレポートの情報を格納するデータクラス。
    """
    session_id: str
    file_path: Path
    user_name: str
    generated_at: datetime = field(default_factory=datetime.now)
    file_size_bytes: int = 0
    user_line_id: str = ""

    def __post_init__(self):
        self.file_path = Path(self.file_path)
        if self.file_path.exists():
            self.file_size_bytes = self.file_path.stat().st_size

    @property
    def file_name(self) -> str:
        return self.file_path.name

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "file_name": self.file_name,
            "user_name": self.user_name,
            "generated_at": self.generated_at.isoformat(),
            "file_size_bytes": self.file_size_bytes,
        }
