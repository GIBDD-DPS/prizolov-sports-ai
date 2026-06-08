# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.18 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Parser source adapters."""

from app.parser.sources.betensured import BetensuredParser
from app.parser.sources.forebet import ForebetParser
from app.parser.sources.predictz import PredictzParser

PARSERS = [
    ForebetParser(),
    PredictzParser(),
    BetensuredParser(),
]
