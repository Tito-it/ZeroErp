# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service diagnostico pricing v5. Esegue i 4 check sui 3 stadi del
#        resolver per spiegare perche' il pricing non risolve e quali asset
#        configurare. Read-only, nessun side-effect, nessuna chiamata al
#        resolver vero (la diagnosi non risolve, ispeziona la configurazione).
# ------------------------------------------------------------

from datetime import date
from typing import Any
from uuid import UUID

from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import PayloadValidator
from apps.vendite.db.pricing_diagnose_repository import (
    PricingDiagnoseRepository,
)


_E_VALIDATION = "E_VENDITE_VALIDATION"
_E_NOT_FOUND = "E_VENDITE_NOT_FOUND"


class PricingDiagnoseService:
    """Diagnostica configurazione pricing per (articolo, uom, BA, utility,
    emittente, data, classe_utenza opzionale). Ritorna un report a stadi
    che il FE rende come checklist con icone ✓/✗ per ogni passo.
    """

    def __init__(self, repo: PricingDiagnoseRepository | None = None) -> None:
        self._repo = repo or PricingDiagnoseRepository()
        self._v = PayloadValidator(
            validation_code=_E_VALIDATION,
            log_to_db=True,
            function_name="pricing_diagnose_service",
        )

    # Scopo: orchestratore dei 4 check. Valida input, poi esegue i passi
    #        in sequenza. Il calcolo del campo `esito_atteso` traccia quale
    #        sarebbe il primo fallimento del resolver vero, cosi' il FE
    #        puo' allineare il messaggio errore al check fallito.
    def diagnose(
        self,
        *,
        articolo_id: UUID | str,
        uom_id: int,
        data_riferimento: date,
        ba_id: int,
        utility_id: int,
        emittente_soggetto_ruolo_id: int,
        classe_utenza_id: int | None = None,
    ) -> dict[str, Any]:
        # Validazione input identica al resolver vero (il diagnose deve poter
        # essere chiamato con gli stessi parametri).
        articolo_str = self._v.require_uuid({"articolo_id": articolo_id}, "articolo_id")
        self._v.guard_positive_int(uom_id, field="uom_id")
        self._v.guard_positive_int(ba_id, field="ba_id")
        self._v.guard_positive_int(utility_id, field="utility_id")
        self._v.guard_positive_int(
            emittente_soggetto_ruolo_id, field="emittente_soggetto_ruolo_id",
        )
        ErrorManager.require(
            isinstance(data_riferimento, date),
            code=_E_VALIDATION,
            message="data_riferimento deve essere una data.",
        )
        if classe_utenza_id is not None:
            self._v.guard_positive_int(classe_utenza_id, field="classe_utenza_id")

        # Step radice: BA + categoria. Se BA non trovato il diagnose ferma
        # con codice 404 (l'admin deve creare prima il BA).
        ba_row = self._repo.get_ba_categoria(int(ba_id))
        ErrorManager.require(
            ba_row is not None,
            code=_E_NOT_FOUND,
            message="Billing account non trovato.",
            detail=f"ba_id={ba_id}",
        )
        assert ba_row is not None

        ba_block = {
            "trovato": True,
            "categoria_id": ba_row["categoria_cliente_id"],
            "categoria_codice": ba_row.get("categoria_codice"),
            "categoria_descrizione": ba_row.get("categoria_descrizione"),
            "categoria_partecipa_promo": bool(ba_row["categoria_partecipa_promo"]),
        }

        # ========== STADIO 0 — PROMO ==========
        promo_row = self._repo.find_promo_attiva(
            articolo_id=articolo_str,
            uom_id=int(uom_id),
            data_riferimento=data_riferimento,
        )
        promo_attiva = promo_row is not None
        # La promo si applica SOLO se la categoria del BA partecipa_promo.
        promo_applicabile = promo_attiva and ba_block["categoria_partecipa_promo"]
        stadio_0 = {
            "applicabile": promo_applicabile,
            "promo_attiva_articolo": promo_attiva,
            "promo_codice": promo_row["codice"] if promo_row else None,
            "promo_descrizione": promo_row["descrizione"] if promo_row else None,
            "motivo": (
                None if promo_applicabile
                else (
                    "Promo attiva ma la categoria cliente non partecipa alle promo."
                    if promo_attiva and not ba_block["categoria_partecipa_promo"]
                    else f"Nessuna promo attiva su (articolo, uom={uom_id}) "
                         f"in data {data_riferimento.isoformat()}."
                )
            ),
        }

        # ========== STADIO 1 — CONTRATTO ==========
        contratto_row = self._repo.find_contratto_attivo(
            ba_id=int(ba_id),
            utility_id=int(utility_id),
            data_riferimento=data_riferimento,
        )
        contratto_attivo = contratto_row is not None
        articolo_negoziato_in_c: bool | None = None
        contratto_applicabile = False
        contratto_motivo: str | None
        if not contratto_attivo:
            contratto_motivo = (
                f"Nessun contratto ATTIVO per (BA={ba_id}, utility={utility_id}) "
                f"in data {data_riferimento.isoformat()}."
            )
        else:
            assert contratto_row is not None
            modalita = contratto_row["modalita_pricing"]  # 'C' o 'A_O_B'
            if modalita == "C":
                articolo_negoziato_in_c = self._repo.contratto_riga_articolo_negoziato(
                    contratto_id=int(contratto_row["contratto_id"]),
                    articolo_id=articolo_str,
                )
                if articolo_negoziato_in_c:
                    contratto_applicabile = True
                    contratto_motivo = None
                else:
                    contratto_motivo = (
                        "Contratto modalita C trovato ma l'articolo non "
                        "ha riga negoziata: il resolver solleverebbe "
                        "E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C."
                    )
            else:  # A_O_B → ha listino, sempre applicabile
                contratto_applicabile = True
                contratto_motivo = None

        stadio_1 = {
            "applicabile": contratto_applicabile,
            "contratto_attivo": contratto_attivo,
            "contratto_numero": (
                contratto_row["contratto_numero"] if contratto_row else None
            ),
            "modalita_pricing": (
                contratto_row["modalita_pricing"] if contratto_row else None
            ),
            "articolo_negoziato_in_C": articolo_negoziato_in_c,
            "motivo": contratto_motivo,
        }

        # ========== STADIO 2 — CATEGORIA → MATRICE LISTINO ==========
        # Si valuta sempre (anche se contratto applicabile) perche' la matrice
        # e' il fallback di default e l'admin vuole sapere se e' configurata
        # comunque (es. preparare il futuro post-contratto).
        if ba_block["categoria_id"] is None:
            stadio_2 = {
                "applicabile": False,
                "matrice_riga_presente": False,
                "matrice_listino_id": None,
                "matrice_listino_codice": None,
                "matrice_listino_descrizione": None,
                "classe_match": None,
                "motivo": "Il BA non ha categoria_cliente assegnata.",
            }
        else:
            matrice_row = self._repo.find_matrice_riga(
                categoria_cliente_id=int(ba_block["categoria_id"]),
                utility_id=int(utility_id),
                emittente_soggetto_ruolo_id=int(emittente_soggetto_ruolo_id),
                classe_utenza_id=classe_utenza_id,
                data_riferimento=data_riferimento,
            )
            if matrice_row is None:
                classe_str = (
                    f"classe={classe_utenza_id}" if classe_utenza_id is not None
                    else "classe=NULL"
                )
                stadio_2 = {
                    "applicabile": False,
                    "matrice_riga_presente": False,
                    "matrice_listino_id": None,
                    "matrice_listino_codice": None,
                    "matrice_listino_descrizione": None,
                    "classe_match": None,
                    "motivo": (
                        f"Nessuna riga matrice per (categoria="
                        f"{ba_block['categoria_codice'] or ba_block['categoria_id']}, "
                        f"utility={utility_id}, "
                        f"emittente_sr={emittente_soggetto_ruolo_id}, "
                        f"{classe_str}) in data {data_riferimento.isoformat()}."
                    ),
                }
            else:
                stadio_2 = {
                    "applicabile": True,
                    "matrice_riga_presente": True,
                    "matrice_listino_id": matrice_row["listino_id"],
                    "matrice_listino_codice": matrice_row.get("listino_codice"),
                    "matrice_listino_descrizione": matrice_row.get(
                        "listino_descrizione",
                    ),
                    "classe_match": matrice_row.get("classe_match"),
                    "motivo": None,
                }

        # ========== Esito atteso del resolver ==========
        # Calcoliamo quale sarebbe il primo stadio applicabile, cosi' il FE
        # puo' evidenziare il "vincitore" anche quando la diagnosi e' chiamata
        # in successo (mostrare il path applicato) o spiegare il fallimento
        # quando nessuno stadio matcha.
        if stadio_0["applicabile"]:
            esito = {"origine": "PROMO", "errore_atteso": None}
        elif stadio_1["applicabile"]:
            origine = (
                "CONTRATTO"
                if stadio_1["modalita_pricing"] == "C"
                else "CONTRATTO_LISTINO"
            )
            esito = {"origine": origine, "errore_atteso": None}
        elif stadio_2["applicabile"]:
            esito = {"origine": "CATEGORIA", "errore_atteso": None}
        else:
            # Nessuno stadio applicabile: il resolver vero fallirebbe. Il
            # codice errore atteso dipende dal motivo prevalente.
            if stadio_1["contratto_attivo"] and stadio_1["modalita_pricing"] == "C":
                errore = "E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C"
            else:
                errore = "E_CATEGORIA_LISTINO_NON_MAPPATA"
            esito = {"origine": None, "errore_atteso": errore}

        # ========== Suggerimenti operativi ==========
        # Lista ordinata di azioni concrete che l'admin puo' fare per
        # sbloccare il pricing. Vuota se il resolver e' applicabile.
        azioni: list[str] = []
        if esito["errore_atteso"] is not None:
            if not stadio_2["matrice_riga_presente"] and ba_block["categoria_id"]:
                azioni.append(
                    f"Aggiungi mappa (categoria "
                    f"{ba_block['categoria_codice'] or ba_block['categoria_id']}, "
                    f"utility {utility_id}, emittente_sr "
                    f"{emittente_soggetto_ruolo_id}) in "
                    "/amm-software/matrice-categorie-listini/.",
                )
            if not stadio_1["contratto_attivo"]:
                azioni.append(
                    f"Crea un contratto ATTIVO sul BA per utility {utility_id} "
                    "(modalita A/B con listino, oppure C con riga negoziata).",
                )
            elif (
                stadio_1["modalita_pricing"] == "C"
                and stadio_1["articolo_negoziato_in_C"] is False
            ):
                azioni.append(
                    f"Aggiungi una riga al contratto "
                    f"{stadio_1['contratto_numero']} per l'articolo richiesto "
                    "(prezzo_unitario obbligatorio, modalita C).",
                )
            if not stadio_0["promo_attiva_articolo"]:
                azioni.append(
                    "Oppure crea una promo articolo per la coppia (articolo, uom) "
                    "valida alla data del documento.",
                )
            if ba_block["categoria_id"] is None:
                azioni.append(
                    "Assegna una categoria_cliente al billing account "
                    "(default STANDARD).",
                )

        return {
            "ba": ba_block,
            "stadio_0_promo": stadio_0,
            "stadio_1_contratto": stadio_1,
            "stadio_2_categoria": stadio_2,
            "esito_atteso": esito,
            "azioni_suggerite": azioni,
        }
