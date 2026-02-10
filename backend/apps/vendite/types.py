from typing import Any, TypeAlias, TypedDict

# Tipi condivisi pipeline vendite per ridurre chiavi "magiche" e firma duplicate.

LottoPipelineMeta: TypeAlias = dict[str, Any]


class PipelineStepLogMeta(TypedDict):
    ordine: int | None
    dry_run: bool


class GroupAttivitaKey(TypedDict):
    articolo_id: int
    dest_billing_account_id: int
    uom_id: int | None
    prezzo_unitario: float | None
    iva_id: int | None
    competenza_dal: str | None
    competenza_al: str | None
    visibilita_componenti: str
    calcolo_qta_padre: str
    arrotondamento_importi_dec: int
    arrotondamento_quantita_dec: int
    metodo_arrotondamento_importi: str
    metodo_arrotondamento_quantita: str


class ResetLottoDraftResult(TypedDict):
    updated_lotti: int
    updated_attivita: int
    deleted_fatture: int
    deleted_righe: int


class ResetLottoFatturaDraftResult(TypedDict):
    updated_attivita: int
    deleted_fatture: int
    deleted_righe: int
