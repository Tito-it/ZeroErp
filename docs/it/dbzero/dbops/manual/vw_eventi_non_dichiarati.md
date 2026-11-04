## 📘 Documentazione Concettuale – Vista `dbops.vw_eventi_non_dichiarati`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.event_log](/dbzero/vendite/tabelle/event_log) — il diario degli eventi che la vista legge
> * [config.eventi_dominio](/dbzero/config/tabelle/eventi_dominio) — il catalogo dei codici evento
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — la riga di catalogo del presidio
>
> Approfondimento viste:
>
> * [dbops.vw_bersagli_non_dichiarati](/dbzero/dbops/views/vw_bersagli_non_dichiarati) — il cancello che legge il sorgente, per un vocabolario che scrive il database
>
> Approfondimento funzioni:
>
> * [dbops.fn_conta_presidio](/dbzero/dbops/funzioni/fn_conta_presidio) — il conteggio del digest

---

### 🎯 Scopo Principale

I codici evento finiti nel diario `vendite.event_log` e assenti dal catalogo `config.eventi_dominio`:
la deriva già avvenuta. È una spia da guardare, non un semaforo che ferma.

---

### ⚠️ Non è la gemella dei presidi sui codici errore

I codici errore li solleva il database, e si cercano nel testo delle funzioni. I codici evento li
scrive il **backend**: una vista sul testo delle funzioni tornerebbe vuota per sempre, cioè direbbe
sempre «tutto a posto» guardando nel posto sbagliato. Il cancello vero sta nel backend, dove i codici
sono scritti, e fa fallire la build su un codice non a catalogo.

⭐ Questa vista fa un lavoro complementare: vede ciò che nessun controllo sul sorgente vede, un codice
costruito a runtime o scritto da qualcosa che non è il backend. Per lo stesso motivo è legata ai dati:
su un ambiente senza traffico è cieca.

⛔ **Il rubinetto non si chiude con una FK sul codice evento.** Una scrittura rifiutata perché il
codice non è ancora a catalogo sarebbe il diario che smette di scrivere per un problema di
configurazione: il diario rifiuta solo quando non sa dire di chi è la riga.

---

### Come si legge

Una riga per codice evento sconosciuto: quante righe del diario lo portano, la prima e l'ultima
volta, e quanti tipi di entità diversi tocca. Si spegne aggiungendo il codice al catalogo degli
eventi.

---

### ⚠️ Legge con gli occhi di chi interroga

La vista è `security_invoker`, e il diario degli eventi è in row level security: da un percorso senza
le variabili di sessione tornerebbe zero **per cecità**. Per questo nel catalogo dei presidi il suo
perimetro è `DEFINER`: il digest la conta come proprietario e riporta il numero, non le righe. È una
`LAVORAZIONE` a cadenza settimanale.

---

### Test

* `db/pgtap/dbops/test-catalogo-presidi-v1.sql` — il proprietario del diario è quello della funzione
  che conta, cioè il presupposto del perimetro `DEFINER`.

Il cancello sui codici evento è un test del backend,
`backend/apps/core/tests/test_event_codes_declared_guardrail.py`, sul sorgente Python.

---

### Note di migrazione

* 2026-08-22 — nasce con la consegna BE-9 di `brief-db-event-log-scope-e-riga-parlante` §5, come spia accanto al
  cancello del backend.

---

{% include-markdown "signature-core.md" %}
