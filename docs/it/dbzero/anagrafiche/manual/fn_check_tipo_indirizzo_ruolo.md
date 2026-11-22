## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_check_tipo_indirizzo_ruolo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi) — da cui legge i tipi già presenti sulla chiave
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo, da cui legge il tipo di ruolo e il soggetto
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_check_tipo_indirizzo_ruolo_su_contesto](/dbzero/anagrafiche/funzioni/fn_check_tipo_indirizzo_ruolo_su_contesto) — la metà pura, a cui passa il contesto
> * [anagrafiche.fn_crea_indirizzo_ruolo](/dbzero/anagrafiche/funzioni/fn_crea_indirizzo_ruolo) — la madre che la chiama e solleva il primo motivo
> * [anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo) — il guard della tabella, presidio delle altre strade
> * [anagrafiche.fn_check_tipo_indirizzo_soggetto](/dbzero/anagrafiche/funzioni/fn_check_tipo_indirizzo_soggetto) — la gemella sul soggetto
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — i due strati degli indirizzi e le loro regole

---

### 🎯 Scopo Principale

`anagrafiche.fn_check_tipo_indirizzo_ruolo` dice perché un tipo d'indirizzo non si può scrivere sul ruolo
salvato, sul ruolo stesso o su una sua istanza: restituisce l'elenco ordinato dei motivi, vuoto se il tipo è
ammesso. La madre singolare la chiama prima di scrivere e solleva il primo.

---

### La chiave di destinazione

L'istanza dice **dove** va l'indirizzo: vuota, sul ruolo; valorizzata, su quell'istanza. I tipi presenti si
leggono su quella chiave, la stessa dei due indici unici: un tipo che il ruolo ha già non occupa una sua
istanza, e un tipo di un'istanza non occupa il ruolo né un'altra istanza. Che l'istanza sia del soggetto del
ruolo non lo dice questa check: lo dice il guard dell'istanza, alla scrittura.

---

### Legge il contesto, non giudica

Dal ruolo salvato legge il tipo di ruolo e la natura del soggetto, dalla chiave i tipi presenti, e passa tutto,
col giorno operativo, alla check su contesto: la regola sta là, e qui non c'è nessun predicato. Il giorno è lo
stesso del guard della tabella. Gira coi permessi di chi la chiama; le tabelle che legge non hanno un filtro di
visibilità.

---

{% include-markdown "it/dbzero/anagrafiche/_tipo-indirizzo-ammesso.md" %}

---

### Codici errore

* `E_SCRIPT_CHIAMATA_NON_VALIDA` — il ruolo non è passato; il tipo non è passato (dalla check su contesto).
* `E_SOGGETTO_RUOLO_NON_TROVATO` — il ruolo non esiste.

I codici dei motivi la funzione non li solleva: li restituisce.

---

### Test

* `db/pgtap/anagrafiche/test-check-tipo-indirizzo-v1.sql` — la madre chiama la check e non contiene il predicato;
  il tipo nuovo, il tipo già presente, lo stesso tipo su un'istanza senza motivi, la riga scaduta, il ruolo che
  non c'è.
* `db/pgtap/anagrafiche/test-fornitore-privato-indirizzi-v1.sql` — la sede legale sul ruolo di un privato,
  rifiutata dalla madre.
* `db/pgtap/anagrafiche/test-copia-indirizzo-destinazione-v1.sql` — il tipo già presente giudicato sulla chiave
  di destinazione della copia.

---

### Note di migrazione

* 2026-11-15 — nasce con la copia degli indirizzi, insieme alla sua metà pura.
* 2026-11-16 — passa alla metà pura anche la natura del soggetto del ruolo.

---

{% include-markdown "signature-core.md" %}
