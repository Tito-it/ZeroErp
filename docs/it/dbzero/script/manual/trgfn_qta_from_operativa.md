## 📘 Documentazione Concettuale – Trigger function `script.trgfn_qta_from_operativa`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli_uom_operativa](/dbzero/catalogo/tabelle/articoli_uom_operativa) — le unità operative dell'articolo, col fattore e le regole della quantità
> * [catalogo.unita_misura_conversioni](/dbzero/catalogo/tabelle/unita_misura_conversioni) — le conversioni generali, il ripiego
> * [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe) — una delle sei tabelle su cui è montata
>
> Approfondimento funzioni:
>
> * [catalogo.fn_get_uom_factor](/dbzero/catalogo/funzioni/fn_get_uom_factor) — il fattore alla data del documento
> * [catalogo.fn_uom_operativa_alla_data](/dbzero/catalogo/funzioni/fn_uom_operativa_alla_data) — le regole della quantità alla data del documento
> * [catalogo.fn_get_uom_base](/dbzero/catalogo/funzioni/fn_get_uom_base) — l'unità base, quando la riga non dice l'unità
> * [script.fn_fonte_porta_quantita](/dbzero/script/funzioni/fn_fonte_porta_quantita) — quali fonti della quantità la portano sulla riga
> * [script.trgfn_righe_guard_quantita_per_fonte](/dbzero/script/funzioni/trgfn_righe_guard_quantita_per_fonte) — rifiuta la quantità operativa con una fonte a valle

---

### 🎯 Scopo Principale

Calcola la quantità base di una riga di documento di vendita: la quantità operativa, scritta
nell'unità che l'operatore ha scelto, per il fattore verso l'unità base dell'articolo.
`quantita` è una colonna calcolata: la scrive solo questo trigger.

---

### Il fattore

* **Il fattore scritto sulla riga** (`factor_to_base`) è la fotografia e si rispetta: anche
  quello copiato da un documento sorgente (l'ordine dal preventivo, la bolla dall'ordine, il
  reso dalla bolla).
* **Altrimenti** si legge con `catalogo.fn_get_uom_factor` alla **data del documento**: 1 per
  l'unità base, poi la mappatura dell'articolo in vigore quel giorno, poi la conversione
  generale fra le due unità. Il fattore usato si fotografa sulla riga, e da lì in poi resta:
  cambiare la mappatura non tocca le righe già scritte.
* **Senza fattore la riga è rifiutata** (`E_UOM_MISSING`): una quantità base inventata è
  peggio di nessuna. La frase dice l'unità, l'unità base, l'articolo e la data.
* **Se un aggiornamento cambia l'unità e non il fattore**, il fattore di prima era dell'altra
  unità: si rilegge per quella nuova.
* **Senza unità operativa** vale l'unità base dell'articolo.

Su ordini, bolle e resi `factor_to_base` è obbligatorio ma non ha un valore predefinito: una
riga che arriva senza fattore lo riceve da questo trigger, non da un «1» scritto prima.

---

### La data del documento

La data viene dalla testata: il montaggio dice la tabella della testata, la colonna della riga
che la punta e la colonna della data. Le date della testata sono obbligatorie.

| Tabella delle righe | Testata | Data |
| --- | --- | --- |
| `vendite.preventivi_righe` | `preventivi` | `data` |
| `vendite.ordini_righe` | `ordini` | `data` |
| `vendite.ddt_righe` | `ddt` | `data` |
| `vendite.resi_righe` | `resi` | `data` |
| `vendite.contratti_righe` | `contratti` | `data` |
| `vendite.offerte_commerciali_eccezioni` | `offerte_commerciali` | `validita_dal` |

Su contratto e offerta il montaggio salta le righe di esclusione, che non hanno quantità, unità
né fattore.

---

### Le regole della quantità

Sono quelle della mappatura dell'unità alla data del documento
(`catalogo.fn_uom_operativa_alla_data`):

* con `forbid_fraction` la quantità operativa dev'essere intera
  (`E_QTA_OPERATIVA_NON_INTERA`);
* non può avere più decimali di `max_decimals` (`E_QTA_OPERATIVA_DECIMALI`); gli zeri in coda
  non contano;
* dev'essere un multiplo di `qty_step` (`E_QTA_OPER_STEP_INVALIDO`).

Un'unità convertita dalle conversioni generali non ha regole. La quantità base si arrotonda a
6 decimali.

---

### La fonte della quantità

Su contratto e offerta la quantità può arrivare a valle (letture, timesheet, inserimento
manuale a ogni periodo: `script.fn_fonte_porta_quantita` falso). Con quelle fonti il trigger
porta `quantita` a NULL a ogni scrittura e si ferma lì; una quantità operativa scritta la
rifiuta prima il guard della quantità per fonte. Con la fonte fissa, e sulle tabelle senza
fonte, la quantità operativa è obbligatoria (`E_QTA_MISSING`).

---

### Il montaggio

Argomenti del trigger:

1. scrivi il fattore usato, se la riga non l'ha (vero su tutti e sei i montaggi);
2. la colonna della fonte della quantità, vuota sulle tabelle che non ce l'hanno;
3. la tabella della testata;
4. la colonna della riga che la punta;
5. la colonna data della testata.

Senza gli ultimi tre il trigger rifiuta con `E_SCRIPT_CHIAMATA_NON_VALIDA`: un montaggio senza
la data del documento è un errore di chi monta.

Su un aggiornamento che non cambia quantità operativa, unità né fattore il trigger non fa
niente.

---

### Codici errore

* `E_UOM_MISSING` — nessun fattore alla data del documento: né mappatura dell'articolo, né
  conversione generale. Campo `uom_operativa_id`.
* `E_QTA_MISSING` — quantità operativa mancante con la fonte fissa o senza fonte.
* `E_QTA_OPERATIVA_NON_INTERA`, `E_QTA_OPERATIVA_DECIMALI`, `E_QTA_OPER_STEP_INVALIDO` — le
  regole della quantità. Campo `qta_operativa`.
* `E_SCRIPT_CHIAMATA_NON_VALIDA` — montaggio senza testata e data.

---

### Test

* `db/pgtap/catalogo/test-uom-fattore-e-regole-v1.sql` — il fattore dalla conversione generale,
  la riga senza conversione rifiutata, il fattore della mappatura alla data di due preventivi,
  il cambio d'unità che rilegge il fattore, `max_decimals`.
* `db/pgtap/vendite/test-refactor-qta-operativa-preventivi-v1.sql` — sui preventivi la quantità
  base è la quantità operativa per il fattore della mappatura, e il fattore si fotografa.
* `db/pgtap/vendite/offerte_commerciali/test_offerte_eccezioni_qta_from_operativa.sql` — lo
  stesso calcolo sulle eccezioni di offerta.

---

### Note di migrazione

* 2026-05-27 — su un aggiornamento che non tocca gli input operativi il trigger non fa niente.
* 2026-08-04 — tolti due argomenti morti: oggi il primo è lo snapshot del fattore, il secondo la
  fonte.
* 2026-10-08 — una fonte a valle porta la quantità a NULL.
* 2026-10-21 — ritirata la fonte derivata dai componenti, che era l'eccezione all'obbligo della
  quantità operativa.
* 2026-11-09 — il fattore alla data del documento da `catalogo.fn_get_uom_factor`, la riga
  senza fattore rifiutata invece del fattore 1, `max_decimals` applicato, il cambio d'unità che
  rilegge il fattore; tre argomenti nuovi del montaggio (brief-db-revisione-catalogo, giro 2).

---

{% include-markdown "signature-core.md" %}
