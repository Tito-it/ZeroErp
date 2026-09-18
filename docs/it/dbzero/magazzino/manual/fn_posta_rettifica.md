## 📘 Documentazione Concettuale – Funzione `magazzino.fn_posta_rettifica`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.rettifiche](/dbzero/magazzino/tabelle/rettifiche), [magazzino.rettifiche_righe](/dbzero/magazzino/tabelle/rettifiche_righe)
>
Approfondimento funzioni:
> • [magazzino.fn_posta_inventario](/dbzero/magazzino/funzioni/fn_posta_inventario) — la gemella, con un passo in più (il piano)
> • [magazzino.fn_scrivi_movimento](/dbzero/magazzino/funzioni/fn_scrivi_movimento) — la primitiva che chiama per riga
>
Guide: brief `brief-db-magazzino-lotto-2-motore` (§4.5, D-L2-g)

---
### 🎯 Scopo Principale

(rev 2026-09-18 — Lotto 2 del magazzino)

**Registra una rettifica confermata**: la *correzione a mano* che il modello promette («la
correzione a mano È una rettifica»). Per ogni riga posta con la primitiva il delta **dato**
(`qta_delta`, firmato) con `RETT_POS` o `RETT_NEG` dal segno, sorgente `RETTIFICA_RIGA`, il
costo della riga solo su un'entrata; poi porta la testata a `POSTED`. Una transazione sola;
ritorna i movimenti scritti.

Ha la stessa forma dell'inventario con un passo in meno: il delta non si calcola, è scritto
sulla riga. Anche la porta (`zeroerp.magazzino_posting_rettifica`), i rifiuti sulla testata
(non trovata, non `CONFIRM`, senza righe) e l'all-or-nothing sono gli stessi.

⭐ Una rettifica negativa **ignora i blocchi** (una promessa) ma **non il fisico**: registra
un fatto sulla merce, e un magazzino che non può registrare ciò che vede mente. Se dopo la
rettifica una promessa non è più mantenibile, lo dice
[vw_disponibilita](/dbzero/magazzino/views/vw_disponibilita) (disponibile negativo), non un
rifiuto del conteggio.

Presidio: `db/pgtap/magazzino/test-fn-posta-rettifica-v1.sql`.

---

### Storia

* 2026-09-18 — nasce con il Lotto 2 (`20260918-23`).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
