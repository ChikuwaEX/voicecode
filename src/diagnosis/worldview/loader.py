"""
世界観 YAMLローダー

疎結合設計の中核:
    - YAMLファイルを差し替えるだけで世界観を全変更可能
    - コード（diagnosis_engine.py）は一切変更不要
    - テーマの動的切り替えに対応
"""

from pathlib import Path
from typing import Optional
import yaml


class WorldviewLoader:
    """
    世界観YAMLファイルを読み込み、アーキタイプ情報を提供するクラス。

    使用例:
        loader = WorldviewLoader(theme_name="elements_v1")
        archetype = loader.get_archetype("SOLAR_HERALD")
    """

    def __init__(self, theme_name: str = "elements_v1", themes_dir: Optional[Path] = None):
        """
        Args:
            theme_name: 使用するYAMLテーマ名（拡張子なし）
            themes_dir: YAMLファイルが格納されたディレクトリ（省略時は自動検出）
        """
        if themes_dir is None:
            themes_dir = Path(__file__).parent / "themes"

        self._themes_dir = themes_dir
        self._theme_name = theme_name
        self._data: dict = {}
        self._load_theme(theme_name)

    def _load_theme(self, theme_name: str) -> None:
        """指定されたテーマのYAMLファイルを読み込む"""
        theme_path = self._themes_dir / f"{theme_name}.yaml"

        if not theme_path.exists():
            raise FileNotFoundError(
                f"世界観テーマファイルが見つかりません: {theme_path}\n"
                f"利用可能なテーマ: {self.list_available_themes()}"
            )

        with open(theme_path, "r", encoding="utf-8") as f:
            self._data = yaml.safe_load(f)

        if not self._data:
            raise ValueError(f"世界観テーマファイルが空です: {theme_path}")

    def switch_theme(self, theme_name: str) -> None:
        """テーマを動的に切り替える（コードを変更せずに世界観を変更）"""
        self._load_theme(theme_name)
        self._theme_name = theme_name

    def list_available_themes(self) -> list[str]:
        """利用可能なテーマ一覧を返す"""
        return [
            p.stem for p in self._themes_dir.glob("*.yaml")
        ]

    def get_archetype(self, archetype_code: str) -> dict:
        """
        アーキタイプコードから完全なアーキタイプ情報を返す。

        Args:
            archetype_code: アーキタイプコード（例: "SOLAR_HERALD"）

        Returns:
            dict: アーキタイプの全情報（YAML内容そのまま）

        Raises:
            KeyError: 存在しないアーキタイプコードの場合
        """
        archetypes = self._data.get("archetypes", {})
        if archetype_code not in archetypes:
            available = list(archetypes.keys())
            raise KeyError(
                f"アーキタイプコード '{archetype_code}' が見つかりません。\n"
                f"利用可能なコード: {available}"
            )
        return archetypes[archetype_code]

    def get_all_archetypes(self) -> dict:
        """すべてのアーキタイプ情報を返す"""
        return self._data.get("archetypes", {})

    def get_element(self, element_code: str) -> dict:
        """
        元素コードから元素情報を返す。

        Args:
            element_code: 元素コード（例: "FIRE"）

        Returns:
            dict: 元素の情報（色・チャクラ・クリスタル等）
        """
        elements = self._data.get("elements", {})
        return elements.get(element_code, {})

    def get_element_color(self, element_code: str, polarity: str) -> dict:
        """
        元素コード＋陰陽から対応する色情報を返す。

        Args:
            element_code: 元素コード（例: "FIRE"）
            polarity: "陽" or "陰"

        Returns:
            dict: {"name": "紅蓮", "reading": "ぐれん", "hex": "#C0392B"}
        """
        element = self.get_element(element_code)
        if not element:
            return {"name": "", "reading": "", "hex": "#FFFFFF"}

        color_key = "yang_color" if polarity == "陽" else "yin_color"
        color_data = element.get(color_key)

        # 新形式（yang_color/yin_color）が存在しない場合は旧形式フォールバック
        if not color_data:
            return {
                "name": element.get("name", ""),
                "reading": "",
                "hex": element.get("color", "#FFFFFF"),
            }

        return color_data

    def get_meta(self) -> dict:
        """テーマのメタ情報を返す"""
        return self._data.get("meta", {})

    @property
    def theme_name(self) -> str:
        return self._theme_name

    @property
    def tagline(self) -> str:
        """世界観のキャッチコピーを返す"""
        return self.get_meta().get("tagline", "")
