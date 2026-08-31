## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_ordini_gen_numero`

> 👀 **Vedi anche**
>
> • [vendite.ordini](/dbzero/vendite/tabelle/ordini)
> • [vendite.registri_fatturazione](/dbzero/vendite/manual/registri_fatturazione)
> • [vendite.fn_assegna_numero_documento](/dbzero/vendite/manual/fn_assegna_numero_documento) (i sei passi)
> • [vendite.trgfn_ddt_gen_numero_emesso](/dbzero/vendite/manual/trgfn_ddt_gen_numero_emesso) (stesso schema, momento diverso)

---

### 🎯 Scopo Principale

(rev 2026-08-31, sera)

Assegna il **`numero` dell'ordine alla creazione**, prendendolo dal motore dei
registri. `BEFORE INSERT` su `vendite.ordini`.

⚠️ **Sostituisce `trgfn_ordini_gen_codice`**, che era generata dal framework di
`config.sistema_codici` e non esiste più. Chi cerca quel nome nel database non lo
trova: il rename è avvenuto il 31 agosto 2026 col trasloco sui registri.

---

### Il momento non cambia, ed è dichiarato

⭐ L'ordine **nasce numerato**: nessuno stato da guardare. ⛔ E la conseguenza si
accetta apertamente — un ordine creato e poi abbandonato **consuma un numero**, e
nella progressione resta un buco.

Per una fattura sarebbe un problema fiscale; per un ordine no, ed è il motivo per
cui i due documenti numerano in momenti diversi.

---

### Che cosa succede, in ordine

1. se il numero è già valorizzato, non fa niente. ⭐ Serve a due cose: rispettare un
   numero fornito dall'esterno, e rendere **innocua** la finestra di rilascio in cui
   questo trigger conviveva con quello generico;
2. traduce l'emittente da una convenzione all'altra — l'ordine porta l'id
   dell'emittente fiscale, il registro porta il soggetto-ruolo — e la traduzione è
   scritta esplicitamente, perché è 1:1 ma non è ovvia;
3. chiama
   [`vendite.fn_assegna_numero_documento`](/dbzero/vendite/manual/fn_assegna_numero_documento),
   che fa i sei passi;
4. scrive **insieme** `numero`, `anno`, `serie` e `registro_id`.

⚠️ Il punto 4 non è pignoleria: quelle quattro colonne sono la chiave del
documento. Scriverne una senza le altre lascia la riga a dichiarare un sezionale
diverso da quello su cui ha davvero contato.

---

### ⚠️ Da dove viene la forma del numero

Dal **registro**: prefisso, suffisso e numero di cifre. `config.sistema_codici` non
ha più una riga `ordine` dal 31 agosto 2026; i valori con cui un registro nasce
stanno in [`vendite.famiglie_documento`](/dbzero/vendite/manual/famiglie_documento).

⚠️ La sequenza `vendite.ordini_numero_seq` non è più il contatore: quello è
`vendite.registri_fatturazione_progressivi`, per registro e per anno.

---

{% include-markdown "signature-core.md" %}
