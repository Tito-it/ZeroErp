## 📘 Documentazione Concettuale – Tabella `vendite.preventivi_riepiloghi_iva`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [vendite.preventivi](/dbzero/vendite/tabelle/preventivi)
> [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe)
> [vendite.fatture_riepiloghi_iva](/dbzero/vendite/tabelle/fatture_riepiloghi_iva)
>
Approfondimento funzioni:
> [vendite.fn_ricalcola_riepilogo_iva_preventivo](/dbzero/vendite/funzioni/fn_ricalcola_riepilogo_iva_preventivo)
> [vendite.fn_ricalcola_totali_preventivo](/dbzero/vendite/funzioni/fn_ricalcola_totali_preventivo)
> [config.fn_get_aliquota_iva](/dbzero/config/funzioni/fn_get_aliquota_iva)

### 🎯 Scopo Principale

(latest review 02-05-2026)

La tabella **`vendite.preventivi_riepiloghi_iva`** memorizza il riepilogo IVA
aggregato per preventivo, una riga per ogni combinazione `(iva_id, natura_id,
esigibilita, split_payment)`. Pattern speculare a
`vendite.fatture_riepiloghi_iva`: garantisce calcolo IVA fiscalmente corretto
(ROUND a 2 decimali sull'aggregato per aliquota, non per riga) coerente con il
dettato di **DPR 633/72 art.21** e **DM 24/12/93**.

### Perche' una tabella, non solo una query inline

Il calcolo IVA del preventivo era prima solo nella vista
`vw_preventivi_righe_dettaglio` e nella fn `fn_ricalcola_totali_preventivo`,
**con arrotondamento per riga** (errato fiscalmente). Conseguenza concreta:
una fattura emessa dallo stesso preventivo poteva avere `totale_iva` diverso
di centesimi rispetto a `preventivi.totale_iva`, anche con identico imponibile.

Soluzione: stesso pattern delle fatture, riepilogo persistito su tabella
dedicata. Vantaggi:

* **Single source of truth** per i totali IVA del preventivo
* **Builder "fattura da preventivo"** copia direttamente le righe del riepilogo
* **UI riepilogo IVA** del preventivo via `vw_preventivi_riepilogo_iva_dettaglio`
* **Diagnostica** quadratura via `arrotondamento` (full-precision vs ROUND)
* **Coerenza centesimi** preventivo <-> fattura emessa

### Campi chiave e semantica

* **`id`** *(bigserial)* – PK tecnica.
* **`preventivo_id`** *(bigint)* – FK a `vendite.preventivi(id)`, **ON DELETE CASCADE**: la cancellazione del preventivo elimina i riepiloghi.
* **`iva_id`** *(integer, NULL)* – FK a `config.iva(id)`. NULL ammesso per righe esenti senza `iva_id` valorizzato.
* **`natura_id`** *(integer, NULL)* – FK a `config.iva_natura(id)`. **Sempre NULL nei preventivi attuali**: `preventivi_righe` non espone natura. Colonna presente per coerenza con `fatture_riepiloghi_iva` e per future estensioni.
* **`esigibilita`** *(char(1), NULL)* – `I` immediata, `D` differita, `S` split. Stesso commento di `natura_id`: NULL nei preventivi.
* **`split_payment`** *(boolean, NULL)* – stesso commento: NULL nei preventivi.
* **`imponibile`** *(numeric, NOT NULL DEFAULT 0)* – `ROUND(SUM(qta*prezzo*(1-sconto/100)), 2)` per ogni gruppo IVA.
* **`imposta`** *(numeric, NOT NULL DEFAULT 0)* – `ROUND(imponibile * aliquota_iva/100, 2)`. Aliquota override-able da stato emittente via `config.fn_get_aliquota_iva`.
* **`arrotondamento`** *(numeric, NOT NULL DEFAULT 0)* – `SUM(imponibile_riga full-precision) - SUM(imponibile_riga full-precision rounded)`. Diagnostica per quadratura.
* **Audit** – `data_insert`, `user_insert`, `data_update`, `user_update`.

### Vincoli

| Tipo | Nome | Colonne |
|---|---|---|
| PRIMARY KEY | `pk_preventivi_r_iva` | `id` |
| FOREIGN KEY | `fk_preventivi_r_iva_preventivo` | `preventivo_id` -> `vendite.preventivi(id)` ON DELETE CASCADE |
| FOREIGN KEY | `fk_preventivi_r_iva_iva` | `iva_id` -> `config.iva(id)` |
| FOREIGN KEY | `fk_preventivi_r_iva_natura` | `natura_id` -> `config.iva_natura(id)` |
| UNIQUE | `uq_preventivi_r_iva_key` | `(preventivo_id, COALESCE(natura_id, 0), COALESCE(esigibilita, 'I'), COALESCE(split_payment, false), COALESCE(iva_id, 0))` |

### Popolamento

La tabella e' **solo riempita da `vendite.fn_ricalcola_riepilogo_iva_preventivo`**.
Mai INSERT manuale o via API — la fn fa DELETE+INSERT atomico per
preventivo. La fn e' invocata da:

1. `vendite.fn_ricalcola_totali_preventivo` (wrapper) — chiamata diretta o via trigger
2. Trigger AFTER su `preventivi_righe` (`trg_preventivi_righe_z90_ricalcola_totali_*`) — ogni INSERT/UPDATE/DELETE riga ricalcola

### Esempi

**Lettura riepilogo per preventivo:**

```sql
SELECT iva_id, imponibile, imposta, arrotondamento
  FROM vendite.preventivi_riepiloghi_iva
 WHERE preventivo_id = 42
 ORDER BY iva_id;
```

**Quadratura totali da riepilogo:**

```sql
SELECT preventivo_id,
       SUM(imponibile) AS totale_imponibile,
       SUM(imposta)    AS totale_iva,
       SUM(imponibile) + SUM(imposta) AS totale_documento
  FROM vendite.preventivi_riepiloghi_iva
 WHERE preventivo_id = 42
 GROUP BY preventivo_id;
```

**Diagnostica arrotondamento (ricerca anomalie):**

```sql
SELECT preventivo_id, iva_id, ROUND(arrotondamento, 6) AS arr
  FROM vendite.preventivi_riepiloghi_iva
 WHERE ABS(arrotondamento) > 0.005
 ORDER BY ABS(arrotondamento) DESC;
```

### Note operative

* **NO storicizzazione**: la tabella non ha trigger di storico; il contenuto e'
  ricostruibile in qualsiasi momento da `preventivi_righe`. Mantenere lo storico
  porterebbe over-engineering senza beneficio concreto.
* **CASCADE FK preventivi**: la cancellazione di un preventivo (rara, oggi solo
  via cleanup) elimina automaticamente i riepiloghi. La fn `fn_ricalcola_*`
  gestisce correttamente il caso "0 righe attive" lasciando la tabella vuota
  per quel `preventivo_id`.
* **natura/esigibilita/split sempre NULL oggi**: la struttura e' allineata a
  `fatture_riepiloghi_iva` per simmetria. Se in futuro `preventivi_righe` esponesse
  questi campi, la fn aggiornata li raccoglierebbe automaticamente nel group by.
* **arrotondamento residuo**: non e' un bug, e' la differenza naturale tra somma
  full-precision e somma a 2 decimali. Valori tipici < 0.01. Per uso fiscale ha
  rilevanza informativa.

---

{% include-markdown "signature-core.md" %}

---
