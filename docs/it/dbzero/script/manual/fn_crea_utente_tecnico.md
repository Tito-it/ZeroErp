## 📘 Documentazione Concettuale – Funzione `script.fn_crea_utente_tecnico`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [dbops.processi](/dbzero/dbops/manual/processi)
> • [dbops.processi_identita](/dbzero/dbops/manual/processi_identita)
> • [anagrafiche.identita_digitali](/dbzero/anagrafiche/manual/identita_digitali)
>
**Approfondimento funzioni:**
>
• [script.fn_log_and_raise_error](/dbzero/script/manual/fn_log_and_raise_error)
>

### 🎯 Scopo Principale
(latest review 04-09-2026)

Crea **l'utente con cui un processo automatico lavora i documenti di
un'azienda**.

Un lavoro notturno che emette fatture deve poter rispondere a *«per conto di chi
stai scrivendo?»* esattamente come una persona che usa l'applicazione. Questa
funzione gli dà quella risposta: un utente vero, con un perimetro vero, che
**non può fare login**.

---

### Firma

```sql
script.fn_crea_utente_tecnico(
    p_processo_codice text,                        -- il processo in dbops.processi
    p_emittente_codice varchar,                    -- ⛔ OBBLIGATORIO: quale azienda
    p_profilo_codice   varchar DEFAULT NULL        -- di norma NON si passa
) RETURNS integer  -- l'auth_user_id creato
```

---

### ⭐⭐ L'azienda è OBBLIGATORIA, ed è costitutiva — non un parametro in più

È la cosa da capire prima di usare la funzione.

> **In questo sistema un utente ha UNA sola azienda.** Multi-azienda è **solo**
> il super admin.

⇒ Non esiste «l'utente tecnico della fatturazione». Esiste *«l'utente tecnico
della fatturazione **per l'azienda Rossi**»*, e se le aziende sono tre gli
utenti sono tre. La funzione si chiama una volta per coppia.

⚠️ **Non era l'idea di partenza.** La parola «whitelist» faceva pensare a una
lista di aziende per utente, e il piano diceva «tutte le aziende all'utente
tecnico». Il modello dice il contrario, e il piano è stato riscritto.

---

### Che cosa costruisce, in un colpo solo

| | |
| --- | --- |
| utente Django | password **inutilizzabile** (prefisso `!`): nessuno può fare login al posto del processo |
| soggetto | un soggetto dedicato, col suo contatto |
| soggetto-ruolo | di tipo `PROC_AUTO` — il tipo riservato ai processi |
| identità digitale | ruolo `OPERATORE`, con il flag `tecnica` |
| perimetro | la riga in `config.user_emittenti_fiscali`: **quell'azienda e basta** |
| legame | la riga in [processi_identita](/dbzero/dbops/manual/processi_identita) |

⭐ È **una unità sola**: o esistono tutti i pezzi, o non ne esiste nessuno. Un
utente creato a metà — con l'identità ma senza perimetro, o viceversa — sarebbe
peggio di nessun utente: girerebbe, e vedrebbe le cose sbagliate.

---

### ⭐ Il profilo di norma NON si passa

Un profilo di accesso porta **capability**, cioè permessi applicativi. Un
processo automatico non deve premere pulsanti: fa una cosa sola, e la fa
attraverso il proprio codice.

⇒ Il default è **zero capability**, che è il minimo privilegio. Se serve un
profilo, dev'essere di tipo `AD_HOC`. ⛔ Mai `SUPER_ADMIN`: darebbe al processo
il bypass su ogni perimetro, cioè esattamente ciò che questo cantiere toglie.

---

### I guard, e perché ci sono

* **Il processo deve volerlo davvero**: vivo (ritiro non raggiunto, con la
  regola di `script.fn_e_obsoleto`: un ritiro programmato è ancora vivo fino al
  suo giorno), di classe `DOMINIO`, su canale `PGAGENT`, `COMMAND` o
  `CODA_AUTOMATICA`. ⛔ Un processo di **coda** viene
  rifiutato: gira con l'identità dell'operatore che lo accoda, e dargli un
  utente tecnico cancellerebbe il nome di quella persona.
* **L'azienda deve esistere ed essere attiva.**
* **Il profilo, se passato, dev'essere `AD_HOC`** e mai super admin.

Ogni rifiuto passa da `fn_log_and_raise_error` con un codice registrato: chi
legge l'errore sa quale invariante ha toccato, non solo che «non ha funzionato».

---

### ⚠️ È DATO DI MACCHINA, non catalogo

Le chiamate a questa funzione vivono in changeSet nel contesto
`dati_macchina`, che la **CI non esegue**: dipendono da quali aziende esistono
su quella installazione, e creano righe che puntano a `django.auth_user`.

⇒ Un ambiente nuovo nasce **senza** utenti tecnici. Non è una dimenticanza: è
il motivo per cui esistono i presidi
[vw_processi_dominio_senza_identita](/dbzero/dbops/manual/vw_processi_dominio_senza_identita)
e [vw_emittenti_non_serviti](/dbzero/dbops/manual/vw_emittenti_non_serviti),
che lo dicono subito invece di lasciarlo scoprire alla prima fatturazione muta.

---

### Esempio d'uso

```sql
-- Un utente tecnico per la fatturazione batch dell'azienda ACME
SELECT script.fn_crea_utente_tecnico('run_fatturazione_batch', 'ACME');

-- Verifica: i due presidi devono tornare vuoti
SELECT * FROM dbops.vw_processi_dominio_senza_identita;
SELECT * FROM dbops.vw_emittenti_non_serviti;
```

Origine: `docs/it/dev/work-done/brief-db-processi-automatici-identita-e-perimetro.md` §4.

---

{% include-markdown "signature-core.md" %}
