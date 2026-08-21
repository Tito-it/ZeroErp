## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_vettori_normalize()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [anagrafiche.vettori](/dbzero/anagrafiche/tabelle/vettori)
> • [config.sistema_codici](/dbzero/config/tabelle/sistema_codici)
>
Approfondimento funzioni:
> • [anagrafiche.trgfn_vettori_guard_ruolo_vettore](/dbzero/anagrafiche/funzioni/trgfn_vettori_guard_ruolo_vettore)
> • [script.fn_generate_codice](/dbzero/script/funzioni/fn_generate_codice)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Oggi questa funzione non fa nulla.** Il corpo è `BEGIN RETURN NEW; END`, e il suo
`COMMENT` lo dichiara: «*Normalize: no-op; generazione codice demandata al sistema_codici*».

È il residuo di un `normalize` che in origine valorizzava il `codice` del vettore e che è
stato svuotato quando la generazione codici è passata a `config.sistema_codici`. Il trigger
è rimasto agganciato: costa una chiamata per riga e non produce effetti.

Questa pagina esiste per dire proprio questo — altrimenti il nome, allineato ai
`trgfn_*_normalize` che invece normalizzano davvero, lascia credere che qualcosa succeda.

---

### Aggancio

Trigger `trg_vettori_norm_ins_upd` — `BEFORE INSERT OR UPDATE` su `anagrafiche.vettori`.

---

### ⚠️ Il codice del vettore non lo genera nessuno

Il `COMMENT` rimanda al `sistema_codici`, ma il rinvio **non ha destinatario**:

* su `anagrafiche.vettori` **non esiste** un trigger `gen_codice` (a differenza di
  `soggetti`, `fornitori`, `billing_account`, `istanze_utilities`);
* in `config.sistema_codici` **non esiste** una riga per i vettori;
* la colonna `anagrafiche.vettori.codice` è però `NOT NULL`.

Conseguenza operativa: **il codice del vettore deve arrivare dal chiamante**. Un `INSERT`
che lo omette non viene salvato da nessun default — fallisce con violazione di vincolo
(SQLSTATE `23502`), senza nessun codice `E_*` che ne spieghi il motivo.

Una volta scritto, il codice è immutabile: ci pensa
`trg_vettori_a10_lock_columns_upd` (`CODICE_NON_MODIFICABILE`).

---

### Se un giorno serve rimuoverla

Il trigger è inerte, quindi toglierlo non cambia comportamento. Prima di farlo però va
verificato che nessun pgTAP asserisca la sua presenza (`grep -rn trg_vettori_norm db/pgtap/`):
un test che conta i trigger della tabella diventerebbe rosso senza che nulla si sia rotto.

---

### Codici errore

Nessuno: la funzione non solleva e non registra niente.

---

{% include-markdown "signature-core.md" %}
