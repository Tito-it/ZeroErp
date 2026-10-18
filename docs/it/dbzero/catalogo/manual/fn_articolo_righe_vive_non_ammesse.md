## 📘 Documentazione Concettuale – Funzione `catalogo.fn_articolo_righe_vive_non_ammesse`

> 👀 **Vedi anche**
>
> [catalogo.fn_articolo_correggi_struttura](/dbzero/catalogo/manual/fn_articolo_correggi_struttura) — il verbo che la chiama prima e dopo la correzione
> [script.fn_check_articolo_riga](/dbzero/script/manual/fn_check_articolo_riga) — la check dei guard di riga che giudica ogni riga

### 🎯 Scopo Principale

(nasce 2026-10-18, brief-db-articoli-ammessi-per-documento A-11)

Elenca le righe **vive** di un articolo che la check dei guard di riga **non ammette**, ciascuna col
primo motivo. Una riga è viva se è attiva e il suo documento non è chiuso.

---

### Che cosa restituisce

`{documento, documento_id, riga_id, motivo}`, solo per le righe con un motivo. `documento` è il codice
di `config.tipi_entita`; `motivo` è il primo motivo di `script.fn_check_articolo_riga`, giudicato con
la natura e il tipo d'eccezione della riga.

| Dove | Riga viva |
| --- | --- |
| preventivo, ordine, bolla, offerta, contratto | attiva, e la fase dello stato non è `CHIUSO` |
| versione di listino | attiva, e la versione non è `CHIUSA` |
| promo | attiva, e il periodo non è finito alla data operativa (`documento_id` = `riga_id` = id della promo) |

Sono le sette tabelle su cui è montato `script.trgfn_righe_guard_articolo_ammesso`. Il pgTAP
`catalogo/test-articolo-correzione-righe-aperte-v1` diventa rosso se il guard viene montato su una
tabella che questa funzione non legge.

### Perché esiste una riga viva non ammessa

Il guard di riga giudica una riga quando nasce e quando cambia articolo (`UPDATE OF articolo_id`),
non dopo. Una riga viva può quindi essere non ammessa per strade che il modello prevede: una riga
riaccesa, un'OVERRIDE il cui articolo esce dalla versione operativa del listino, un'AGGIUNTA il cui
articolo poi ci entra. Per questo il verbo di correzione confronta il **prima** col **dopo**, e
rifiuta solo le righe che la correzione rende non ammesse.

SECURITY INVOKER: sotto RLS chi la chiama vede solo le sue righe. Il verbo, SECURITY DEFINER, la
chiama su tutte le aziende.

---
{% include-markdown "signature-core.md" %}
