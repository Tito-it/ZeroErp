# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: LA PROVENIENZA DEL PREZZO CHE VIAGGIA COL PREZZO, dalla riga del
#        documento alla riga di commessa (brief-db-provenienza-prezzo-segue-il-
#        prezzo §8.7, K-1 e K-4). Una forma sola per i due capi del push:
#          * i lister (`vendite.fn_list_*_da_pushare`), che restituiscono le
#            dieci colonne in coda a ogni riga;
#          * i componenti di un kit, la cui provenienza il loader legge con lo
#            stesso BB del DB (`vendite.fn_provenienza_prezzo_esplosa`), senza
#            ricopiarne la regola.
#        La riga di commessa la riceve campo per campo (`CommessaAttivitaInput`).
#
# ⭐ I NOMI. I campi sono quelli della riga di commessa
#    (`COLONNE_PROVENIENZA_PREZZO`); nel lister e nel BB del DB il contratto
#    del prezzo esce come `prezzo_contratto_id`, perche' in alcuni lister
#    `contratto_id` e' gia' il documento. La traduzione sta in un punto solo,
#    `COLONNA_DEL_LISTER`.
# ⛔ IL PUSH NON DEDUCE PIU' LA PROVENIENZA. Fino al 2026-11-14 la ricostruiva
#    chiedendo al resolver da dove VERREBBE oggi il prezzo
#    (`_resolve_pricing_audit`): una provenienza che poteva non essere quella
#    del prezzo che si stava copiando. Ora la dice chi ha scritto il prezzo.
# ------------------------------------------------------------
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, fields
from decimal import Decimal
from typing import Any


# Scopo: la provenienza del prezzo di una riga, con i nomi della riga di
#        commessa. Vuota (tutto None) = nessuna provenienza: la riga senza
#        prezzo, o il consumo, il cui prezzo lo dara' il listino piu' tardi
#        (R-5).
@dataclass(frozen=True)
class ProvenienzaPrezzo:
    prezzo_base_snapshot: Decimal | None = None
    origine_prezzo: str | None = None
    tipo_variazione_applicata: str | None = None
    valore_variazione_applicata: Decimal | None = None
    promo_id: int | None = None
    contratto_id: int | None = None
    categoria_cliente_id_snapshot: int | None = None
    classe_utenza_id_snapshot: int | None = None
    listino_riga_id: int | None = None
    listino_versione_id: int | None = None

    # Scopo: i campi come argomenti con nome di `CommessaAttivitaInput`.
    def come_campi(self) -> dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(self)}


PROVENIENZA_VUOTA = ProvenienzaPrezzo()

# Le colonne di provenienza di una riga di commessa, con i nomi della riga.
# ⭐ Sede unica: `commesse_repository` (che le scrive, `update_attivita_prezzo`)
#    e il BB `prezzo_riga_commessa` le leggono da qui.
COLONNE_PROVENIENZA_PREZZO: tuple[str, ...] = tuple(f.name for f in fields(ProvenienzaPrezzo))

# Campo della riga di commessa -> colonna del lister e del BB del DB.
COLONNA_DEL_LISTER: dict[str, str] = {
    campo: ("prezzo_contratto_id" if campo == "contratto_id" else campo)
    for campo in COLONNE_PROVENIENZA_PREZZO
}


# Scopo: la provenienza da una riga letta, chiedendo ogni colonna col suo nome
#        nel lister (`leggi(nome)`), eventualmente con un prefisso.
def provenienza_da_colonne(leggi: Callable[[str], Any], *, prefisso: str = "") -> ProvenienzaPrezzo:
    return ProvenienzaPrezzo(**{
        campo: leggi(prefisso + colonna) for campo, colonna in COLONNA_DEL_LISTER.items()
    })


# Il prefisso delle colonne di provenienza nella proiezione di un componente:
# la proiezione ha gia' un `origine_prezzo`, e i nomi non devono scontrarsi.
PREFISSO_COMPONENTE = "prov_"


# Scopo: il frammento SQL che legge la provenienza di una riga (alias `alias`,
#        con le colonne `origine_prezzo`, `listino_versione_id`,
#        `listino_riga_id`, `prezzo_resolver_context`) dal BB del DB:
#        (colonne da proiettare, LATERAL da mettere nel FROM).
def sql_provenienza_esplosa(alias: str, *, prefisso: str = PREFISSO_COMPONENTE) -> tuple[str, str]:
    colonne = ",\n".join(
        f"pp.{colonna} AS {prefisso}{colonna}" for colonna in COLONNA_DEL_LISTER.values()
    )
    lateral = (
        "CROSS JOIN LATERAL vendite.fn_provenienza_prezzo_esplosa("
        f"{alias}.origine_prezzo, {alias}.listino_versione_id, "
        f"{alias}.listino_riga_id, {alias}.prezzo_resolver_context) pp"
    )
    return colonne, lateral
