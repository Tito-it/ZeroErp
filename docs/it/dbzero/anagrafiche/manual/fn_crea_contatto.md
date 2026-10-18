## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_contatto()`

> 👀 **Vedi anche**
>
> [anagrafiche.contatti](/dbzero/anagrafiche/manual/contatti) ·
> [script.fn_scrivi_riga_da_jsonb](/dbzero/script/manual/fn_scrivi_riga_da_jsonb)

### 🎯 Scopo
(17-10-2026 — brief `brief-db-processi-accensione-per-ambiente`, 2b-1 lotto 3)

**Creare un contatto** di un soggetto, oppure di un suo ruolo (il contatto
dell'ufficio acquisti di un fornitore, per esempio). È la sede unica: la usano
la creazione di persone, società e utenti tecnici, i builder pgTAP e il
backend.

### La regola

**Nominativo e tipo di contatto, o niente.** Un contatto senza uno dei due è
rifiutato con `E_CONTATTO_INCOMPLETO`, e il campo che manca si accende nel
form. Gli altri campi (email, telefono, cellulare, PEC, note, titolo di
cortesia, unità organizzativa, istanza) sono facoltativi; un campo che non
appartiene a un contatto è rifiutato col suo nome.

Le regole della tabella valgono come sempre: un solo contatto per tipo sullo
stesso soggetto (o sullo stesso ruolo), e il primo contatto di un ruolo
diventa quello di default.

⚠️ Decidere **se** creare il contatto, quando in un form è facoltativo e
l'utente l'ha lasciato vuoto, resta al backend e al frontend: il database
decide **come** si scrive.

### Test

`db/pgtap/anagrafiche/test-fn-crea-contatto-v1.sql`.

---

{% include-markdown "signature-core.md" %}
