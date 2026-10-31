## 📘 Documentazione Concettuale – Tabella `dbops.automazione_chiusura_scadenze`

> 👀 **Vedi anche**
>
Guide:
> [Processi pgAgent funzionali](/guide/processi-pgagent-funzionali)
> [Automazione DB](/guide/automazione-db)
> [Linee guida SQL §7c — Ciclo stato + finestra di validita'](/linee-guida-sql)
>
Approfondimento tabelle:
> [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni)
> [vendite.contratti](/dbzero/vendite/tabelle/contratti)
>
Approfondimento funzioni:
> [dbops.fn_apply_chiusura_scadenze](/dbzero/dbops/funzioni/fn_apply_chiusura_scadenze)
>
WIP:
> [Automazione chiusure per scadenza](/dev/work-done/automazione-chiusure-scadenze)

### 🎯 Scopo Principale

(latest review 26-04-2026)

La tabella **`dbops.automazione_chiusura_scadenze`** centralizza la
configurazione del **framework parametrico di chiusura per scadenza**
applicato alle tabelle che presentano il pattern **"ciclo stato +
finestra di validita'"** (linee-guida-sql §7c).

Ogni riga descrive una tabella target e i parametri necessari alla
funzione `dbops.fn_apply_chiusura_scadenze()` per portare lo stato
gestionale al valore "chiuso" quando `valido_al < CURRENT_DATE`. La
funzione e' invocata dal job pgAgent unico `chiusura_scadenze_daily`
ogni notte alle 00:05.

Il framework e' la **promozione al nucleo `dbops`** del pattern gia'
applicato a `vendite.listini_versioni` (24-04-2026) e
`vendite.contratti` (26-04-2026), secondo il principio §7 del
manifesto sviluppo concentrico (due consumatori reali → astrazione
validata).

---

### ⭐ Il verbo di chiusura (rev 2026-10-28)

* **`verbo_chiusura`** *(text NULL)* – per una testata sotto la porta del modello del documento:
  il verbo che chiude le righe scadute (`schema.funzione`, senza argomenti, ritorna quante ne ha
  chiuse). Oggi `vendite.fn_cessa_contratti_scaduti` (contratti),
  `vendite.fn_chiudi_preventivi_scaduti` (preventivi, EMESSO -> SCADUTO, dal 31-10-2026,
  `col_valido_al = validita_al`) e
  `vendite.fn_chiudi_versioni_listino_scadute` (versioni di listino, che dal 28-10-2026 hanno lo
  stato nel vocabolario `config.stati_doc_listino_versioni`: `tipo_stato = FK`). NULL = nessuna
  porta, il framework fa l'`UPDATE` dinamico.

### Campi chiave e semantica

* **`id`** *(smallserial PK)* – id tecnico della riga di config.
* **`schema_tabella`** *(text NN)* – schema PostgreSQL della tabella target (es. `vendite`).
* **`nome_tabella`** *(text NN)* – nome tabella target (es. `listini_versioni`, `contratti`).
* **`col_stato`** *(text NN)* – nome colonna stato sulla tabella target (es. `stato`, `stato_doc_contratto_id`).
* **`tipo_stato`** *(text NN, CHECK IN `VARCHAR`/`FK`)* – discrimina la modalita' di lookup del codice stato:
  * `VARCHAR`: la colonna stato contiene direttamente il codice (varchar + CHECK constraint sui valori ammessi);
  * `FK`: la colonna stato e' FK a una tabella catalogo, il codice viene risolto via lookup su `codice_interno`.
* **`col_valido_al`** *(text NN, default `valido_al`)* – nome colonna data fine validita'.
* **`stato_attivo_codice`** *(text NN)* – valore stato pre-chiusura. Per `VARCHAR` e' il valore stesso (es. `ATTIVA`); per `FK` e' il `codice_interno` della riga lookup (es. `ATTIVO`).
* **`stato_chiuso_codice`** *(text NN)* – valore stato post-chiusura. Semantica analoga (`CHIUSA` per VARCHAR, `CESSATO` come codice_interno per FK).
* **`fk_lookup_schema`** *(text NULL)* – per `tipo_stato='FK'`: schema della tabella di lookup (es. `config`).
* **`fk_lookup_table`** *(text NULL)* – per `tipo_stato='FK'`: nome tabella di lookup (es. `stati_doc_contratti`).
* **`fk_lookup_codice_col`** *(text NULL)* – colonna chiave logica per il match (tipicamente `codice_interno`). Va specificata esplicitamente per `tipo_stato='FK'`.
* **`fk_lookup_id_col`** *(text NULL)* – colonna PK della tabella di lookup, usata come valore da scrivere nella `col_stato` target (tipicamente `id`). Va specificata esplicitamente per `tipo_stato='FK'`.
* **`classe`** *(text NN, CHECK)* – ⭐ *(dal 2026-09-04)* la natura del
  **bersaglio**: `MANUTENZIONE` | `AMMINISTRAZIONE` | `DOMINIO`. Vedi sotto.
* **`attivo`** *(boolean NN, default true)* – abilita/disabilita la riga senza eliminarla.
* **`descrizione`** *(text)* – documentazione inline sul caso d'uso.
* **Audit** – `data_insert`, `user_insert`, `data_update`, `user_update`, `tx_id`.

---

### Vincoli

| Tipo | Nome | Descrizione |
| --- | --- | --- |
| PK | `pk_automazione_chiusura_scadenze` | `id` |
| UNIQUE | `uq_automazione_chiusura_scadenze_target` | `(schema_tabella, nome_tabella)` — una sola riga per tabella |
| CHECK | `chk_automazione_chiusura_scadenze_tipo_stato` | `tipo_stato IN ('VARCHAR','FK')` |
| CHECK | `chk_automazione_chiusura_scadenze_fk_coerente` | per `tipo_stato='VARCHAR'` i campi `fk_lookup_*` devono essere NULL; per `tipo_stato='FK'` tutti valorizzati |
| CHECK | `chk_automazione_chiusura_scadenze_classe` | `classe IN ('MANUTENZIONE','AMMINISTRAZIONE','DOMINIO')` |

L'indice parziale `ix_automazione_chiusura_scadenze_attivo` su `(id) WHERE attivo IS TRUE` supporta la lettura tipica del job (filtra solo righe attive).

---

### ⭐ Rev 2026-09-04 — la classe sta sul BERSAGLIO, non sul job

È il caso che non entrava nello schema generale, e va spiegato perché la
soluzione è diversa da quella degli altri processi.

`chiusura_scadenze_daily` è **un solo job** che chiude scadenze su **più
tabelle**. Le tabelle però non sono tutte uguali: `vendite.contratti` e
`vendite.listini_versioni` appartengono a un'azienda, un'eventuale tabella
tecnica no.

⛔ Mettere la classe sul **job** avrebbe costretto a scegliere una natura sola
per tutte le tabelle: o si dichiara di dominio un lavoro che tocca anche cose di
nessuno, o si dichiara di manutenzione un lavoro che tocca fatture.

⇒ La classe sta su **ogni riga di configurazione**, cioè su ogni bersaglio.

⚠️ **Il `NOT NULL` è il cancello della cosa**: una riga nuova nel CSV
*deve* dichiarare che natura ha. Senza, arruolerebbe un'altra tabella nel giro
notturno senza dire di chi sono le righe che tocca — che è esattamente il
difetto per cui questa colonna esiste.

⭐ **Oggi entrambi i bersagli sono `DOMINIO`**, ed è la ragione per cui il job
non si spacca in due: portano entrambi l'emittente (`contratti` con la colonna
diretta, `listini_versioni` attraverso il listino padre).

---

### Comportamento previsto

1. Una nuova riga (via INSERT seed in `80_data/sql/dbops/automazione_chiusura_scadenze.csv`) descrive una tabella che vuole partecipare alla chiusura per scadenza.
2. Il job pgAgent `chiusura_scadenze_daily` invoca `dbops.fn_apply_chiusura_scadenze()`, che itera sulle righe `attivo=true` e applica UPDATE dinamici alle tabelle target.
3. Per `tipo_stato='VARCHAR'`: UPDATE diretto con i codici come stringhe.
4. Per `tipo_stato='FK'`: prima lookup id chiuso/attivo da `fk_lookup_schema.fk_lookup_table` via `codice_interno`, poi UPDATE con id risolti.
5. Pre-check di esistenza schema/tabella/colonne (e per FK anche tabella lookup + codici): in caso di config invalida raise `E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA` (no exec parziale).

---

### Esempi

**1) Seed VARCHAR (listini_versioni):**

```csv
2,vendite,listini_versioni,stato,VARCHAR,valido_al,ATTIVA,CHIUSA,,,,,t,...
```

Risultato: `UPDATE vendite.listini_versioni SET stato='CHIUSA' WHERE stato='ATTIVA' AND valido_al < CURRENT_DATE`.

**2) Seed FK (contratti):**

```csv
3,vendite,contratti,stato_doc_contratto_id,FK,valido_al,ATTIVO,CESSATO,config,stati_doc_contratti,codice_interno,id,t,...
```

Risultato: lookup id `ATTIVO`/`CESSATO` su `config.stati_doc_contratti`, poi `UPDATE vendite.contratti SET stato_doc_contratto_id=<id_cessato> WHERE stato_doc_contratto_id=<id_attivo> AND valido_al < CURRENT_DATE`.

**3) Disattivare temporaneamente una riga (es. manutenzione):**

```sql
UPDATE dbops.automazione_chiusura_scadenze
   SET attivo = false
 WHERE schema_tabella = 'vendite'
   AND nome_tabella   = 'contratti';
```

Il job successivo non processera' i contratti finche' non viene riattivata.

---

### Note operative

* I codici stato sono espressi come **`codice_interno`** (per FK) o come valore varchar (per VARCHAR), **mai come id numerico**: stabilita' tra ambienti dev/CI/prod.
* Aggiungere una nuova tabella al pattern non richiede nuovo codice DB: basta una INSERT seed con i parametri corretti.
* Compatibilita' con guard tabella-specifici: l'UPDATE eseguito dalla funzione attraversa eventuali trigger guard transizione e li soddisfa per costruzione (precondizione temporale `valido_al < CURRENT_DATE` identica al WHERE).
* La tabella e' di **configurazione amministrativa**: le righe sono inserite via Liquibase seed, non da utenti finali.

---

{% include-markdown "signature-core.md" %}

---
