## 📘 Documentazione Concettuale – Funzione `script.fn_pgtap_set_contesto_operatore()`

> 👀 **Vedi anche**
>
> • [script.fn_pgtap_set_contesto_operatore](/dbzero/script/funzioni/fn_pgtap_set_contesto_operatore)
> • [dbops.fn_pgtap_crea_soggetto_pg](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_pg)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Dà alla sessione di test **lo stesso contesto che il backend imposta** per un operatore:
ruolo applicativo, utente corrente, perimetro emittente.

🔴 **È la riga più importante del preambolo pgTAP**, e la sua assenza non produce un errore:
produce un test **verde per sottrazione**. Senza veste dichiarata le policy RLS sono
fail-closed, le `SELECT` della fixture leggono zero righe, e le asserzioni finiscono nei rami
`skip` — che non verificano niente.

⚠️ Un test che ha bisogno di una veste **diversa** (per esempio `CLIENTE_PORTALE`) chiama
comunque prima questa — la fixture deve *vedere* per costruire — e cambia veste solo dopo,
impostando `app.ruolo_applicativo` e `app.current_identita_id`.

⚠️ E svuotare `app.current_user_id` **non** è un modo per testare il fail-closed: il cancello
vero è `app.ruolo_applicativo`.

⭐ **Su un database vuoto costruisce, non cerca** (rev `20260920-01`). Senza argomento la
funzione sceglie un operatore con un emittente in whitelist; su un database ricostruito dai
changelog (la CI, un'installazione nuova) non ce n'è nessuno, e fino a quella revisione il
contesto restava **vuoto** — il file moriva venti righe più in là su «Nessun emittente
fiscale attivo». Ora, se non trova nessuno, costruisce azienda + operatore con
[dbops.fn_pgtap_crea_emittente_operatore](/dbzero/dbops/funzioni/fn_pgtap_crea_emittente_operatore)
e apre il contesto su quello. Dove un operatore c'è, o con l'argomento, niente cambia.

⚠️ L'operatore costruito è un utente **tecnico**: per RLS e guard è un operatore a tutti gli
effetti, ma un test il cui soggetto è l'operatore *umano* (flag tecnica, profili) costruisce il
suo caso e lo passa come argomento. E un test che ha bisogno degli **id** del mondo (l'emittente,
il soggetto ruolo, due aziende) chiama il builder da sé, prima di questa riga, come nella guida.

⛔ **Vincoli differiti: quando costruisce, esce IMMEDIATE** (dichiarato in `20260921-18`). Il
builder richiude la finestra `DEFERRED` della propria saga con `SET CONSTRAINTS ALL IMMEDIATE`,
che vale per tutta la transazione: PostgreSQL non permette di leggere il modo corrente né di
ripristinarlo, e chiuderli in ogni ramo «per omogeneità» sarebbe peggio — un setter di contesto
chiuderebbe i vincoli pendenti *nei panni del nuovo attore*, cioè sotto un'altra RLS. Con
argomento, o dove un operatore esiste, la funzione **non tocca i vincoli**. Il contratto è quindi
asimmetrico per costruzione, e la conseguenza per i file è una: **dopo questa riga non si conta
sulla finestra differita di default**. Un file che sposta il proprio `SET CONSTRAINTS ALL
IMMEDIATE` «dove l'unità di lavoro è completa» la riapre subito dopo il contesto con
`SET CONSTRAINTS ALL DEFERRED`. Senza, è verde su dev e rosso sul database da zero — e solo
quando è il **primo** file della corsa, perché il secondo (`create-gestore-conto-bancario`, contesto
in autocommit) committa un operatore e nessuno dopo percorre più il ramo che costruisce:
`anagrafiche/create-cliente`, CI del 2026-09-21, «due volte in due giorni» senza riprodursi da solo.
Guida: [pgtap-come-si-scrive-un-test](/guide/pgtap-come-si-scrive-un-test), §«Il mondo
si costruisce».

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
