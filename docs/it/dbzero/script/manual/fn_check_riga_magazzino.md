## 📘 Documentazione Concettuale – Funzione `script.fn_check_riga_magazzino`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — `gestito_a_magazzino`, `requires_lotto`, `requires_serial`
> • [magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini) — `usa_ubicazioni`
> • [magazzino.lotti](/dbzero/magazzino/tabelle/lotti), [magazzino.assets](/dbzero/magazzino/tabelle/assets), [magazzino.ubicazioni](/dbzero/magazzino/tabelle/ubicazioni)
>
Approfondimento funzioni:
> • [magazzino.fn_scrivi_movimento](/dbzero/magazzino/funzioni/fn_scrivi_movimento) — la solleva (passi 5-8)
> • [magazzino.fn_inventario_piano](/dbzero/magazzino/funzioni/fn_inventario_piano) — la mostra (esito `NON_POSTABILE`)
>
Guide: [Linee guida SQL — 12.5.2 la madre chiama la check](/linee-guida-sql) · brief `brief-db-magazzino-lotto-2-motore` (§6-ter C8)

---
### 🎯 Scopo Principale

(rev 2026-09-18 — Lotto 2 del magazzino)

**La riga si può scrivere a registro?** Dati magazzino, articolo e — se ci sono — lotto,
seriale e ubicazione, risponde l'elenco ordinato dei motivi per cui **no**: vuoto se sì.
Pura, non scrive, non solleva.

Sono i passi 5-8 della primitiva, in una sede sola, e il motivo per cui esistono qui e non
dentro la primitiva è preciso: sono errori che **una persona corregge sulla riga** (marcare
l'articolo, indicare il lotto, scegliere l'ubicazione). Se li facesse solo la primitiva, il
piano dell'inventario mostrerebbe come «da postare» righe che il posting rifiuterà, e
l'operatore lo scoprirebbe sbagliando. Così invece il piano legge la stessa funzione e le
segna `NON_POSTABILE` con il motivo, e il posting rifiuta con la stessa frase.

---

### I motivi, nell'ordine dei passi

| Passo | Regola | Codice · `campo` |
| --- | --- | --- |
| 5 | l'articolo è attivo e **gestito a magazzino** (e qui ci si ferma: senza articolo il resto non ha senso) | `E_MAG_ARTICOLO_NON_GESTITO` · `articolo_id` |
| 6 | **decide l'articolo**: se `requires_lotto` il lotto è obbligatorio, altrimenti è vietato; se c'è, è dell'articolo e attivo | `E_MAG_LOTTO_OBBLIGATORIO` · `E_MAG_LOTTO_NON_AMMESSO` · `E_MAG_LOTTO_DI_ALTRO_ARTICOLO` · `lotto_id` |
| 7 | **decide l'articolo**: idem per il seriale; e il pezzo è dell'**emittente del magazzino** | `E_MAG_SERIALE_OBBLIGATORIO` · `E_MAG_SERIALE_NON_AMMESSO` · `E_MAG_ASSET_DI_ALTRO_ARTICOLO` · `E_MAG_ASSET_DI_ALTRO_EMITTENTE` · `asset_id` |
| 8 | **decide il magazzino**: se `usa_ubicazioni` l'ubicazione è obbligatoria, altrimenti è vietata; se c'è, è del magazzino e attiva | `E_MAG_UBICAZIONE_OBBLIGATORIA` · `E_MAG_UBICAZIONE_NON_AMMESSA` · `E_MAG_UBICAZIONE_DI_ALTRO_MAGAZZINO` · `ubicazione_id` |

Ogni motivo porta `campo` nel dettaglio: il frontend accende il campo giusto. Le chiavi i18n
sono `magazzino.riga.blocco.*` (undici).

Che cosa **non** guarda: il magazzino in sé (esiste, attivo: passo 4 della primitiva) e la
disponibilità ([fn_check_disponibilita_uscita](/dbzero/script/funzioni/fn_check_disponibilita_uscita)).

Presidio: `db/pgtap/magazzino/test-fn-scrivi-movimento-controlli-v1.sql` (5-15) e
`test-fn-posta-inventario-v1.sql` (6, 12, 13).

---

### Storia

* 2026-09-18 — nasce con il Lotto 2 (`20260918-16`), decisione C8.

---

{% include-markdown "signature-core.md" %}
