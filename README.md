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
2. Indexa o PDF em `data/chroma_policies/` com o modelo local `paraphrase-multilingual-MiniLM-L12-v2` (o download do modelo ocorre na primeira indexação)

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
- `get_order_status` — status/itens/rastreio somente com o e-mail do titular
- `list_customer_orders` — pedidos por e-mail
- `search_store_policies` — trechos do manual (horários, trocas, frete, etc.)

## Decisões técnicas

- **Híbrido tools + RAG:** dados tabulares e preços vêm de SQLite (sem alucinação); regras e textos legais vêm do PDF indexado.
- **SQLite em vez de SQL livre:** ferramentas tipadas, previsíveis e fáceis de testar.
- **Chroma + `paraphrase-multilingual-MiniLM-L12-v2`:** o manual está em português. O embedding padrão do Chroma (`all-MiniLM-L6-v2`) é treinado sobretudo em inglês e recupera mal esse texto. O modelo multilingual continua local, sem custo de embedding na API. O PDF sai do extrator com uma palavra por linha; o índice junta essas palavras e corta por seção numerada (até ~480 caracteres, repetindo o título), em vez de uma janela fixa de 900 caracteres que misturava assuntos.
- **OpenAI chat completions + tools:** loop simples, compatível com entrevista técnica.
- **Promoções:** se houver várias ativas para o mesmo produto, aplica-se o **maior `discount_percent`**.
- **Catálogo:** `search_products` devolve `matched_count` e `truncated`. O limite padrão é 25 e o filtro de preço roda sobre o conjunto inteiro, então uma busca como “violões até R$ 1.000” não perde itens em silêncio. Se a página vier cortada, o agente precisa dizer isso.
- **Privacidade de pedidos:** `get_order_status` só devolve status, itens, rastreio e nome quando o e-mail informado é o do titular. Sem e-mail, ou com e-mail de outra pessoa, a ferramenta não revela dados do pedido.
- **Estoque:** as ferramentas de catálogo devolvem só `availability` (`disponivel` ou `indisponivel`). A quantidade de cada produto não chega ao modelo nem deve aparecer na resposta.

## Limitações e próximos passos

- Não cria, altera nem cancela pedidos (encaminha para humano).
- Histórico só na sessão atual (sem banco de conversas).
- A extração do PDF perde tabelas e quebras de parágrafo; a recuperação depende da redação da pergunta, mesmo com chunks por seção e embedding multilingual.
- O e-mail do pedido confere a titularidade, mas não substitui autenticação forte.
- Melhorias futuras: UI web (Gradio), testes de eval do agente de ponta a ponta, cache de respostas frequentes.

## Testes

```powershell
pytest tests/
```

## Exemplos de conversa

Transcrições em [`examples/conversations/`](examples/conversations/) — incluem catálogo, preço, endereço/horário, **devolução (CDC + manual)** e limites do agente.

## Uso de assistentes de IA no desenvolvimento

Este projeto foi estruturado com apoio do **Cursor** (planejamento, geração de boilerplate, revisão de edge cases). O fluxo foi: leitura do enunciado/PDF → desenho híbrido tools+RAG → implementação incremental → testes manuais das ferramentas → documentação. Decisões de negócio (promoções, privacidade) foram explicitadas no código e neste README.