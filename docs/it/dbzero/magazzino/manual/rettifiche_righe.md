## 📘 Documentazione Concettuale – Tabella `magazzino.rettifiche_righe`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.rettifiche](/dbzero/magazzino/tabelle/rettifiche) — la testata
> • [magazzino.lotti](/dbzero/magazzino/tabelle/lotti), [magazzino.assets](/dbzero/magazzino/tabelle/assets)
>
Guide: brief `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.7)

---
### 🎯 Scopo Principale

(rev 2026-09-15 — Lotto 1 del magazzino)

**Le righe di [magazzino.rettifiche](/dbzero/magazzino/tabelle/rettifiche)**: per ogni
articolo (ed eventualmente lotto, pezzo serializzato, ubicazione) di quanto la giacenza va
corretta (`qta_delta`, mai zero, firmata) e perché (`motivo`). Ogni riga è la **sorgente** del
movimento di rettifica (`RETTIFICA_RIGA`, causale `RETT_POS` o `RETT_NEG` secondo il verso).

### Lotto e seriale sono chiavi

`lotto_id` ([magazzino.lotti](/dbzero/magazzino/tabelle/lotti)) e `asset_id`
([magazzino.assets](/dbzero/magazzino/tabelle/assets)) hanno preso il posto dei due testi
liberi `lotto` e `seriale`: senza, l'operazione non avrebbe niente da passare alla primitiva
del registro. Se l'articolo li pretende (`requires_lotto`, `requires_serial`) è
l'operazione a rifiutare una riga senza; «il lotto è di questo articolo» lo controlla lei,
non un CHECK.

Con un pezzo serializzato la correzione è di **un** pezzo (`|qta_delta| = 1`).

### Chi può vedere e scrivere

Le righe seguono la testata: `rls_rettifiche_righe_ef_whitelist` risale alla rettifica, e
da lì al magazzino e al suo emittente. Meccanismo comune: [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

### Dal 18-09 (Lotto 2)

`costo_unitario` (nullable, ≥ 0): il costo che chi compila una rettifica **positiva** (merce
ritrovata) può conoscere; senza, si valorizza alla media corrente. Su una negativa non conta:
l'uscita va alla media. Le righe si scrivono con la testata in `DRAFT`; da `CONFIRM` in poi sono
dell'operazione o congelate.

---

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
