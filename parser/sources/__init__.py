# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.14 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Parser source adapters."""

from sources.betensured import BetensuredParser
from sources.forebet import ForebetParser
from sources.predictz import PredictzParser

PARSERS = [
    ForebetParser(),
    PredictzParser(),
    BetensuredParser(),
]
