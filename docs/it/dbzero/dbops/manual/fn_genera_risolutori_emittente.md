## 📘 Documentazione Concettuale – Funzione `dbops.fn_genera_risolutori_emittente`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.emittente_modi](/dbzero/dbops/tabelle/emittente_modi) — il registro dei modi
>
> Approfondimento funzioni:
>
> * [dbops.fn_risolutore_emittente_corpo](/dbzero/dbops/funzioni/fn_risolutore_emittente_corpo) — il testo dei due corpi
> * [script.fn_resolve_emittente_fiscale_id](/dbzero/script/funzioni/fn_resolve_emittente_fiscale_id) — il risolutore fiscale che riscrive
> * [script.fn_resolve_emittente_sr_id](/dbzero/script/funzioni/fn_resolve_emittente_sr_id) — il gemello che riscrive

---

### 🎯 Scopo Principale

Riporta i due risolutori dell'emittente al registro `dbops.emittente_modi`. Per ognuno confronta il
corpo e la descrizione vivi con quelli che il registro produce, e lo riscrive solo se sono diversi.
Restituisce quante funzioni ha riscritto: quando niente è cambiato, zero, e nessuna modifica allo
schema.

---

### Quando gira

A ogni migrazione, dopo il caricamento del registro, da un passo di convergenza della fase finale.
Così un modo aggiunto al CSV arriva nei risolutori nella stessa migrazione, e un risolutore toccato a
mano torna quello del registro alla migrazione successiva.

Riscrive le funzioni con la loro firma, `SECURITY DEFINER` e il `search_path` bloccato: chi le chiama
non vede nessuna differenza, salvo i modi nuovi. Funziona solo dal proprietario delle due funzioni:
dall'applicazione si ferma sull'errore di PostgreSQL.

---

### Test

`dbops/test-emittente-modi-registro-v1`, test 6: sul database migrato non riscrive niente.

---

{% include-markdown "signature-core.md" %}
