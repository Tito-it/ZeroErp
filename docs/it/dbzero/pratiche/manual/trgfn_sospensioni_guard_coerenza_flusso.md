## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_sospensioni_guard_coerenza_flusso`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.sospensioni](/dbzero/pratiche/tabelle/sospensioni) — la tabella che il guard presidia
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — il flusso sospeso
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_pratiche_sorgenti_guard_coerenza_flusso](/dbzero/pratiche/funzioni/trgfn_pratiche_sorgenti_guard_coerenza_flusso) — la stessa regola sui collegamenti fra documento e pratica
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — registra e solleva l'errore

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_sospensioni_guard_coerenza_flusso` garantisce che il flusso di una
sospensione appartenga alla stessa pratica della sospensione.

---

### Le regole

* Una sospensione senza flusso sospende la pratica intera: nessun controllo.
* Una sospensione con flusso è rifiutata se il flusso appartiene a un'altra pratica.
* ⚠️ È rifiutata con lo stesso errore anche se il flusso non si trova: a differenza del guard gemello
  sui collegamenti di pratica, qui il caso non è lasciato alla chiave esterna.

Il guard scatta all'inserimento e quando cambia `flusso_id`; un cambio della sola `pratica_id` non lo
fa scattare.

---

### Codici errore

* `E_SOSPENSIONI_FLUSSO_NON_COERENTE` — il flusso non appartiene alla pratica della sospensione. La frase
  nomina il flusso e la pratica.

---

### Note di migrazione

* 2026-08-18 — la chiamata d'errore passava una frase già composta come valore unico a un messaggio
  con due segnaposto, e la composizione falliva: ora passa il flusso e la pratica.

---

{% include-markdown "signature-core.md" %}
