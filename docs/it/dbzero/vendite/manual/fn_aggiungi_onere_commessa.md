## 📘 Documentazione Concettuale – Funzione `vendite.fn_aggiungi_onere_commessa(...)`

> 👀 **Vedi anche**
>
> [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita) ·
> [config.causali_onere](/dbzero/config/tabelle/causali_onere) ·
> [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) ·
> [vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita) ·
> [vendite.commesse_attivita_log](/dbzero/vendite/tabelle/commesse_attivita_log)

---

### 🎯 Scopo Principale

(rev 2026-07-23)

Madre DB della **porta oneri** (`brief-db-immutabilita-quantita-e-porta-oneri` §4c). Crea una
riga `commesse_attivita` di **puro valore** (`quantita = 1`, `tipo_movimento = 'ONERE'`), già
`APPROVATA`, partendo da un **articolo-onere**.

Il principio del brief: la commessa è un **libro giornale**, i fatti non si modificano — si
**aggiungono**. La porta oneri è l'unica via per caricare una voce di valore che non nasce da un
documento: qta fissa a 1 e importo positivo → una nota di credito travestita è **impossibile per
costruzione**. Nasce `APPROVATA` perché il presidio è **all'ingresso** (permesso dedicato lato
BE, `carica_voce_manuale`), non a valle: chi carica un onere è responsabile. Poi la riga fa il
**giro normale**: emissione → attività fatturabile → fattura.

Usabile da un endpoint interattivo **o** da un processo automatico autorizzato.

### Regole principali

* **Modello articolo↔causale**: riceve un **articolo-onere** (`catalogo.articoli.causale_onere_id`
  valorizzato, 1:1) e ne **deriva** causale, `uom` e — a valle — l'**IVA** (quella dell'articolo:
  ogni onere ha la propria aliquota). La causale è *snapshottata* su
  `commesse_attivita.causale_onere_id`.
* **Riga SOURCELESS**: nessuna sorgente documentale (`sorgente_tipo_id`/`sorgente_uid` = `NULL`);
  il discriminatore portante è `tipo_movimento = 'ONERE'` (+ causale + `segment_key` `MAN:`).
* **`quantita = 1`, importo solo positivo**: il prezzo È l'importo dell'onere.
* **`segment_key`** dedicata: `MAN:<commessa>:<progressivo>` (non si incrocia con i segment di
  push `ORD:`/`DDT:`).
* **`istanza_utility_id` e `tipo_doc_fiscale_id` obbligatori** (contesto reale): la riga nasce
  `APPROVATA` + `NON_EMESSA` = emittibile, quindi il `tipo_doc` deve essere valorizzato.
* Riusa `fn_upsert_commessa_attivita` (idempotenza su `segment_key`) ed è il **primo writer** di
  `commesse_attivita_log` (evento `ONERE_AGGIUNTO`, dettaglio pieno per audit).

---

### Concorrenza: perché il progressivo si calcola sotto lock

(`brief-db-race-segment-key-onere`, 2026-07-23)

Questa porta è il **primo scrittore concorrente reale** della funzione: i push dei documenti
sorgente si mettono in fila da soli (un worker alla volta), gli **operatori no** — due persone
possono caricare un onere sulla stessa commessa nello stesso istante.

Il problema, se il progressivo si calcola senza precauzioni: entrambe le chiamate leggono lo
stesso numero, costruiscono la **stessa** `segment_key`, e `fn_upsert_commessa_attivita` — che
per progetto è idempotente sulla coppia `(commessa, segment_key)` — **aggiorna la riga della
prima invece di crearne una nuova**. Il risultato non è "un onere in meno": l'importo del primo
onere **sparisce** (si fattura di meno), la riga sopravvissuta porta articolo e causale del
secondo ma può conservare il *motivo* del primo, e **nessuno riceve un errore** — entrambe le
chiamate rispondono OK. Un ammanco silenzioso, che nessun controllo a valle intercetta.

Tre presidi, dal più esterno al più interno:

1. **Lucchetto per commessa** (`pg_advisory_xact_lock`): chi arriva secondo aspetta il primo, e
   ricalcola il progressivo quando la riga dell'altro è già registrata. Il lucchetto vale solo
   per la **singola commessa** (due operatori su commesse diverse non si ostacolano mai) e si
   toglie da solo a fine transazione.
2. **Progressivo dal numero più alto già usato**, non dal conteggio delle righe: contare
   presuppone che nessuna riga sia mai stata cancellata. Una sola cancellazione e il conteggio
   punterebbe su un numero già assegnato — stessa collisione, anche senza concorrenza. I
   **buchi nella numerazione sono ammessi** e non significano nulla.
3. **Guard `E_ONERE_SEGMENT_DUPLICATO`**: la porta oneri è una **creazione**, mai un
   aggiornamento. Se malgrado tutto la scrittura risultasse un aggiornamento, la funzione
   **fallisce a voce alta** invece di sovrascrivere il lavoro di un altro. Non deve mai scattare:
   se scatta, è il sintomo di una regressione (o di una transazione con impostazioni di
   isolamento non standard).

Il guard vive **qui** e non dentro `fn_upsert_commessa_attivita`: là l'aggiornamento è la
semantica giusta (rileggere un documento sorgente due volte deve dare lo stesso risultato, non
un doppione).

---

### Parametri

| Parametro | Tipo | Note |
|-----------|------|------|
| `p_commessa_id` | `bigint` | Commessa destinataria. Obbligatorio (>0). |
| `p_istanza_utility_id` | `bigint` | Istanza utility/servizio a cui l'onere si riferisce. Obbligatorio (>0). |
| `p_articolo_onere_id` | `uuid` | Articolo-onere (attivo, con `causale_onere_id`). Da qui si derivano causale/uom/IVA. |
| `p_importo` | `numeric` | Importo dell'onere. Solo positivo (>0). |
| `p_tipo_doc_fiscale_id` | `bigint` | Tipo documento fiscale della riga (emittibile). Obbligatorio (>0). |
| `p_motivo` | `text` | Motivo libero (audit). Default `NULL`; finisce in `meta.motivo_onere` e nel log. |
| `p_data_attivita` | `date` | Data attività. Default `NULL` → oggi (`CURRENT_DATE`); la competenza segue. |

---

### 📦 Output

| Tipo | Descrizione |
|------|-------------|
| `bigint` | `id` della riga `commesse_attivita` (onere) creata |

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_PARAMETRO_INVALIDO` | `commessa_id` / `istanza_utility_id` / `tipo_doc_fiscale_id` `NULL` o `<= 0` |
| `E_ONERE_IMPORTO_NON_VALIDO` | `importo` `NULL` o `<= 0` |
| `E_ONERE_ARTICOLO_MANCANTE` | `p_articolo_onere_id` inesistente, non attivo, o senza causale (non è un onere) |
| `E_ONERE_SEGMENT_DUPLICATO` | La scrittura ha **aggiornato** una riga esistente invece di crearne una nuova (collisione di `segment_key`). Non deve mai accadere: è la rete di sicurezza contro la sovrascrittura silenziosa. Rimedio: ripetere l'operazione. |

---

### Esempio d'uso

```sql
-- Carica una penale di 150,00 sulla commessa 42 (articolo-onere ONERE_PENALE).
SELECT vendite.fn_aggiungi_onere_commessa(
  p_commessa_id         => 42,
  p_istanza_utility_id  => 7,
  p_articolo_onere_id   => (SELECT id FROM catalogo.articoli WHERE codice = 'ONERE_PENALE'),
  p_importo             => 150.00,
  p_tipo_doc_fiscale_id => 1,
  p_motivo              => 'Ritardo consegna oltre termine contrattuale'
);
```

---

{% include-markdown "signature-core.md" %}
