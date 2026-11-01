# Status de pedido e limite de escopo

**Usuário:** Qual o status do pedido 8?

**Assistente:** Para consultar o pedido preciso confirmar a titularidade. Me passa o **e-mail cadastrado** na compra? Sem ele eu não acesso status, itens nem rastreio.

**Usuário:** anacarol.ferreira@coldmail.com

**Assistente:** O e-mail confere com o pedido **#8**. Ele está **enviado (shipped)**.

- **Cliente:** Ana Carolina Ferreira
- **Data:** 15/02/2026
- **Total:** R$ 349,90 (débito)
- **Rastreio:** BRJL5544332BR
- **Previsão de entrega:** 28/02/2026
- **Item:** 1× Kala KA-C Concert Mogno

Se quiser, posso explicar o significado do status ou ajudar com outro pedido.

**Usuário:** Cancela esse pedido pra mim.

**Assistente:** No momento **não consigo cancelar pedidos** por aqui — essa operação precisa ser feita pela equipe humana. Entre em contato pelo **(67) 3341-4444** ou **contato@emporiodamusica.com.br** informando o pedido **#8**.

**Usuário:** Qual a previsão do tempo em Campo Grande amanhã?

**Assistente:** Essa pergunta foge do meu escopo — sou o assistente da **Empório da Música** e posso ajudar com produtos, pedidos, pagamento, entregas e políticas da loja. Quer consultar algum instrumento ou pedido?

_Ferramentas usadas: `get_order_status(order_id=8, customer_email="anacarol.ferreira@coldmail.com")` — a primeira pergunta não consultou o pedido, porque o e-mail ainda não tinha sido informado._
