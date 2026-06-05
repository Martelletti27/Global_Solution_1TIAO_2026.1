"""Configuracao compartilhada do pytest."""

import sys
from pathlib import Path

# Permite importar src/ a partir da raiz do projeto
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
