## 📘 Documentazione Concettuale – Funzione `script.fn_get_note`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.note_stili](/dbzero/config/tabelle/note_stili) — il vocabolario degli stili
> * [config.lingue](/dbzero/config/tabelle/lingue) — il vocabolario delle lingue
> * [vendite.note](/dbzero/vendite/tabelle/note) — il meccanismo delle note, documentato per intero
>
> Approfondimento funzioni:
>
> * [vendite.fn_get_vendite_note](/dbzero/vendite/funzioni/fn_get_vendite_note) — l'involucro di vendite
> * [acquisti.fn_get_acquisti_note](/dbzero/acquisti/funzioni/fn_get_acquisti_note) — l'involucro di acquisti
> * [magazzino.fn_get_magazzino_note](/dbzero/magazzino/funzioni/fn_get_magazzino_note) — l'involucro di magazzino

---

### 🎯 Scopo Principale

Il lettore comune delle note: estrae le note di un documento da una tabella di note che gli si
passa per nome, e le restituisce tutte nella stessa forma, con stile e lingua risolti dai loro
vocabolari.

Serve le tabelle di note che hanno la stessa forma: `vendite.note`, `acquisti.note` e
`magazzino.note`. Ogni dominio ha un involucro che la chiama sulla propria tabella, così il
chiamante non deve conoscere il nome della tabella.

---

### Che cosa restituisce, e in che ordine

Per un documento (il tipo e l'id del bersaglio) restituisce le sue note, e si può restringere a
una riga sola. Tre interruttori decidono che cosa raccogliere: le note di testata, quelle di
riga, e se tenere solo quelle visibili.

Lo stile e la lingua escono come **codice** del vocabolario, non come riferimento: chi stampa
riceve `GRASSETTO` o `it`, non un id. Una nota senza lingua esce senza lingua.

L'ordine è quello di stampa: prima le note di testata, poi quelle di riga; dentro ciascun
gruppo, per posizione, sequenza e infine ordine di inserimento.

---

### ⚠️ Una sola forma per tutte le tabelle

La funzione dichiara un risultato unico, e le tabelle di note lo devono rispettare: tipo,
ancoraggio e posizione escono come testo anche se nelle tabelle sono stringhe di lunghezza
fissata. È il lettore a convertirli: se mancasse la conversione, ogni chiamata fallirebbe per un
tipo che non corrisponde, su tutte le famiglie insieme.

`catalogo.note` non è servita da questo lettore: il suo bersaglio si identifica con un uuid e non
con un id numerico.

---

### ⭐ Perché il nome della tabella si passa come riferimento

La tabella si passa come riferimento a un oggetto del database, non come testo libero: il nome si
risolve prima di entrare nella lettura, e una tabella che non esiste fa fallire la chiamata
invece di costruire una lettura su un nome qualunque.

---

### Note di migrazione

* 2026-10-10 — la lingua esce com'è, senza il riempimento a cinque caratteri che le aggiungeva
  spazi in coda (`brief-db-character-n-spazi-di-riempimento`).
* 2026-10-25 — il tipo del bersaglio è il codice della grammatica dei tipi (`ORDINE_VENDITA`, non
  più `ORDINE`), `brief-db-grammatica-unica-documenti`, lotto 3.
* 2026-11-01 — il lettore converte in testo tipo, ancoraggio e posizione: senza la conversione
  ogni chiamata falliva (verificato quel giorno sugli involucri di vendite e acquisti). Dallo
  stesso giorno serve anche `magazzino.note`, che ha preso la forma delle altre note.

---

{% include-markdown "signature-core.md" %}
