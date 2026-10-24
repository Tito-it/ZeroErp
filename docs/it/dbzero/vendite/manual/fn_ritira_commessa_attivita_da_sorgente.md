## 📘 Documentazione Concettuale – Funzione `vendite.fn_ritira_commessa_attivita_da_sorgente`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)  
> • [vendite.commesse_attivita_log](/dbzero/vendite/tabelle/commesse_attivita_log)  
>
**Approfondimento funzioni:**
>
• [script.fn_check_sorgente_chiudibile](/dbzero/script/funzioni/fn_check_sorgente_chiudibile)  
> • [vendite.fn_documento_ritira_legami](/dbzero/vendite/funzioni/fn_documento_ritira_legami) — chi la chiama, dopo la conferma dell'annullo  
> • [vendite.fn_annulla_commessa_attivita](/dbzero/vendite/funzioni/fn_annulla_commessa_attivita)  

---

### 🎯 Scopo Principale
(latest review 26-08-2026)

**Il ritiro: il documento riprende ciò che aveva spinto.** Porta ad `ANNULLATA`
le sole righe di commessa in **`NON_EMESSA`** della sorgente indicata, e lascia
una riga di registro **per ciascuna**. Restituisce **quante** ne ha ritirate.

---

### ⭐ È l'oggetto di una promessa che il modello faceva già per iscritto

Il guard 4 di
[`fn_annulla_commessa_attivita`](/dbzero/vendite/funzioni/fn_annulla_commessa_attivita)
dice, da sempre:

> *«per una riga da push il rimedio è **SEMPRE a monte, sul documento**»*

⛔ Fino al 26 agosto 2026 quella frase era **una promessa senza oggetto**:
annullare l'ordine fermava i push **futuri** e non ritirava niente di ciò che era
già passato. Il lavoro restava in commessa, fatturabile, e l'unico modo di
uscirne era **essere fatturato**.

Questa funzione è l'oggetto.

---

### ⭐ Le due funzioni sono complementari, non in contraddizione

| | perimetro |
| --- | --- |
| `fn_annulla_commessa_attivita` | **rifiuta** le righe con sorgente, e lavora sulle **sourceless** |
| **questa** | lavora **solo** su quelle **con** sorgente |

Insieme coprono il piano, e nessuna delle due invade l'altra.

⚠️ Le righe **sourceless** — `ONERE` e `RETTIFICA` — non hanno sorgente e il
ritiro per sorgente **non le trova**. È corretto: per l'onere la via è
`fn_annulla_commessa_attivita`, per la rettifica
`fn_annulla_accredito_riga_reso`. È la stessa distinzione **origine / natura**
che ha morso il dominio il 20 agosto 2026.

---

### ⛔ La chiave, e sbagliarla non dà errore

`p_sorgente_uid` è **`<testata>.uid::text`**, per ogni sorgente: è ciò che le
cinque `fn_list_*_da_pushare` scrivono in `commesse_attivita.sorgente_uid`.

⚠️ **Non** è la chiave di `vendite.commesse_sorgenti`, che varia per sorgente
(`uid` per il preventivo, `id::text` per l'ordine). Passare quella sbagliata non
solleva niente: **ritira zero righe**, cioè un ritiro che non ritira.

⭐ È il motivo per cui la funzione restituisce un **conteggio** invece di `void`,
e per cui c'è un test apposta.

---

### ⚠️ Il motivo è obbligatorio, come per l'annullamento manuale

`ANNULLATA` è **irreversibile**: `fn_approva_commessa_attivita` la filtra e non
esiste ripristino. L'unica traccia del *perché* è l'evento di registro, e a mesi
di distanza un importo sparito senza spiegazione è indistinguibile da un difetto.

⭐ **Qui vale il doppio**: chi chiude il documento non sta guardando la commessa,
e il ritiro è per lui un **effetto a distanza**.

---

### ⚠️ Un ritiro è una cascata silenziosa, e si paga col registro

Una riga di `vendite.commesse_attivita_log` — evento
**`RIGA_RITIRATA_DA_SORGENTE`** — **per riga ritirata**, con il motivo, lo stato
precedente, la sorgente, il `segment_key`, il prezzo e il tipo movimento.

Senza, «il lavoro è sparito» diventa indistinguibile da un difetto — che è
esattamente il male da cui nasce il cantiere.

ℹ️ La colonna `evento` non ha `CHECK` né tabella-vocabolario: **nessun seed da
estendere**.

---

### Cosa scrive, e in che ordine

1. **fotografa** le righe `NON_EMESSA` della sorgente — *prima* di annullarle:
   lo stato precedente è ciò che il registro deve raccontare, e l'`UPDATE` lo
   sovrascrive. È la stessa disciplina del riordino di
   `fn_cleanup_fatture_by_ids`: **si legge il dato finché è vivo**;
2. **porta ad `ANNULLATA`** le sole `NON_EMESSA`;
3. **scrive il registro**, riga per riga.

⚠️ `FOR UPDATE` con `ORDER BY id`: serializza i concorrenti ed evita il deadlock
fra due chiusure che si intersecano in ordine opposto.

⚠️ Il predicato è scritto **in positivo** (`= 'NON_EMESSA'`) e non come
`<> 'EMESSA'`: se domani il `CHECK` ammettesse un quarto stato, il default resta
il **non toccarlo** — fail-closed su un verbo irreversibile.

---

### Esempio d'uso

```sql
-- Ritiro manuale (il caso normale passa dal trigger)
SELECT vendite.fn_ritira_commessa_attivita_da_sorgente(
    (SELECT id FROM config.sorgenti WHERE codice_interno = 'ORDINE_VENDITA'),
    (SELECT uid::text FROM vendite.ordini WHERE id = 41),
    'Ritiro manuale: ordine chiuso per errore di inserimento');
-- → 3

-- Chiave sbagliata: nessun errore, e nessun ritiro
SELECT vendite.fn_ritira_commessa_attivita_da_sorgente(6, '41', 'prova');
-- → 0   ⛔ è il modo silenzioso in cui questo verbo può fallire
```

---

### ⭐ Una sorgente, una commessa: `p_commessa_id` (dal 2026-10-12)

Quarto parametro, in coda e `DEFAULT NULL` (brief-db-annullo-a-valle-riapre-a-monte, D-1):

| `p_commessa_id` | Chi lo usa | Cosa ritira |
| --- | --- | --- |
| `NULL` | l'annullo di un **documento** | le righe della sorgente in tutte le commesse: il documento riprende tutto ciò che ha spinto |
| valorizzato | l'annullo di una **commessa** | le sole righe di quella commessa: la stessa sorgente può avere righe vive in un'altra commessa, che non c'entra |

Il filtro è residuo: l'accesso resta dalla coppia sorgente. La firma è cambiata
(`DROP` + `CREATE`, `20261012-18`); le chiamate a tre argomenti restano valide.

---

### Note operative

* **`SECURITY INVOKER`**: `commesse_attivita` ha la RLS, e lo scope resta quello
  del chiamante. ⚠️ Chi non vede le righe ne ritira **zero**, e il conteggio è
  l'unico modo di accorgersene.
* `stato_approvazione` resta com'è: sono due assi distinti, e una riga ritirata
  conserva la memoria di essere stata approvata.
* `data_update` / `user_update` / `tx_id` / storico: li mettono i trigger.
* Non è raggiungibile dall'interfaccia: la chiama il BB
  [`fn_documento_ritira_legami`](/dbzero/vendite/funzioni/fn_documento_ritira_legami)
  dentro i verbi di annullo (`fn_annulla_ddt`, `fn_annulla_ordine`,
  `fn_annulla_preventivo`, `fn_annulla_contratto`), **dopo la conferma** di chi
  annulla. Fino al 2026-10-11 la chiamava in silenzio un trigger `_z90_`
  all'ingresso in uno stato abortito (brief-db-annullo-documento-con-legami, D-5).
  Il motivo registrato è ora «Ritiro all'annullo confermato del documento di
  origine (…)».
* Test: `db/pgtap/vendite/test-ritiro-commessa-attivita-da-sorgente-v1.sql`
  (10 test). ⭐ Il **7** è quello che vale: con la chiave sbagliata ritira zero e
  non solleva.
* Cantiere: `brief-db-lavoro-che-non-torna-indietro.md`, lotto L7 / Q-5′ strada A.

---

{% include-markdown "signature-core.md" %}
