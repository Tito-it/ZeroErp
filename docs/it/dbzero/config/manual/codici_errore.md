## 📘 Documentazione Concettuale – Tabella `config.codici_errore`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [config.classi_errore](/dbzero/config/tabelle/classi_errore)
> • [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)
> • [dbops.codici_errore_senza_policy](/dbzero/dbops/tabelle/codici_errore_senza_policy)
> • [dbops.messaggi_errore_codici_legacy](/dbzero/dbops/tabelle/messaggi_errore_codici_legacy)
>
Approfondimento viste:
> • [config.vw_codici_errore_identita](/dbzero/config/views/vw_codici_errore_identita)
> • [dbops.vw_codici_errore_da_dichiarare](/dbzero/dbops/views/vw_codici_errore_da_dichiarare)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

L'**identità** di un codice errore: che cosa è (`classe`) e se è ancora in servizio
(`obsoleto_dal`). Una riga per codice, senza traduzioni — 726 al 2026-08-21.

La separazione dall'altra tabella è il punto: **qui c'è l'identità, in
`config.messaggi_errore` c'è la frase**, chiavata `(codice, lingua)`. Un codice esiste anche
prima di avere una traduzione, e sopravvive a un cambio di testo.

---

### Le colonne che contano

* **`codice`** — la chiave. Convenzione `E_{MODULO}_{TIPO}`, con la famiglia `W_` per i
  warning (`docs/it/dev/api.md`). ⛔ I `W_` restano `W_`: si loggano e non si sollevano —
  un `W_` sollevato diventerebbe un HTTP 500.
* **`classe`** — FK a `config.classi_errore`: la natura del rifiuto.
* **`obsoleto_dal`** — deprecazione, non cancellazione. Un codice ritirato resta, perché
  compare nei log storici.
* **`note`** — il *perché* del codice. Nel progetto sono note lunghe e argomentate: raccontano
  da quale difetto è nato, perché è distinto da un codice vicino, quale piano lo ha deciso.
* **`causa_fallimento`** *(dal 2026-10-16)* — quando questo errore ferma un lavoro
  automatico, di che natura è il guasto
  ([`dbops.cause_fallimento`](/dbzero/dbops/manual/cause_fallimento)): `AMBIENTE`,
  `PROGRAMMA` o `CONFIGURAZIONE`. ⭐ **Vuota di proposito** su quasi tutti i codici: vuol
  dire «decide il processo». Si valorizza solo su un codice che ha un destinatario suo,
  per esempio un errore che si sistema dalle impostazioni dell'applicazione. La legge
  [`maintenance.vw_job_run_da_guardare`](/dbzero/maintenance/manual/vw_job_run_da_guardare).
  ⚠️ Non è la `classe`: la classe descrive l'errore per chi ha fatto la richiesta, la
  causa dice chi deve rimediare a un lavoro notturno fermo.

⚠️ `chk_codici_errore_note_una_riga` impone che `note` stia **su una riga sola**: è un campo
di CSV, e un a-capo lo spezzerebbe. Le note lunghe si scrivono di seguito, senza newline.

---

### ⚠️ Il catalogo non sa chi lo usa

Questa tabella elenca i codici **dichiarati**. Non sa quali siano effettivamente sollevati dal
codice PL/pgSQL: quella è una misura diversa, e la fa
`dbops.vw_codici_errore_da_dichiarare` leggendo i corpi delle funzioni.

Le due letture non coincidono, e nessuna delle due è sbagliata:

* un codice **dichiarato ma mai sollevato** è documentazione di qualcosa che non succede;
* un codice **sollevato ma non dichiarato** è un errore che l'operatore vedrà con un
  segnaposto irrisolto invece che con la sua frase.

Il secondo caso è quello che i guardrail presidiano.

---

### Popolamento

Seed `80_data` dal CSV `codici_errore.csv`, loader mirror `runOnChange` `20260614-08`, che
carica **dopo** `classi_errore` (FK) e **prima** di `messaggi_errore`.

⭐ **Un codice nuovo è solo un append al CSV** — a questo e a `messaggi_errore.csv`. Mai un
nuovo loader `upsert`: quelli esistenti sono mirror vivi e ripescano il CSV a ogni migrate.

---

{% include-markdown "signature-core.md" %}
