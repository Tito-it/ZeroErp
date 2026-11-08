## 📘 Documentazione Concettuale – Vista `vendite.vw_fattura_righe_lista`

> **Ultimo aggiornamento**: 3 novembre 2026

> 👀 **Vedi anche**
>
> • [vendite.vw_fattura_righe_esposte](/dbzero/vendite/views/vw_fattura_righe_esposte) — la rappresentazione del documento, che questa vista legge e non ricalcola
> • [vendite.fn_numero_documento_fattura](/dbzero/vendite/funzioni/fn_numero_documento_fattura) — il numero parlante della fattura rettificata
>
> **Verifica:** `db/pgtap/vendite/test-vw-fattura-righe-lista-v1.sql`

---

### 🎯 Scopo Principale

(vista nata il 2026-09-28, `20260928-28`)

**Le righe di una fattura come lista**: la sorgente della lista configurabile
`vendite.fattura_righe` e dell'endpoint delle righe della fattura.

---

### ⭐ Perché non basta la vista madre

`vw_fattura_righe_esposte` è la rappresentazione del documento per ogni uscita
(PDF, SDI, portale), e ha due caratteristiche che una lista non regge:

- il **padre di un kit è sintetico**: non ha una riga propria, quindi non ha
  una chiave. Senza chiave non si pagina, non si espande, non si esporta;
- è **gerarchica**: i componenti esposti stanno sotto il padre grazie
  all'ordinamento. Una lista che ordina per un'altra colonna li staccherebbe, e
  una pagina potrebbe tagliare un kit a metà.

---

### La forma (decisione di Tid del 2026-09-28, D-8.3)

| Colonna | Cosa |
| --- | --- |
| righe | **solo il primo livello**: righe normali, parti di una riga spezzata dal plafond, padri dei kit |
| `riga_key` | `R:<id>` per le righe vere; `K:<fattura>:<md5>` per il padre di un kit, costruita sulla stessa tupla con cui la vista madre lo compone (fattura, kit, IVA, cliente di destinazione, articolo e descrizione del padre e, dal 2026-10-02, il periodo: lo stesso kit su due periodi sono due padri) |
| `componenti`, `componenti_numero` | i componenti **esposti** del kit (DESCRITTIVO e VALORIZZATO; i NASCOSTO no), dentro la riga padre, per la riga di espansione. Dal 2026-10-01 ogni componente porta anche `esposizione`, `prezzo_unitario`, `sconto_percentuale` e `importo_riga`, valorizzati solo sul VALORIZZATO |
| `importo_riga` | l'imponibile come lo espone la fattura: sul padre, la somma dei componenti **non** valorizzati; NULL se il kit è tutto valorizzato (kit senza resto). ⚠️ Dal 2026-10-01 la somma della colonna **non** dà il totale del documento: l'importo dei valorizzati sta dentro `componenti`. Il totale si legge dalla testata |
| `riga_rettificata_*` | il legame riga-riga della nota di credito; `riga_rettificata_documento` è il numero **parlante** della fattura rettificata, non il contatore |

⇒ Ordinamento e paginazione lavorano sulle righe del documento: **un kit si
muove intero**. L'ordine del documento è `ordinamento, riga_nr, riga_key`.

⚠️ **Limite ereditato, dichiarato**: due padri con lo stesso kit, IVA e
destinatario ma articolo o descrizione diversi riceverebbero gli stessi
componenti — come nella vista madre, che li lega sulle stesse quattro colonne.
⚠️ Le due parti di una riga spezzata dal plafond sono righe vere: ordinando per
importo possono separarsi (per numero di riga restano vicine).

---

### Regole

- **Nessun calcolo rifatto**: la regola del kit resta nella vista madre.
- Il filtro per fattura scende fino alle righe (dal 2026-09-28 il CTE `kit`
  della vista madre non è più materializzato, `20260928-43`).
- **Nessun `ORDER BY`**; `security_invoker`: `fatture_righe` è in RLS.
- **Il periodo** (dal 2026-10-02, `20261002-65`): `competenza_dal`, `competenza_al`
  e `ha_periodo` in coda, dalla vista madre. Si stampa il periodo quando
  `ha_periodo` è vero. Il periodo entra anche nella partizione dei componenti, così
  ogni padre porta solo i componenti del suo periodo.
- **Il periodo da mostrare** (dal 2026-10-03, `20261003-06`): `periodo_dal` e
  `periodo_al` in coda. Sono `competenza_dal` e `competenza_al` quando
  `ha_periodo` è vero, e restano vuoti sulle righe puntuali. Alimentano le
  colonne di lista «Periodo dal» e «Periodo al», a video e nell'export. Con
  `competenza_dal` come sorgente l'export avrebbe mostrato una data anche dove il
  documento non stampa nessun periodo. La regola su quando c'è un periodo non si
  ricopia: la vista legge `ha_periodo`.

---

{% include-markdown "signature-core.md" %}

### Oneri e sezione del documento (rev 2026-11-03)

Dal `20261103-50`, in coda:

| Colonna | Che cosa |
| --- | --- |
| `tipo_movimento` | quello delle attività fatturabili della riga (`NORMALE`, `RETTIFICA`, `ONERE`); NULL sul padre di un kit |
| `e_onere`, `causale_onere_id` | l'articolo della riga è un articolo-onere (trasporto, urgenza…), arrivato da un documento o dalla porta oneri; vale anche per la rettifica di un onere |
| `sezione_documento` | 1 articoli, 2 oneri |

L'**ordine del documento** è `sezione_documento, ordinamento, riga_nr, riga_key`: gli oneri in fondo,
a video e in stampa, con la stessa regola di ordine e bolla (`vw_ordini_righe_dettaglio`,
`vw_ddt_righe_dettaglio`).
