# Empório da Música — Agente de Atendimento

Agente conversacional em **Python** para o desafio técnico **AI Engineer (Artefact)**: atendimento textual da loja fictícia **Empório da Música** (Campo Grande/MS), combinando **function calling** sobre dados operacionais (CSVs) e **RAG** sobre o manual `políticas_da_loja.pdf`.

## Requisitos

- Python **3.11+**
- Chave de API **OpenAI** (modelo padrão: `gpt-4o-mini`)
- Dados em `data/` (CSVs + PDF incluídos neste repositório)

## Configuração

```powershell
cd emporio-musica-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
# Edite .env e defina OPENAI_API_KEY
```

Na primeira execução, o CLI:

1. Gera `data/store.db` a partir dos CSVs
2. Indexa o PDF em `data/chroma_policies/` (embeddings locais via Chroma)

Scripts opcionais:

```powershell
python scripts/ingest_data.py
python scripts/index_policies.py
python scripts/index_policies.py --force
```

## Executar o agente (CLI)

```powershell
emporio-agent
# ou
python -m emporio_agent.cli
```

Comandos na sessão:

- `/limpar` — reinicia o histórico
- `/export nome.md` — salva transcrição em `examples/conversations/`
- `/sair` — encerra

## Arquitetura

| Camada | Responsabilidade |
|--------|------------------|
| `data_loader.py` | CSV → SQLite; buscas de produtos e pedidos |
| `promotions.py` | Preço efetivo (maior desconto entre promoções `is_active=1`) |
| `policies_rag.py` | PDF → chunks → Chroma (busca semântica) |
| `tools.py` | Schemas + dispatch das 5 ferramentas |
| `agent.py` | Loop OpenAI tool calling + memória de sessão |
| `cli.py` | Interface Rich no terminal |

### Ferramentas expostas ao LLM

- `search_products` — catálogo com filtros (categoria, preço máx., estoque)
- `get_product_details` — por ID ou nome
- `get_order_status` — status/itens; validação opcional por e-mail
- `list_customer_orders` — pedidos por e-mail
- `search_store_policies` — trechos do manual (horários, trocas, frete, etc.)

## Decisões técnicas

- **Híbrido tools + RAG:** dados tabulares e preços vêm de SQLite (sem alucinação); regras e textos legais vêm do PDF indexado.
- **SQLite em vez de SQL livre:** ferramentas tipadas, previsíveis e fáceis de testar.
- **Chroma + embedding ONNX default:** indexação local sem custo extra de embeddings na API.
- **OpenAI chat completions + tools:** loop simples, compatível com entrevista técnica.
- **Promoções:** se houver várias ativas para o mesmo produto, aplica-se o **maior `discount_percent`**.
- **Privacidade de pedidos:** recomenda-se informar `order_id`; se o cliente passar e-mail, usa-se `customer_email` para conferir titularidade.
- **Estoque:** as ferramentas de catálogo devolvem só `availability` (`disponivel` ou `indisponivel`). A quantidade de cada produto não chega ao modelo nem deve aparecer na resposta.

## Limitações e próximos passos

- Não cria, altera nem cancela pedidos (encaminha para humano).
- Histórico só na sessão atual (sem banco de conversas).
- RAG depende da qualidade da extração do PDF; chunks grandes podem misturar temas.
- Melhorias futuras: UI web (Gradio), testes de eval do agente, cache de respostas frequentes, autenticação forte para pedidos.

## Testes

```powershell
pytest tests/
```

## Exemplos de conversa

Transcrições em [`examples/conversations/`](examples/conversations/) — incluem catálogo, preço, endereço/horário, **devolução (CDC + manual)** e limites do agente.

## Uso de assistentes de IA no desenvolvimento

Este projeto foi estruturado com apoio do **Cursor** (planejamento, geração de boilerplate, revisão de edge cases). O fluxo foi: leitura do enunciado/PDF → desenho híbrido tools+RAG → implementação incremental → testes manuais das ferramentas → documentação. Decisões de negócio (promoções, privacidade) foram explicitadas no código e neste README.