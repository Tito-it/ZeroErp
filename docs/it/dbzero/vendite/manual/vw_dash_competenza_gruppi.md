## 🔍 Documentazione Concettuale – Vista `vendite.vw_dash_competenza_gruppi`

> **Versione**: 2026-07-27 (brief-db-emissione-fattura-per-documento-sorgente
> PARTE A step A8, requisito A3, decisione D-4 · migration `20260727-18`)

> **Vedi anche**
>
[vendite.vw_dash_competenza_attivita](/dbzero/vendite/views/vw_dash_competenza_attivita) — la base da cui deriva
> [vendite.fn_build_gruppo_fatturabile_key](/dbzero/vendite/funzioni/fn_build_gruppo_fatturabile_key)
> [vendite.vw_dash_fatturazione_documenti](/dbzero/vendite/views/vw_dash_fatturazione_documenti) — riferimento leggibile
> [config.sorgenti](/dbzero/config/tabelle/sorgenti) — colonna `area`

---

### 🎯 Scopo Principale

L'**elenco dei gruppi fatturabili** che alimenta la card «Da emettere» della
Lente Competenza. Prima di agire, l'operatore deve vedere cosa può fatturare,
raggruppato nelle unità su cui può decidere, con **quante righe** e **quanto
valore** ciascuna pesa.

```text
Card «Da emettere» (29 attività)
 ├─ PRV-0012              Rossi    5 righe   1.000 €   [Fattura]
 ├─ CTR-0007              Rossi    3 righe     500 €   [Fattura]
 ├─ ORD-0033              Bianchi  8 righe   2.300 €   [Fattura]
 └─ Oneri · commessa #42  Rossi    1 riga      500 €   [Fattura]
```

Prima del 2026-07-27 questo elenco **non esisteva in nessuna forma**: la
discovery lavorava a livello di terna del lotto, non di gruppo.

---

### Perché è *derivata* e non una query autonoma

Costruita su `vw_dash_competenza_attivita` per due ragioni che sarebbero
altrimenti da riscrivere e mantenere:

1. **Scope emittente gratis.** La base è `security_invoker=on` e filtra su
   `script.fn_get_emittenti_scope_sr_ids`: un operatore non può vedere né
   selezionare gruppi fuori dal suo perimetro. Non perché la regola sia ripetuta
   qui, ma perché è **la stessa sorgente**.
2. **Conteggi coerenti con la card per costruzione.** Il numero della card nasce
   dallo stesso `stadio` e dallo stesso `valore`. Una query parallela partirebbe
   identica e divergerebbe alla prima modifica di una delle due — è la lezione
   già pagata con le viste del riepilogo IVA.

---

### `stadio` è nel `GROUP BY`, non filtrato

La vista resta generale: è il **consumatore** a filtrare `DA_EMETTERE` per la
lista del cockpit.

Conseguenza: un gruppo parzialmente fatturato compare su **due righe**, una per
stadio. Non è un difetto — è l'informazione vera: dice all'operatore che di quel
documento una parte è già passata.

---

### ⚠️ Il riferimento leggibile passa da un `LATERAL`, non da un join

`vw_dash_fatturazione_documenti` ha una riga per **(documento, competenza_mese)**.
Un `LEFT JOIN` su `(area, documento_uid)` moltiplicherebbe le righe del gruppo
**prima** dell'aggregazione, gonfiando `n_attivita` e `valore` — cioè proprio i
due numeri che devono coincidere con la card.

Col `LATERAL ... LIMIT 1` applicato **dopo** l'aggregazione, l'etichetta non può
toccare i numeri.

La traduzione `sorgente → area` passa da `config.sorgenti.area`, il vocabolario
che prima del 2026-07-27 era scritto a mano dentro sei viste.

---

### ⚠️ Tutti i join sono `LEFT`, mai `INNER`

Un gruppo il cui documento non è risolvibile — sorgente senza `area`, documento
fuori dal perimetro della vista documenti — deve **comunque comparire**, con la
chiave grezza. Sparire dall'elenco significherebbe lavoro non azionabile: lo
stesso difetto che il concetto di gruppo esiste per evitare.

Il fallback del riferimento è a cascata: `codice del documento` → `codice della
commessa` → `chiave del gruppo`. Non si resta mai senza etichetta.

---

### Colonne principali

| Colonna | Note |
|---|---|
| `gruppo_key` | **esattamente** la stringa che i filtri `p_gruppi` accettano: il FE passa ciò che legge |
| `tipo_gruppo` | `codice_interno` della sorgente, oppure `ONERI_COMMESSA`. È un **codice**, non un'etichetta: la traduzione a video la fa il frontend (i18n) |
| `area_documento` | area documentale, `NULL` per i gruppi non sfogliabili |
| `riferimento` | numero del documento, o codice commessa, o chiave grezza |
| `n_attivita` · `valore` | il **peso** di ciò che si sta per fatturare, *prima* di agire |
| `ha_oneri` | difensivo: un gruppo dovrebbe essere interamente ONERE o interamente NORMALE |
| `stadio` | nel GROUP BY, vedi sopra |

---

### ⚠️ `security_invoker=on` va ri-specificato

La reloption **non compare** in `pg_get_viewdef` e PostgreSQL la **azzera** a
ogni `CREATE OR REPLACE` che non la ripete. Perderla trasformerebbe la vista in
`security_definer` di fatto, aprendo un buco nello scope emittente. Un pgTAP la
verifica (`test-vw-dash-competenza-gruppi-v1.sql`, caso 9).

---

### 🆕 Le colonne del 2026-08-15: display già decodificato

Due colonne aggiunte con `20260815-25`, su richiesta del backend
([brief-db-emittibilita-visibile-e-sbloccabile](/dev/work-in-progress/brief-db-emittibilita-visibile-e-sbloccabile)
§8.3 e §9 F3). Entrambe tolgono al repository una **seconda risoluzione della
stessa cosa**, e nessuna delle due costa un JOIN nuovo.

| Colonna | Da dove viene | Perché in vista |
|---|---|---|
| `commessa_stato_descrizione` | `stati_commessa`, `COALESCE(descrizione, codice)` | A video va la descrizione. Un codice interno dentro una frase — *«The job order is in state BOZZA»* — è il sintomo che la decodifica è finita lato client. Il JOIN la vista lo faceva già per `emittibile` e `codice_interno` |
| `documento_id` | la **stessa** LATERAL da cui esce `riferimento` | I drawer di dominio si aprono per **id**, e la vista esponeva solo codice e uid |

⭐ **Il punto che rende `documento_id` non cosmetico.** Finché l'id lo risolveva
il repository con una LATERAL sua, `riferimento` (il codice, dalla vista) e
`documento_id` (l'id, dal repository) potevano in linea di principio descrivere
**due documenti diversi**, se un giorno l'`ORDER BY` fosse cambiato da una parte
sola. Ora arrivano dalla stessa riga per costruzione: non è più una convenzione
da mantenere a mano.

ℹ️ `documento_id` è `NULL` per i gruppi **sourceless** (oneri di commessa,
`area_documento` `NULL` → la LATERAL non produce righe). È corretto: quei gruppi
un documento non ce l'hanno, e il frontend offre la sola commessa.

ℹ️ `COALESCE` e non `descrizione` nuda: la colonna è nullable a catalogo, e un
campo di **display** vuoto si legge come «non lo so» invece che come «manca il
dato».

---

### Nota per chi scrive test

La vista base è **fail-closed senza GUC**:
`script.fn_get_emittenti_scope_sr_ids(NULL)` restituisce l'array **vuoto** (non
`NULL`), quindi senza `app.current_user_id` **nessuna riga passa**. Un test che
non imposta la sessione misurerebbe zero *per il motivo sbagliato*.

Le due colonne nuove sono presidiate dai casi 14-15 di
`test-vw-dash-competenza-v1.sql`.

---

{% include-markdown "signature-core.md" %}
