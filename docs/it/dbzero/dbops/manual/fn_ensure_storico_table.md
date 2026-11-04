## 📘 Documentazione Concettuale – Funzione `dbops.fn_ensure_storico_table`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log) — creazione, simulazione e cessione della shadow
> * [dbops.error_log](/dbzero/dbops/tabelle/error_log) — dove finisce un errore, prima di uscire
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_storico_provision](/dbzero/dbops/funzioni/fn_run_automations_storico_provision) — il runner che la chiama per ogni tabella con la colonna `storicizza`
> * [dbops.fn_storico_arma_scope](/dbzero/dbops/funzioni/fn_storico_arma_scope) — la forma dello scope congelato, applicata alla shadow appena nata
> * [dbops.fn_run_automations_storico](/dbzero/dbops/funzioni/fn_run_automations_storico) — monta poi il trigger che scrive nella shadow
> * [script.fn_sqlstate_di_ambiente](/dbzero/script/funzioni/fn_sqlstate_di_ambiente) — distingue un guasto dell'ambiente da un difetto
>
> Guide:
>
> * [Storicizzazione delle tabelle](/guide/storicizzazione-tabelle) — la struttura standard delle tabelle di storico

---

### 🎯 Scopo Principale

Crea, se non esiste, la tabella di storico `storico.<tabella>` di una tabella madre, con la struttura
standard, la arma con lo scope congelato e la cede al proprietario della madre. Se la shadow c'è già
non fa niente: non la aggiorna e non la arma, quello è compito della convergenza.

---

### La struttura che crea

* un `id` proprio, indipendente dalla chiave della madre;
* la colonna che lega la versione alla madre, col nome ricevuto dal chiamante e lo stesso **tipo**
  della chiave primaria della madre: la chiave monocolonna, altrimenti la colonna `id`;
* lo snapshot `jsonb` della riga, il tipo di cambiamento e di operazione, chi e quando ha scritto,
  la transazione, la finestra di validità;
* un indice sulla colonna di legame e, se la regola lo chiede, un indice GIN sullo snapshot.

⛔ **Nessuna FK verso la madre**, per scelta: bloccherebbe la cancellazione delle righe della madre,
e uno storico deve sopravvivere alla riga che racconta.

Il nome della shadow è il nome **nudo** della madre: due madri omonime in schemi diversi
condividono la stessa shadow, e la crea la prima che passa. Le distingue `origine_schema`.

---

### ⭐ La shadow nasce armata

Creata la tabella, la funzione chiama `fn_storico_arma_scope`: la shadow riceve subito
`origine_schema` (`NOT NULL`, perché è vuota), lo scope con il suo indice, la revoca del `DELETE`
all'applicazione e, se la mappa dice che la madre è protetta, la row level security con le sue
policy. Un errore lì dentro esce come errore della creazione: una shadow senza scope non nasce
zitta.

---

### ⭐ L'archivio di una tabella è di chi possiede la tabella

Creata e armata, la shadow viene **ceduta al proprietario della madre**. Arma chi la crea, perché in
quel momento ne è proprietario; poi la cede. La cessione avviene solo se chi crea **può** farla —
superuser, o membro del ruolo proprietario della madre: altrimenti un `WARN` nell'audit, e la shadow
resta di chi l'ha creata. Mai un errore che fermi la storicizzazione.

Così la convergenza da Liquibase, che lavora solo sulle shadow del migratore, le trova sempre.

---

### Simulazione

In simulazione non esegue niente: registra nell'audit la tabella che verrebbe creata e si ferma.
Non arma e non cede. ⚠️ La ricerca della chiave della madre avviene comunque: una madre senza chiave
utilizzabile solleva anche in simulazione.

---

### Codici errore

* `E_STORICO_PARENT_PK_NOT_FOUND` — la madre non ha una chiave primaria monocolonna né una colonna
  `id`: non si sa di che tipo fare la colonna di legame. Si solleva prima di creare qualsiasi cosa.
* `E_STORICO_PROVISION` — la creazione, l'armatura o la cessione falliscono. ⚠️ Un guasto
  dell'**ambiente** (connessione, risorse, arresto, privilegio, lock) si scrive nel registro errori
  con questo codice e poi si rilancia **col suo SQLSTATE**; un difetto di struttura esce col codice.

Gli errori e l'audit sono registrati sotto il nome del runner `fn_run_automations_storico_provision`,
non di questa funzione.

---

### Test

* `db/pgtap/storico/test-storico-scope-congelato-v1.sql` — la shadow di prova nasce armata (RLS, tre
  policy, `origine_schema NOT NULL`), e ogni shadow ha lo stesso proprietario della propria madre.
* `db/pgtap/dbops/test-automazioni-guasto-ambiente-rilanciato-v1.sql` — il gestore d'errore apre il
  ramo dell'ambiente (registro errori, poi rilancio dell'originale) e usa lo stesso contesto
  nell'involucro (presidio sul testo).

---

### Note di migrazione

* 2025-12-26 — nasce come generatore delle shadow; la FK verso la madre, prevista all'inizio, non si
  crea più.
* 2026-09-11 — la shadow nasce armata con lo scope congelato, e viene ceduta al proprietario della
  madre (`brief-db-rls-storico-scope-congelato`, §4b e §4d). Fino ad allora le shadow create dal job
  pgAgent nascevano del ruolo con cui il job si collegava, e i changeSet non potevano alterarle.
* 2026-10-16 — un guasto dell'ambiente si rilancia col suo SQLSTATE invece di diventare l'errore
  dell'involucro (`brief-db-presidio-job-run-a-chi-tocca`, D8, D11).

---

{% include-markdown "signature-core.md" %}
