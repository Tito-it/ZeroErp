## 📘 Documentazione Concettuale – Funzione `magazzino.trgfn_documento_interno_righe_guard_testata`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.inventari_righe](/dbzero/magazzino/tabelle/inventari_righe), [magazzino.rettifiche_righe](/dbzero/magazzino/tabelle/rettifiche_righe) — dove è montato
>
Approfondimento funzioni:
> • [magazzino.trgfn_documento_interno_guard_transizione](/dbzero/magazzino/funzioni/trgfn_documento_interno_guard_transizione) — il gemello sulla testata
>
Guide: brief `brief-db-magazzino-lotto-2-motore` (§3 D-L2-h)

---
### 🎯 Scopo Principale

(rev 2026-09-18 — Lotto 2 del magazzino)

**Le righe seguono la testata.** Una funzione per le due famiglie (`TG_ARGV`: tabella della
testata, colonna FK, colonna di stato, nome della GUC), montata `BEFORE INSERT OR UPDATE OR
DELETE` sulle righe:

| Testata in… | Le righe… |
| --- | --- |
| `DRAFT` | si scrivono |
| `CONFIRM` | le scrive **solo l'operazione** (la stessa GUC della porta `POSTED`: è lei a fissare `qta_sistema`) |
| `POSTED`, `CANCEL` | sono congelate |

Altrimenti `E_MAG_DOCUMENTO_RIGHE_CONGELATE`, con lo stato nella frase. Un `UPDATE` che sposta
una riga su un'altra testata controlla entrambe.

⭐ **Testata assente = passa.** Succede in due casi soli: la cascata di un `DELETE` della
testata (che il guard gemello ha già ammesso solo in `DRAFT`) e una testata fuori perimetro
(che sotto la row level security una riga non raggiunge comunque). Fermarsi qui bloccherebbe
la cancellazione legittima di una bozza.

Presidio: `db/pgtap/magazzino/test-documenti-interni-guard-v1.sql` (8-13).

---

### Storia

* 2026-09-18 — nasce con il Lotto 2 (`20260918-21`).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
