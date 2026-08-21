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

### Il rinvio al `sistema_codici` oggi ha un destinatario — dal 2026-08-21

Il `COMMENT` rimanda alla generazione centralizzata dei codici, e da oggi quel rinvio è vero:
in `config.sistema_codici` esiste la riga `codice_interno = 'vettori'`
(prefisso `VET`, separatore `-`, 7 cifre), che punta ad `anagrafiche.vettori.codice`.

Da quella riga l'automazione generale — `script.trgfn_config_sistema_codici_sync_gen_codice`,
il trigger di sync di `config.sistema_codici` — ha creato da sé tre oggetti:

1. la sequenza `anagrafiche.vettori_codice_seq`;
2. la funzione `anagrafiche.trgfn_vettori_gen_codice()`;
3. il trigger `trg_vettori_a10_gen_codice_ins_upd`.

Un `INSERT` che omette il codice ora ne riceve uno nella forma `VET-0000001`.

⚠️ **Fino al 2026-08-21 il rinvio non aveva destinatario**, ed è la ragione per cui questa
pagina lo racconta. Non esisteva né la riga in `config.sistema_codici` né alcun trigger
`gen_codice` sulla tabella, mentre `anagrafiche.vettori.codice` era — ed è — `NOT NULL` e
`UNIQUE` (`uq_vettori_codice`). Il codice doveva quindi arrivare dal chiamante, e un `INSERT`
che lo ometteva moriva su una violazione di vincolo (SQLSTATE `23502`), senza nessun codice
`E_*` a spiegarne il motivo. Il `COMMENT` di questo no-op indicava una strada che nessuno
aveva aperto.

Presidio: `db/pgtap/anagrafiche/test-vettori-gen-codice.sql`.

Una volta scritto, il codice resta immutabile: ci pensa
`trg_vettori_a10_lock_columns_upd` (`CODICE_NON_MODIFICABILE`), configurato in
`dbops.automation_lock_columns` fin da gennaio — fino a oggi presidiava una colonna che
nessuno generava.

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
