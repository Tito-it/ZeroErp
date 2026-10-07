## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_sync_auth_user_expired()`

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
>
**Approfondimento tabelle:**
>
[anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali)
> [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
>
**Approfondimento funzioni:**
>
[anagrafiche.fn_sync_auth_user_is_active](/dbzero/anagrafiche/funzioni/fn_sync_auth_user_is_active)

---
### 🎯 Scopo Principale
(latest review 18-04-2026)

La funzione **`anagrafiche.fn_sync_auth_user_expired()`** esegue una
sincronizzazione batch degli utenti Django collegati a bridge auth con
finestra di validità scaduta.

Copre il caso in cui un'identità (o una risorsa umana) diventi non valida
per semplice decorrenza della data, senza che avvenga un `UPDATE` esplicito
che triggeri i trigger reattivi.

---

### Estensione §4.5 multi-face-auth

⭐⭐ **Dal 07-10-2026, seconda revisione** (`20_code/20261007-21`, decisione di Tid):
il batch riallinea `is_active` **nei due versi**. Spegne le credenziali che hanno vesti
ma nessuna più utilizzabile, e **accende** quelle che ne hanno una diventata valida
oggi. Prima solo spegneva: una credenziale con l'unica veste a `valido_dal` futuro
nasceva spenta e restava spenta anche quel giorno, perché una data che arriva non
scrive niente. I candidati sono le credenziali con vesti il cui `is_active` non dice
più «esiste una veste utilizzabile oggi»; decide sempre
`fn_sync_auth_user_is_active`. Il nome resta (pgAgent, command Django e repository BE
lo chiamano), il ritorno conta le credenziali **riallineate**, spente o accese.

⭐ **Dal 07-10-2026, prima revisione** (`20_code/20261007-09`, brief `brief-db-veste-utilizzabile`)
i candidati sono le credenziali ancora `is_active = true` che **hanno vesti ma
nessuna utilizzabile oggi** secondo
[script.fn_veste_utilizzabile](/dbzero/script/funzioni/fn_veste_utilizzabile):
la stessa regola che poi decide in `fn_sync_auth_user_is_active`. Una
credenziale senza vesti resta fuori, com'era.

Perché: con D-2 l'operatore umano scade anche quando scade il suo **rapporto**
(`risorse_umane.valido_al`), e il ramo unico su `identita_digitali.valido_al`
quel candidato non lo proponeva mai.

*(Dal 12-09 al 07-10-2026 la funzione aveva un solo ramo: identità attive con
`identita_digitali.valido_al < CURRENT_DATE`.)*

⛔ **Il «ramo legacy» è caduto** — leggeva `risorse_umane.valido_al` attraverso
la vista `risorse_umane_auth_user` (ritirata). Decisione di Tid: *«tutto deve
entrare in `identita_digitali`»*. E non è una perdita di regola:
`fn_sync_auth_user_is_active` (v4) decide **solo** sull'identità, quindi quel
ramo poteva proporre candidati, mai cambiare l'esito.
⚠️ **Superato il 07-10-2026 su un punto** (D-2 di `brief-db-veste-utilizzabile`):
per l'operatore umano la fine del rapporto chiude l'accesso. Non torna il ramo
legacy: il rapporto lo guarda il building block, in una sede sola.

*(Testo precedente, per la storia: la funzione copriva «entrambi i modelli»,
combinati via `UNION`.)*

Le due sorgenti sono combinate via `UNION` e poi filtrate con
`SELECT DISTINCT auth_user_id` per evitare double-sync quando lo stesso
utente è presente in entrambi i modelli durante la transizione.

---

### Regole applicate

* La query interna seleziona solo `auth_user` ancora `is_active = true`
  (gli utenti già disattivati non serve re-sincronizzarli).
* Per ogni `auth_user_id` trovato chiama
  `anagrafiche.fn_sync_auth_user_is_active(auth_user_id)` che applica la
  logica fail-closed (fuori finestra → `false`).
* Incrementa il contatore solo se la funzione ritorna `true` (ovvero se
  `auth_user.is_active` è stato effettivamente modificato).
* In ambienti CI senza schema `django`, la funzione esce subito con `0`.

---

### Output

Ritorna `integer` — numero di utenti effettivamente disattivati.

---

### Uso previsto

* **pgAgent**: job giornaliero schedulato (tipicamente alle prime ore del
  mattino) via `db/changelog/migrations_v2/85_pgagent/`.
* **Management command Django**: `python manage.py sync_auth_user_active`
  per esecuzioni manuali o invocate da pipeline di manutenzione.

---

### Ruolo nel processo

La funzione completa il sistema di propagazione dello stato di login: i
trigger reattivi gestiscono i cambi espliciti, questa funzione gestisce i
cambi temporali impliciti (scadenza overnight). Con l'estensione del ramo
`identita_digitali`, copre ora anche portali clienti/fornitori e shop.

---

{% include-markdown "signature-core.md" %}
