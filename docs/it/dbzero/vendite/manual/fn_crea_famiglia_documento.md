## 📘 Documentazione Concettuale – Funzione `vendite.fn_crea_famiglia_documento`

> 👀 **Vedi anche**
>
> **Approfondimenti tabelle:**
>
> • [vendite.famiglie_documento](/dbzero/vendite/manual/famiglie_documento)
>
> **Chiama:**
>
> • [vendite.fn_provision_registri_famiglia](/dbzero/vendite/manual/fn_provision_registri_famiglia)
>
> **Chi la presidia mentre lavora:**
>
> • [vendite.trgfn_famiglie_documento_guard_riferimenti](/dbzero/vendite/manual/trgfn_famiglie_documento_guard_riferimenti)

---

### 🎯 Scopo Principale

*(rev 2026-09-01 — funzione nata il 2026-09-01)*

**Crea una famiglia di documento E le dà i suoi registri, come una cosa sola.**
Ritorna `(famiglia_id, codice_interno, registri_creati)`.

È la porta che il backend usa per il verbo «crea» del CRUD delle famiglie: ⛔
**non un `INSERT` diretto**.

---

### ⛔ Perché è una funzione «madre»

Sono **due scritture**: la riga di catalogo e i registri.

Fatte in sequenza da fuori, se la seconda fallisce resta una **famiglia senza
registri** — cioè una riga che promette un documento che non si numererà mai. E
non fallisce niente: nessun vincolo dice che quella riga è monca.

⭐ Una sola `SELECT` su connessione in autocommit è **atomica per costruzione**:
qualsiasi eccezione annulla l'intero effetto, e non serve scrivere nessun
`BEGIN`. È il criterio delle [linee guida SQL §5b](/linee-guida-sql).

⚠️ Ed è la proprietà che il pgTAP verifica direttamente: con un riferimento
inesistente la creazione viene rifiutata **e non lascia dietro la famiglia**.

---

### ⭐ Cosa NON fa, ed è deliberato

* **non valida i riferimenti** — c'è il guard `a10_guard_riferimenti`, che
  controlla che la tabella e le colonne nominate esistano davvero, e che una
  serie dichiarata **distingua** il numero;
* **non scrive audit né `tx_id`** — ci sono i trigger;
* **non decide se la famiglia sia fiscale** — quella è una proprietà del
  modello, non di chi crea la riga.

⇒ Fa le due scritture e le tiene insieme. Rifare qui quei controlli sarebbe il
secondo elenco che, prima o poi, diverge dal primo.

---

### ⛔ E non esiste una madre per «modifica» né per «attiva/disattiva»

Sono scritture **singole**: il backend le fa come già fa sui registri — un
aggiornamento diretto, e la traduzione dei vincoli che il database solleva.

⚠️ Una madre dove non c'è niente da tenere insieme è solo un livello in più da
attraversare per capire cosa succede.

---

### ⚠️ I sei campi obbligatori si controllano sul VALORE, non sul NULL

`codice_interno`, `descrizione`, `schema_tabella`, `nome_tabella`,
`colonna_numero`, `colonna_billing_account`.

⛔ Il `NOT NULL` della colonna **non basta**: una stringa vuota lo attraversa, e
un `codice_interno` vuoto sarebbe il bersaglio di una chiave esterna — cioè un
riferimento che non si riesce più a nominare.

⭐ Il campo sbagliato viaggia nel `context ->> 'campo'`, che è il canale con cui
il frontend accende l'input giusto. Il messaggio a catalogo resta generico di
proposito: la frase utile la compone la maschera, che sa come si chiama quel
campo **a video**.

⚠️ La stringa vuota su `colonna_serie` e su `prefisso_default` diventa **NULL**:
il vuoto è la dichiarazione che quella famiglia una serie non ce l'ha, e un `''`
salvato al posto di `NULL` la renderebbe indistinguibile da una serie che si
chiama così.

---

### 📤 Perché ritorna anche il conteggio

`registri_creati` non è una curiosità: **zero su una famiglia attiva significa
che non c'è nessun emittente**, e quel documento non nascerà comunque. Il
backend lo mostra, non lo ignora.

⚠️ Su una famiglia creata **spenta** il conteggio è zero per costruzione, e non è
un errore.

---

### ⚠️ Note operative

* **`SECURITY INVOKER`**: scrive su una tabella senza RLS su cui l'applicazione
  ha già il permesso di inserire. Il provisioning che chiama è `DEFINER` per
  conto suo, e la ragione sta nella sua pagina.
* **Il codice errore dei campi obbligatori** è `E_VENDITE_VALIDATION`
  (`DATO_ERRATO`), senza segnaposti: ⚠️ va invocato con il variadico **vuoto ma
  esplicito**, o PostgreSQL non risolve la firma e risponde «funzione
  inesistente» — un errore tecnico al posto di quello di dominio.

---

*Piano: `brief-be-fe-crud-registri-di-numerazione`, sezione 11.7.*
