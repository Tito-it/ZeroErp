## 📘 Documentazione Concettuale – Vista `vendite.vw_preventivi_righe_dettaglio`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe)
> [vendite.preventivi_riepiloghi_iva](/dbzero/vendite/tabelle/preventivi_riepiloghi_iva)
> [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)
> [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura)
> [config.iva](/dbzero/config/tabelle/iva)
>
Approfondimento funzioni:
> [vendite.fn_ricalcola_riepilogo_iva_preventivo](/dbzero/vendite/funzioni/fn_ricalcola_riepilogo_iva_preventivo)
> [vendite.fn_ricalcola_totali_preventivo](/dbzero/vendite/funzioni/fn_ricalcola_totali_preventivo)

---
### 🎯 Scopo Principale
(latest review 02-05-2026)

`vendite.vw_preventivi_righe_dettaglio` arricchisce le righe preventivo con i
dati denormalizzati di articolo, unita' di misura operativa e aliquota IVA.
Include **importi calcolati** per evitare duplicazione della logica di display
nel backend/frontend.

> **Nota:** la vista NON e' la fonte autoritativa per i totali del preventivo.
> Per imponibile/IVA aggregati per aliquota usare la tabella
> [`vendite.preventivi_riepiloghi_iva`](/dbzero/vendite/tabelle/preventivi_riepiloghi_iva)
> (single source of truth, mantenuta da trigger AFTER su `preventivi_righe`).

---

### JOIN principali

| Tabella | Dati esposti |
|---------|-------------|
| `catalogo.articoli` | codice, descrizione articolo |
| `catalogo.unita_misura` | codice UoM operativa |
| `config.iva` | codice IVA, descrizione IVA, aliquota_iva |

---

### 📑 Campi calcolati

| Campo | Formula | Uso previsto |
|-------|---------|--------------|
| `importo_riga` | `ROUND(quantita * prezzo_unitario * (1 - sconto/100), 2)` | **Display** della singola riga (UI tabella, stampe). Mai per somme aggregate. |
| `imponibile_riga_full` | `quantita * prezzo_unitario * (1 - sconto/100)` (no ROUND) | **Aggregazioni applicative** (vedi nota sotto). |

> **`importo_iva_riga` e' stato rimosso il 02-05-2026**: l'IVA per riga e'
> concettualmente errata. Il calcolo IVA va sempre fatto sull'aggregato per
> aliquota (regola fiscale: DPR 633/72 art. 21 + DM 24/12/93). Per consultare
> l'IVA del documento usare `vendite.preventivi_riepiloghi_iva`.

---

### ⚠️ Nota per somme aggregate (BE/FE)

Chi vuole sommare le righe lato applicativo (Python service o frontend)
**DEVE** usare `imponibile_riga_full` e applicare `ROUND(SUM, 2)` sull'aggregato:

```sql
-- ✅ CORRETTO: arrotonda la somma full-precision
SELECT ROUND(SUM(imponibile_riga_full), 2) AS imponibile_totale
  FROM vendite.vw_preventivi_righe_dettaglio
 WHERE preventivo_id = 42 AND attivo IS TRUE;

-- ❌ ERRATO: somma valori gia' arrotondati per riga (riproduce il bug
--           fiscale originale, scarti di centesimi su molte righe)
SELECT SUM(importo_riga) AS imponibile_totale
  FROM vendite.vw_preventivi_righe_dettaglio
 WHERE preventivo_id = 42 AND attivo IS TRUE;
```

Per i totali del documento (imponibile/IVA per aliquota) la via canonica e'
**sempre** leggere `vendite.preventivi_riepiloghi_iva` (mantenuta dal DB,
calcolo gia' fiscalmente corretto), evitando ogni aggregazione applicativa.

`importo_riga` resta utile solo per **mostrare** la riga in UI/stampa (il
suo ROUND riflette quello che l'utente vedra' nella stampa cartacea della
singola riga); non e' mai un input di aggregazione.

---

### Note operative

* Include sia righe **attive** che **inattive** (campo `attivo`): le inattive
  servono per consultare lo storico revisioni.
* Ordinamento: `preventivo_id, ordine, id`.

---

### Esempio d'uso

```sql
-- Righe attive di un preventivo (display per riga)
SELECT articolo_codice, descrizione, quantita, prezzo_unitario,
       sconto_percentuale, importo_riga, iva_codice, iva_descrizione,
       iva_aliquota
  FROM vendite.vw_preventivi_righe_dettaglio
 WHERE preventivo_id = 42
   AND attivo IS TRUE
 ORDER BY ordine;

-- Imponibile totale calcolato lato applicativo (full precision + ROUND)
SELECT ROUND(SUM(imponibile_riga_full), 2) AS imponibile_totale
  FROM vendite.vw_preventivi_righe_dettaglio
 WHERE preventivo_id = 42 AND attivo IS TRUE;

-- Riepilogo IVA per aliquota (preferito: gia' calcolato in DB)
SELECT iva_codice, iva_aliquota, imponibile, imposta
  FROM vendite.vw_preventivi_riepilogo_iva_dettaglio
 WHERE preventivo_id = 42
 ORDER BY iva_aliquota;
```

---

{% include-markdown "signature-core.md" %}
