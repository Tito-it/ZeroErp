## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_risorse_umane_guard_ruolo`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> * [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
>
> **Approfondimento funzioni:**
>
> * [script.fn_guard_soggetto_ruolo](/dbzero/script/funzioni/fn_guard_soggetto_ruolo)
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---

### 🎯 Scopo Principale

(latest review 10-03-2026)
La trigger function **`anagrafiche.trgfn_risorse_umane_guard_ruolo()`**
garantisce che ogni riga di `anagrafiche.risorse_umane` sia collegata a un
`soggetto_ruolo_id` di tipo **RIS_UMANA** e che tale ruolo punti allo stesso
`soggetto_id` presente nel record della risorsa umana.

---

### 🔍 Regole applicate

* Trigger **BEFORE INSERT OR UPDATE** su `anagrafiche.risorse_umane`.
* Chiama `script.fn_guard_soggetto_ruolo(...)` con `p_cd_int_ruolo := 'RIS_UMANA'`.
* Aggiorna `NEW.soggetto_ruolo_id` con l'ID valido restituito.
* Recupera il `soggetto_id` reale dal ruolo.
* Se il `soggetto_id` del ruolo e quello della risorsa non coincidono:
  * blocca l'operazione con errore `E_RISORSA_UMANA_SOGGETTO_MISMATCH`.

---

### ✅ Ruolo nel processo

La funzione protegge la coerenza del modello anagrafico evitando disallineamenti
tra:

* il soggetto anagrafico della risorsa umana
* il ruolo associato alla stessa risorsa

In questo modo `anagrafiche.risorse_umane` resta sempre un'estensione coerente
del ruolo `RIS_UMANA`.

---

{% include-markdown "signature-core.md" %}
