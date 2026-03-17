from enum import Enum


class DocType(str, Enum):
    CCCD = "CCCD"
    BANG_DAI_HOC = "Bang_dai_hoc"
    GIAY_KHAM_SUC_KHOE = "Giay_kham_suc_khoe"
    ANH_THE = "Anh_the"
    LY_LICH = "Ly_lich"
    KHAC = "Khac"


SUPPORTED_MIME_TYPES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}

UNKNOWN_FOLDER = "_unknown"
TMP_CCCD_DIR = "_tmp_cccd"
