## 📘 Documentazione Concettuale – Vista `dbops.vw_processi_che_bypassano`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il registro dei processi automatici, di cui questa vista guarda i ruoli
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo in cui la vista è un presidio
>
> Approfondimento viste:
>
> * [dbops.vw_processi_dominio_senza_difesa](/dbzero/dbops/views/vw_processi_dominio_senza_difesa) — l'altro lato: le tabelle senza policy o guard
>
> Guide:
>
> * [I lavori automatici: che natura hanno e per conto di chi girano](/guide/processi-automatici-classe-e-identita) — perché un processo non deve saltare la row level security
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — come si legge un presidio con un debito dichiarato

---

### 🎯 Scopo Principale

Presidio: i ruoli applicativi che saltano la row level security, cioè i ruoli che possono
collegarsi, non sono superuser e hanno `BYPASSRLS`. L'invariante è «nessuna riga non dichiarata».

---

### ⚠️ Non dice «nessuno salta la row level security»

Lo scheduler bypassa perché è superuser, il proprietario delle tabelle per proprietà, e devono
farlo: eseguono DDL. La vista li esclude per costruzione e guarda solo ciò che resta: un ruolo che
si collega come un'applicazione e vede tutto senza che nessuna policy lo filtri.

⇒ Un ruolo così è una porta. Toglierla è un lavoro che vive fuori dal database (il ruolo va
ritirato dal provisioning, il backend deve smettere di collegarsi con quello): finché non è fatto,
la vista la tiene **contata**, invece di lasciarla alla memoria.

---

### ⭐ Dichiarata o non dichiarata

Ogni riga ha uno `stato`:

| `stato` | Che cosa vuol dire |
| --- | --- |
| `DEBITO_DICHIARATO` | il ruolo è una porta registrata come porta: il suo nome è scritto nella definizione della vista |
| `NON_DICHIARATO` | qualunque altro ruolo con quelle caratteristiche: un allarme |

⭐ Per questo il presidio non conta le righe: il ritiro di una porta dichiarata e la comparsa di un
ruolo nuovo non dichiarato lascerebbero il numero uguale, e il presidio diventerebbe muto.

⚠️ L'elenco delle porte dichiarate è scritto **nella vista**, e oggi nomina ancora un ruolo ritirato
(`zeroerp_batch_fatturazione`). Se un ruolo con quel nome tornasse, la vista lo presenterebbe come
debito e non come allarme. La `nota` è un testo fisso, uguale su ogni riga, anche su quelle non
dichiarate: non descrive la riga.

---

### ⚠️ Perché si legge il catalogo dei ruoli

`information_schema.role_table_grants` mostra solo i privilegi che la sessione corrente può vedere:
una vista costruita lì sarebbe vuota per ragioni che non hanno niente a che fare con la sicurezza.
La vista legge il catalogo dei ruoli, che è il dato vero.

---

### Chi la guarda

Nel catalogo dei presidi è un presidio a stato, guardato ogni settimana; chi agisce è chi gestisce
il server. La vista gira coi privilegi del proprietario.

---

### Test

* `db/pgtap/dbops/test-processi-registro.sql` — nessuna riga `NON_DICHIARATO`.

---

### Note di migrazione

* 2026-09-04 — nasce col registro dei processi automatici (`brief-db-processi-automatici-identita-e-perimetro`):
  l'unico ruolo applicativo con `BYPASSRLS` era quello della fatturazione batch, dichiarato come
  debito.
* 2026-10-15 — il ruolo della fatturazione batch è ritirato; il suo nome resta nell'elenco della
  vista.

---

{% include-markdown "signature-core.md" %}
