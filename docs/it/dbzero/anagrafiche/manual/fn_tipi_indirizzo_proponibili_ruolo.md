## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_tipi_indirizzo_proponibili_ruolo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.tipi_indirizzi](/dbzero/config/tabelle/tipi_indirizzi) — il catalogo dei tipi, una riga per tipo
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi) — da cui legge i tipi già presenti sulla chiave
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_check_tipo_indirizzo_ruolo_su_contesto](/dbzero/anagrafiche/funzioni/fn_check_tipo_indirizzo_ruolo_su_contesto) — la check che legge per ogni tipo
> * [anagrafiche.fn_crea_indirizzo_ruolo](/dbzero/anagrafiche/funzioni/fn_crea_indirizzo_ruolo) — la madre che accetta ciò che il picker propone
> * [anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo](/dbzero/anagrafiche/funzioni/fn_tipo_indirizzo_obbligatorio_per_ruolo) — da cui la colonna obbligatorio
> * [anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo](/dbzero/anagrafiche/funzioni/fn_tipi_indirizzo_proponibili_tipo_ruolo) — il gemello per il ruolo da creare
> * [anagrafiche.fn_tipi_indirizzo_proponibili_soggetto](/dbzero/anagrafiche/funzioni/fn_tipi_indirizzo_proponibili_soggetto) — il gemello sul soggetto
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — i due strati degli indirizzi e le loro regole

---

### 🎯 Scopo Principale

`anagrafiche.fn_tipi_indirizzo_proponibili_ruolo` dice quali tipi d'indirizzo si possono ancora aggiungere a un
ruolo salvato, sul ruolo stesso o su una sua istanza: una riga per tipo, ammessa oppure spenta col suo motivo.
Propone ciò che la madre del ruolo accetta, perché legge la stessa check.

---

### La chiave di destinazione

L'istanza non ha un valore di default: vuota vuol dire il ruolo, valorizzata quell'istanza. I tipi presenti si
leggono su quella chiave, come fa la check della madre: un tipo che il ruolo ha già resta proponibile su una sua
istanza.

Il contesto (tipo di ruolo, natura del soggetto del ruolo, tipi presenti) si legge una volta sola; per ogni
tipo del catalogo la check su contesto dà i tre motivi del ruolo, col giorno operativo. Un ruolo che non esiste
non dà nessuna riga. Gira coi permessi di chi la chiama.

Lo legge il form dell'aggiunta, e dà i tipi di destinazione della copia di un indirizzo verso quella chiave.

---

{% include-markdown "it/dbzero/anagrafiche/_tipo-indirizzo-ammesso.md" %}

---

### Test

* `db/pgtap/anagrafiche/test-tipi-indirizzo-proponibili-v1.sql` — legge la check della madre; un tipo scritto
  sul ruolo si spegne col codice che la madre solleva, e resta ammesso sull'istanza; il ruolo che non c'è.
* `db/pgtap/anagrafiche/test-fornitore-privato-indirizzi-v1.sql` — sul ruolo salvato di un privato la sede
  legale è spenta col codice della madre.

---

### Note di migrazione

* 2026-11-15 — nasce con la copia degli indirizzi.
* 2026-11-16 — la natura del soggetto del ruolo entra nei motivi e nell'obbligatorio, col fornitore privato.

---

{% include-markdown "signature-core.md" %}
