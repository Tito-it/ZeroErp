## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_fixture_crea_utente_tecnico`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [script.fn_applica_crea_utente_tecnico](/dbzero/script/funzioni/fn_applica_crea_utente_tecnico) — la primitiva che chiama
> * [script.fn_crea_utente_tecnico](/dbzero/script/funzioni/fn_crea_utente_tecnico) — il verbo di cui ha firma e regole
> * [dbops.fn_pgtap_crea_emittente_operatore](/dbzero/dbops/funzioni/fn_pgtap_crea_emittente_operatore) — il builder che la usa
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — i builder dell'accesso

---

### 🎯 Scopo Principale

Crea l'utente tecnico di un processo per un emittente, con la primitiva
[fn_applica_crea_utente_tecnico](/dbzero/script/funzioni/fn_applica_crea_utente_tecnico). Argomenti, regole e
risultato sono quelli del verbo [fn_crea_utente_tecnico](/dbzero/script/funzioni/fn_crea_utente_tecnico), senza
il suo permesso.

---

### 🧪 Per chi è

Per i pgTAP e basta. Le tabelle che danno l'accesso sono in sola lettura per l'applicazione, e i verbi che le
scrivono chiedono il SUPER_ADMIN: il primo SUPER_ADMIN di un test non ha nessuno da cui farsi creare. La fixture
usa le regole del verbo senza il suo permesso. Un test non la chiama da sé: la chiamano i builder.

---

### ⛔ Il cancello: l'ambiente

È `SECURITY DEFINER` ed eseguibile dall'applicazione: è la sola strada senza permesso aperta all'app. Al posto
del guard la chiude l'ambiente dell'installazione. Parte solo dove sono ammessi i dati di sviluppo, con la stessa
regola del provisioning (`dbops.fn_dati_di_sviluppo_ammessi_su_valori`), e in PRODUZIONE solleva
`E_DATI_DI_SVILUPPO_IN_PRODUZIONE` prima di ogni scrittura. L'ambiente sta in `dbops.installazione`, che
l'applicazione legge soltanto.

⚠️ Il limite, dichiarato: su un'installazione di sviluppo l'applicazione può crearsi un utente tecnico di fixture,
come già può fare col provisioning.

Test: `db/pgtap/config/test-porta-tabelle-accesso-v1.sql` (15-16).
