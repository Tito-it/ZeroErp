## 📘 Documentazione Concettuale – Funzione `script.fn_snapshot_indirizzo_soggetto`

> 👀 **Vedi anche**
>
> **Tabelle:**
>
> • [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi)
> • [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
>
> **Funzioni:**
>
> • [script.fn_resolve_indirizzo_documento](/dbzero/script/funzioni/fn_resolve_indirizzo_documento) — la catena che la usa come secondo layer
> • [script.fn_snapshot_indirizzo](/dbzero/script/funzioni/fn_snapshot_indirizzo) — la **gemella** sul layer RUOLO

---
### 🎯 Scopo Principale
(latest review 02-08-2026)

`script.fn_snapshot_indirizzo_soggetto` produce lo **snapshot canonico** di un
indirizzo preso dal **layer SOGGETTO**, cioè dagli indirizzi che appartengono al
soggetto e non a uno specifico ruolo.

È la **gemella** di `script.fn_snapshot_indirizzo`, che fa lo stesso sul layer
RUOLO. Stessa forma in uscita, sorgente diversa.

---

### 🔴 La chiave è `(soggetto_id, tipo)`, non un id

Sembra un dettaglio implementativo ed è invece il punto della funzione.

La vista del soggetto espone un `indirizzo_id` che è la **PK di un'altra
tabella**. Passarlo alla gemella restituirebbe, **in silenzio**, l'indirizzo di
ruolo che per caso ha lo stesso numero: nessun errore, nessuna riga mancante,
solo l'indirizzo sbagliato stampato su un documento fiscale.

Da qui la firma per chiave naturale.

---

### Assenza = zero righe, non errore

Un soggetto può legittimamente non avere un indirizzo di un certo tipo. La
funzione **non solleva**: restituisce zero righe, e sta al chiamante decidere se
quell'assenza sia un problema.

È la scelta che rende la catena a due layer possibile — se sollevasse, il primo
layer vuoto impedirebbe di provare il secondo.

---

### ⚠️ I valori sono normalizzati, e c'è un motivo pagato

Tutti i campi testuali passano da `NULLIF(btrim(...), '')`.

Non è cosmesi. `province.sigla` è `character(10)` e `stati.codice_iso2` è a
larghezza fissa: senza `btrim`, uno snapshot conteneva `"prov": "AV        "` —
otto spazi congelati dentro un `jsonb` di un documento fiscale.

Il difetto era **noto e rinviato** «per parità di shape» con la gemella. Il rinvio
è tornato indietro dopo che un documento l'aveva già congelato: quando si sceglie
la simmetria contro la correttezza, la correttezza presenta il conto più tardi e
con gli interessi.

---
{% include-markdown "signature-core.md" %}
