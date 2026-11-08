> **Ultimo aggiornamento**: 4 novembre 2026

### 🧪 Le fixture pgTAP — a che cosa servono

Questa funzione appartiene alla famiglia delle **fixture per i test pgTAP**: non è codice di
dominio e non viene mai chiamata dall'applicazione. Esiste per far costruire a un test i dati
di cui ha bisogno, in modo che il test resti leggibile e non si rompa per ragioni che non
c'entrano con ciò che verifica.

---

### ⭐ Perché una fixture invece di un `INSERT` nel test

Perché dal 2026-08-07 **i pgTAP girano come l'applicazione** (`zeroerp_app` + contesto
operatore, con la RLS attiva), non più come owner. Costruire una fixture a mano significa
quindi doversi ricordare, in ogni test, di:

* rispettare i vincoli di dominio e i guard che scattano sull'`INSERT`;
* usare valori che non collidano con quelli già presenti (codice fiscale, partita IVA);
* dichiarare la veste giusta, perché **le policy sono fail-closed**: senza contesto le
  `SELECT` della fixture leggono zero righe e il test diventa **verde per sottrazione** —
  passa smettendo di verificare.

Le fixture concentrano quella conoscenza in un posto solo. Quando un guard nuovo cambia le
condizioni d'ingresso, si aggiorna la fixture e non trenta test.

⚠️ L'eccezione: un file col marcatore `pgtap-runner: owner` (e il suo motivo obbligatorio,
`pgtap-runner-motivo`) gira come owner, perché il **soggetto** del test non è raggiungibile
dall'applicazione. Una fixture non sa da quale dei due file viene chiamata: deve funzionare **in
tutti e due i casi**, come `zeroerp_app` sotto RLS e come owner. Il criterio del marcatore sta
nella [guida](/guide/pgtap-come-si-scrive-un-test), sezione «Quando il test non può girare come
l'applicazione».

---

### ⚠️ Non usarle fuori dai test

Sono in `dbops` e in `script` per comodità di riuso, non perché siano utilità generali.
Scrivono dati di prova e non hanno i presidi che una porta di dominio deve avere.

Guida: [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test); template:
`db/pgtap/_TEMPLATE.sql.txt`, spiegato nella stessa guida, sezione
[«Non partire da zero»](/guide/pgtap-come-si-scrive-un-test#non-partire-da-zero).
