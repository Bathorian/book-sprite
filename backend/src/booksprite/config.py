from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BOOKSPRITE_", env_file=".env", extra="ignore")

    data_dir: Path = PROJECT_ROOT / "data"
    frontend_dist: Path = PROJECT_ROOT / "frontend" / "dist"
    max_upload_mb: int = 500
    max_sprite_upload_mb: int = 20

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.data_dir / 'booksprite.db'}"

    @property
    def books_dir(self) -> Path:
        return self.data_dir / "books"

    @property
    def covers_dir(self) -> Path:
        return self.data_dir / "covers"

    @property
    def sprites_dir(self) -> Path:
        return self.data_dir / "sprites"

    @property
    def tmp_dir(self) -> Path:
        return self.data_dir / "tmp"


settings = Settings()
