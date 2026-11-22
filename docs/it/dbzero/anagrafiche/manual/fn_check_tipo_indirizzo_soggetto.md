## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_check_tipo_indirizzo_soggetto`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti) — da cui legge i tipi già presenti
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_check_tipo_indirizzo_soggetto_su_contesto](/dbzero/anagrafiche/funzioni/fn_check_tipo_indirizzo_soggetto_su_contesto) — la metà pura, a cui passa il contesto
> * [anagrafiche.fn_crea_indirizzo_soggetto](/dbzero/anagrafiche/funzioni/fn_crea_indirizzo_soggetto) — la madre che la chiama e solleva il primo motivo
> * [anagrafiche.trgfn_indirizzi_soggetti_guard_tipo_indirizzo](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_soggetti_guard_tipo_indirizzo) — il guard della tabella, presidio delle altre strade
> * [anagrafiche.fn_check_tipo_indirizzo_ruolo](/dbzero/anagrafiche/funzioni/fn_check_tipo_indirizzo_ruolo) — la gemella sul ruolo
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — i due strati degli indirizzi e le loro regole

---

### 🎯 Scopo Principale

`anagrafiche.fn_check_tipo_indirizzo_soggetto` dice perché un tipo d'indirizzo non si può scrivere sul soggetto
salvato: restituisce l'elenco ordinato dei motivi, vuoto se il tipo è ammesso. La madre singolare la chiama
prima di scrivere e solleva il primo.

---

### Legge il contesto, non giudica

Dal soggetto salvato legge la natura e i tipi che ha già, e li passa, col giorno operativo, alla check su
contesto: la regola sta là, e qui non c'è nessun predicato. Il giorno è lo stesso del guard della tabella, così
la check e il guard non possono dire due cose diverse sullo stesso salvataggio.

Gira coi permessi di chi la chiama. Le tabelle che legge non hanno un filtro di visibilità: i tipi presenti sono
tutti quelli del soggetto.

---

{% include-markdown "it/dbzero/anagrafiche/_tipo-indirizzo-ammesso.md" %}

---

### Codici errore

* `E_SCRIPT_CHIAMATA_NON_VALIDA` — il soggetto non è passato; il tipo non è passato (dalla check su contesto).
* `E_SOGGETTO_NOT_FOUND` — il soggetto non esiste.

I codici dei motivi la funzione non li solleva: li restituisce.

---

### Test

* `db/pgtap/anagrafiche/test-check-tipo-indirizzo-v1.sql` — la madre chiama la check e non contiene il
  predicato; il tipo nuovo, il tipo già presente col campo da accendere, la riga scaduta, il soggetto che non
  c'è.

---

### Note di migrazione

* 2026-11-15 — nasce con la copia degli indirizzi, insieme alla sua metà pura.

---

{% include-markdown "signature-core.md" %}
