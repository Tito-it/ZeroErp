## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_auth_user`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — le vesti che decidono se la credenziale è accesa
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_operatore](/dbzero/anagrafiche/funzioni/fn_crea_operatore) — la madre che la chiama quando l'email non ha una credenziale
> * [anagrafiche.fn_provisiona_dati_di_sviluppo](/dbzero/anagrafiche/funzioni/fn_provisiona_dati_di_sviluppo) — crea così le credenziali dei portali di prova
> * [script.fn_get_auth_user_id_for_email](/dbzero/script/funzioni/fn_get_auth_user_id_for_email) — la regola dell'email unica, senza maiuscole
> * [anagrafiche.trgfn_identita_digitali_sync_auth_user_active](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_sync_auth_user_active) — la credenziale segue le vesti
>
> Guide:
>
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — la persona, la veste e la credenziale

---

### 🎯 Scopo Principale

`anagrafiche.fn_crea_auth_user` crea una credenziale (una riga di `django.auth_user`) dopo aver controllato che
username ed email siano liberi, e ne restituisce l'id.

È un building block: non crea il soggetto, la veste, il rapporto né i contatti. Dentro il database lo chiamano
`anagrafiche.fn_crea_operatore`, solo quando l'email non ha ancora una credenziale (altrimenti la riusa), e
`anagrafiche.fn_provisiona_dati_di_sviluppo`, per gli utenti di prova dei portali.

---

### Username, email e password sono obbligatori

Tutti i parametri hanno un default vuoto, per poterli passare per nome; l'obbligo lo controlla il corpo. Username,
email e password cifrata (nel formato di Django) sono obbligatori, nome e cognome no: se mancano diventano stringhe
vuote, perché Django li vuole non nulli. Username, email, nome e cognome si scrivono senza gli spazi ai bordi.

---

### ⭐ L'email è unica senza distinguere maiuscole e minuscole

Lo username si confronta così com'è. L'email no: la funzione non confronta da sé, ma chiede a
`script.fn_get_auth_user_id_for_email`, la sede unica della regola, e `Mario@x.it` è la stessa email di
`mario@x.it`. Sotto, come rete, c'è l'indice unico sull'email in minuscolo di `django.auth_user`, dove esiste:
nasce dopo le migrazioni di Django, e in CI non c'è. Senza il controllo una collisione arriverebbe dall'indice
come errore generico del vincolo.

---

### La credenziale nasce accesa, e la spengono le vesti

La riga nasce accesa (`is_active` vero), senza staff né superuser, con la data di iscrizione di adesso. Chi decide
poi se la credenziale apre la porta sono le sue vesti: quando nasce la prima veste, i trigger di
`anagrafiche.identita_digitali` riallineano la credenziale alla regola «accesa se almeno una veste è utilizzabile».
Così una credenziale creata per un operatore, che nasce con la veste spenta, è spenta prima della fine della
stessa istruzione.

---

### ⛔ Chi la esegue

Solo il proprietario: è un passo interno della creazione dell'operatore, e l'applicazione non ha `EXECUTE`, e
nemmeno `PUBLIC`. La chiama la primitiva `anagrafiche.fn_applica_crea_operatore`, dietro il verbo del SUPER_ADMIN.

---

### ⚠️ Che cosa oggi non copre

* **Una credenziale senza vesti resta accesa.** Finché nessuna veste nasce su di lei, la credenziale creata da
  sola contraddice la regola delle vesti, e il riallineamento periodico non la tocca: lavora solo sulle credenziali
  che hanno almeno una veste.
* **Non è l'unica strada.** Il backend crea le credenziali degli inviti al portale con un inserimento diretto in
  `django.auth_user`, che non passa da questo controllo dell'email.

---

### Codici errore

| Codice | Quando |
| --- | --- |
| `E_ADMIN_VALIDAZIONE` | username, email o password mancanti o vuoti |
| `E_ADMIN_USERNAME_DUPLICATO` | lo username è già di un'altra credenziale |
| `E_ADMIN_EMAIL_DUPLICATA` | l'email è già di un'altra credenziale, anche solo con maiuscole diverse |
| `E_CREDENZIALE_EMAIL_AMBIGUA` | più credenziali hanno già la stessa email a meno delle maiuscole (da `script.fn_get_auth_user_id_for_email`) |

---

### Test

* `db/pgtap/anagrafiche/test-fn-crea-auth-user.sql` — la creazione, l'email e i campi fissi, username ed email
  duplicati, username, email e password mancanti.
* `db/pgtap/anagrafiche/test-credenziale-email-unica-v1.sql` — l'email che differisce solo per le maiuscole, e la
  forma dell'indice dove c'è.
* Nessun test prova che la credenziale creata da sola resti accesa, né il taglio degli spazi.

---

### Note di migrazione

* 2026-09-25 — l'email duplicata si riconosce senza distinguere maiuscole e minuscole, chiedendo a
  `script.fn_get_auth_user_id_for_email`; prima il confronto era esatto e due grafie passavano come due persone.
* Le pagine di prima citavano `fn_crea_operatore` e un futuro `fn_crea_admin` come chiamanti: la prima è stata
  ritirata, la seconda non è mai nata.

---

{% include-markdown "signature-core.md" %}
