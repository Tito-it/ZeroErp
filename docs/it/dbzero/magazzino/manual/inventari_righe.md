## 📘 Documentazione Concettuale – Tabella `magazzino.inventari_righe`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.inventari](/dbzero/magazzino/tabelle/inventari) — la testata
> • [magazzino.lotti](/dbzero/magazzino/tabelle/lotti), [magazzino.assets](/dbzero/magazzino/tabelle/assets)
>
Guide: brief `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.7)

---
### 🎯 Scopo Principale

(rev 2026-09-15 — Lotto 1 del magazzino)

**Le righe di [magazzino.inventari](/dbzero/magazzino/tabelle/inventari)**: per ogni
articolo (ed eventualmente lotto, pezzo serializzato, ubicazione) quanto è stato contato
(`qta_contata`, mai negativa) e quanto il sistema si aspettava (`qta_sistema`). Una riga da
sola non ha contesto — data, magazzino e stato stanno nella testata.

Ogni riga è la **sorgente** del movimento di allineamento che il conteggio produce
(`INVENTARIO_RIGA`).

### Lotto e seriale sono chiavi

`lotto_id` ([magazzino.lotti](/dbzero/magazzino/tabelle/lotti)) e `asset_id`
([magazzino.assets](/dbzero/magazzino/tabelle/assets)) hanno preso il posto dei due testi
liberi `lotto` e `seriale`: senza, l'operazione non avrebbe niente da passare alla primitiva
del registro. Se l'articolo li pretende (`requires_lotto`, `requires_serial`) è
l'operazione a rifiutare una riga senza; «il lotto è di questo articolo» lo controlla lei,
non un CHECK.

Con un pezzo serializzato il conteggio è `0` o `1`: c'è o non c'è.

### Chi può vedere e scrivere

Le righe seguono la testata: `rls_inventari_righe_ef_whitelist` risale all'inventario, e
da lì al magazzino e al suo emittente. Meccanismo comune: [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

### Dal 18-09 (Lotto 2)

* `costo_unitario` (nullable, ≥ 0): la **valorizzazione iniziale** che chi conta può conoscere —
  il primo carico in assoluto non ha un costo, e senza questa colonna entrerebbe senza valore;
  la primitiva lo usa come primo termine di `COALESCE(costo della riga, media corrente)` su
  un'entrata. Vuoto non è un errore: la media si diluisce, e la spia
  [dbops.vw_magazzino_movimenti_senza_costo](/dbzero/dbops/views/vw_magazzino_movimenti_senza_costo) lo mostra.
* `qta_sistema` lo scrive il **posting dal piano**, prima di postare: è la fotografia contro cui
  il conteggio è stato posto, e resta.
* **Una posizione si conta una volta sola** per inventario (`uq_mag_inventari_righe_posizione`,
  `NULLS NOT DISTINCT` su articolo, ubicazione, lotto, seriale): due righe sulla stessa posizione
  avrebbero postato due delta contro lo stesso sistema.
* Le righe si scrivono con la testata in `DRAFT`; in `CONFIRM` scrive solo il posting.

---

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
