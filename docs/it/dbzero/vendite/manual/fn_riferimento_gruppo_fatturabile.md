## 📘 Documentazione Concettuale – Funzione `vendite.fn_riferimento_gruppo_fatturabile`

> **Ultimo aggiornamento**: 8 novembre 2026

> 👀 **Vedi anche**
>
**Approfondimento funzioni:**
>
• [vendite.fn_split_gruppo_fatturabile_key](/dbzero/vendite/funzioni/fn_split_gruppo_fatturabile_key)
> • [vendite.fn_build_gruppo_fatturabile_key](/dbzero/vendite/funzioni/fn_build_gruppo_fatturabile_key)
> • [vendite.fn_get_sorgente_documento_ref](/dbzero/vendite/funzioni/fn_get_sorgente_documento_ref)
> • [vendite.fn_list_lotto_segnalazioni](/dbzero/vendite/funzioni/fn_list_lotto_segnalazioni)
>
**Approfondimento viste:**
>
• [vendite.vw_dash_competenza_gruppi](/dbzero/vendite/views/vw_dash_competenza_gruppi)

---

### 🎯 Scopo Principale
(latest review 2026-09-08)

Risponde a: **«come si chiama, per una persona, il documento che questa chiave
identifica?»**

```
ORDINE_VENDITA:01a06ce4-35a6-721a-9cd8-9da48bf77626   ->   ORD0036004
```

---

### Perché serve: chiave e etichetta non sono la stessa cosa

Sono lo stesso documento scritto in due modi, e servono a due destinatari
diversi:

| | A chi serve | Perché |
| --- | --- | --- |
| la **chiave** (`gruppo_key`) | al **programma** | `vendite.fn_escludi_documento_da_giro` la vuole: è quello che il pulsante «Togli dal giro» manda |
| il **riferimento** | alla **persona** | `ORD0036004` è ciò che l'operatore riconosce, cerca e sa dire al telefono |

Fino al 2026-09-08 la scheda Critiche del lotto mostrava la **chiave**: un uuid
lungo, in una colonna intitolata «Documento». Ora la chiave continua a viaggiare
in riga per il pulsante, e a video compare il riferimento.

---

### Il ripiego a tre livelli, e perché l'ultimo non è una resa

1. il **numero del documento**, risolto da
   [`fn_get_sorgente_documento_ref`](/dbzero/vendite/funzioni/fn_get_sorgente_documento_ref)
   leggendo il `label_selector` che la sorgente dichiara a catalogo;
2. il **codice della commessa** — serve alla forma sourceless (`MAN:<id>`), dove
   un documento non c'è **per progetto**: lì il contenitore *è* la commessa; e a
   un documento **senza numero** (un consumo). Per quello vale la commessa che il
   chiamante dichiara per il suo contesto (`p_commessa_id`: la scheda Critiche
   passa la commessa del documento **in quel lotto**); senza, la commessa
   **aperta** in cui il documento sta oggi
   ([`fn_commessa_viva_di_sorgente`](/dbzero/vendite/funzioni/fn_commessa_viva_di_sorgente));
3. la **chiave grezza**.

⭐ Il terzo livello è esattamente ciò che l'operatore vedeva **prima** di questa
funzione: peggiorare è impossibile. È il motivo per cui non serve nessun errore
quando una chiave non si risolve.

---

### ⚠️ `NULL` entra e `NULL` esce

Una `gruppo_key` assente significa *«la segnalazione è del **giro**»* — un
emittente non risolto, una configurazione mancante. Lì non c'è nessun documento
da nominare, e inventare un'etichetta direbbe una cosa falsa. La colonna resta
vuota, ed è quella l'informazione.

---

### ⛔ Non solleva mai, e non è pigrizia

La chiama una **lista**. Una chiave storta deve produrre una cella col ripiego,
non una lista rotta — la stessa regola già scritta in testa a
`fn_get_sorgente_documento_ref`.

---

### ⚠️ La seconda scrittura, dichiarata

[`vw_dash_competenza_gruppi.riferimento`](/dbzero/vendite/views/vw_dash_competenza_gruppi)
fa la **stessa** scala di ripiego e **non** chiama questa funzione. È una scelta
con un costo scritto: là il `LATERAL` su `fn_get_sorgente_documento_ref` serve
comunque, perché da quello esce anche `documento_id` — passare dalla chiave
vorrebbe dire risolvere **due volte per riga** su una vista di dashboard, e
riprodurre il corpo di una vista grande (con la sua `security_invoker`, che si
azzera a ogni `CREATE OR REPLACE`) per spostare una riga.

⇒ La seconda scrittura **resta e si presidia**: un pgTAP chiede alle due la
stessa stringa sulla stessa chiave.
⚠️ Prova che **oggi** coincidono, non che non possano divergere. È un ripiego
dichiarato, non un pareggio.

---

### ⭐ La commessa del contesto vince su quella aperta (2026-11-08)

«In quale commessa aperta sta il documento» e «di quale commessa era il
documento in quel lotto» sono due domande diverse. La prima risponde dove il
documento si riusa **oggi**: a commessa chiusa non risponde, e se il documento è
rientrato in un'altra commessa dà quella nuova. La scheda Critiche fa la seconda,
e la risposta la conosce chi ha scritto la segnalazione
(`fatturazione_lotti_log.commessa_id`): per questo il chiamante la passa, e vince.

---

### Regole

* funzione **pura**: non scrive niente. `STABLE`, `SECURITY INVOKER`;
* **non risale a `commesse_attivita`**: la chiave su una segnalazione è un
  **fatto storico**, e quel lavoro può essere già fatturato, annullato o uscito
  dal giro — la colonna si svuoterebbe *proprio dopo*, e la scheda Critiche si
  legge dopo;
* l'aggancio della sorgente è su `codice_interno`, mai su `codice`
  (linee-guida-sql §6c/§6d).

---

### Esempio d'uso

```sql
SELECT vendite.fn_riferimento_gruppo_fatturabile(
    'ORDINE_VENDITA:01a06ce4-35a6-721a-9cd8-9da48bf77626');
-- ORD0036004

SELECT vendite.fn_riferimento_gruppo_fatturabile('MAN:42');
-- il codice della commessa 42

SELECT vendite.fn_riferimento_gruppo_fatturabile(NULL);
-- NULL: la segnalazione e' del GIRO

SELECT vendite.fn_riferimento_gruppo_fatturabile(
    'ATTIVITA_CONSUMI:7c1e…', p_commessa_id => 42);
-- il codice della commessa 42, anche se oggi e' chiusa
```

> Piano e decisioni: `docs/it/dev/work-done/brief-db-uscita-documento-dal-giro.md` §6.2;
> la commessa del contesto: `brief-db-sorgente-documento-e-riga` §8.22 (V-7-bis, 2026-11-08).

---

{% include-markdown "signature-core.md" %}
