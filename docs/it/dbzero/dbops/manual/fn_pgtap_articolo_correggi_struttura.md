## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_articolo_correggi_struttura`

> 👀 **Vedi anche**
>
> [catalogo.fn_articolo_correggi_struttura](/dbzero/catalogo/manual/fn_articolo_correggi_struttura) — il verbo che questo builder chiama

### 🎯 Scopo Principale

(latest review 2026-10-13, brief-db-articoli-ammessi-per-documento A-10)

Builder per i **test pgTAP**. Cambia i flag strutturali di un articolo **già usato** passando dalla
porta vera: il verbo amministratore, chiamato da un SUPER_ADMIN costruito
(`dbops.fn_pgtap_crea_operatore_umano(.., true)`). Poi rimette il contesto di chi chiama
(`app.current_user_id`, `app.ruolo_applicativo`), anche se era vuoto.

Serve ai test che provano che cosa succede **a valle** quando un articolo cambia dopo l'uso: la
natura congelata sulle righe, la riconsegna esente, l'erogazione.

⛔ È INVOKER e non aggira niente: un helper DEFINER che salta la porta sarebbe una scorciatoia
eseguibile dall'applicazione.

Esempio: `SELECT dbops.fn_pgtap_articolo_correggi_struttura(v_articolo, '{"is_solo_componente": true}');`

---
{% include-markdown "signature-core.md" %}
